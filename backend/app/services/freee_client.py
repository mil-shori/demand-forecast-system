"""
freee会計APIクライアント

- FreeeOAuthClient: OAuth2認可コードフロー（認可URL生成・トークン交換・リフレッシュ）
- FreeeAPIClient: 認証済みAPI呼び出し（トークン自動リフレッシュ・429リトライ付き）
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import FreeeToken
from app.services import freee_token_store

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30.0
STATE_TOKEN_EXPIRE_MINUTES = 10


class FreeeNotConfiguredError(Exception):
    """FREEE_CLIENT_ID / FREEE_CLIENT_SECRET が未設定"""


class FreeeNotConnectedError(Exception):
    """freee未接続（トークンなし）"""


class FreeeAPIError(Exception):
    """freee APIエラー"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"freee API error {status_code}: {message}")


def _ensure_configured() -> None:
    if not settings.freee_client_id or not settings.freee_client_secret:
        raise FreeeNotConfiguredError(
            "FREEE_CLIENT_ID / FREEE_CLIENT_SECRET が未設定です。backend/.env に設定してください。"
        )


def generate_state_token() -> str:
    """CSRF対策用のstate（secret_keyで署名したJWT、有効期限10分）"""
    payload = {
        "purpose": "freee_oauth_state",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=STATE_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_state_token(state: str) -> bool:
    """stateの署名・有効期限を検証"""
    try:
        payload = jwt.decode(
            state, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("purpose") == "freee_oauth_state"
    except JWTError:
        return False


class FreeeOAuthClient:
    """OAuth2認可コードフロー"""

    def __init__(self):
        self.auth_base_url = settings.freee_auth_base_url
        self.client_id = settings.freee_client_id
        self.client_secret = settings.freee_client_secret
        self.redirect_uri = settings.freee_redirect_uri

    def build_authorize_url(self, state: str) -> str:
        """freee認可画面のURLを生成"""
        _ensure_configured()
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.auth_base_url}/public_api/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """認可コードをトークンに交換"""
        _ensure_configured()
        return await self._token_request(
            {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
        )

    async def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """リフレッシュトークンでアクセストークンを更新"""
        _ensure_configured()
        return await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
            }
        )

    async def _token_request(self, data: Dict[str, str]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{self.auth_base_url}/public_api/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code != 200:
            logger.error(
                f"freee token request failed: {response.status_code} {response.text}"
            )
            raise FreeeAPIError(response.status_code, response.text)
        return response.json()


class FreeeAPIClient:
    """
    認証済みfreee API呼び出し。

    - 呼び出し前にトークン期限をチェックし、期限切れ間近なら自動リフレッシュ
    - 401応答時は1回だけリフレッシュして再試行
    - 429応答時はRetry-Afterを待って1回だけ再試行
    - freeeのrefresh_tokenはローテーションされるため、リフレッシュ成功後は即DB保存
    """

    def __init__(self, db: Session, token: Optional[FreeeToken] = None):
        self.db = db
        self.token = token or freee_token_store.get_active_token(db)
        if self.token is None:
            raise FreeeNotConnectedError("freeeに接続されていません。先にOAuth認可を行ってください。")
        self.oauth = FreeeOAuthClient()
        self.api_base_url = settings.freee_api_base_url

    @property
    def company_id(self) -> int:
        return self.token.company_id

    async def _ensure_fresh_token(self) -> str:
        """有効なアクセストークンを返す（必要ならリフレッシュ）"""
        if freee_token_store.is_token_expiring(self.token):
            await self._refresh_and_save()
        return freee_token_store.decrypt_token(self.token.access_token)

    async def _refresh_and_save(self) -> None:
        refresh_token = freee_token_store.decrypt_token(self.token.refresh_token)
        token_data = await self.oauth.refresh(refresh_token)
        # refresh_tokenはローテーションされるため即保存（保存失敗＝再認可が必要になる）
        self.token = freee_token_store.save_token(
            self.db,
            company_id=self.token.company_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_in=token_data.get("expires_in", 21600),
            scope=token_data.get("scope"),
        )

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """freee APIへのリクエスト（リフレッシュ・リトライ込み）"""
        access_token = await self._ensure_fresh_token()
        response = await self._send(method, path, access_token, params, json_body)

        if response.status_code == 401:
            # トークン失効の可能性 → 1回だけリフレッシュして再試行
            await self._refresh_and_save()
            access_token = freee_token_store.decrypt_token(self.token.access_token)
            response = await self._send(method, path, access_token, params, json_body)

        if response.status_code == 429:
            # レート制限 → Retry-After秒（上限60秒）待って1回だけ再試行
            retry_after = min(int(response.headers.get("Retry-After", "5")), 60)
            logger.warning(f"freee rate limited, retrying after {retry_after}s")
            await asyncio.sleep(retry_after)
            response = await self._send(method, path, access_token, params, json_body)

        if response.status_code >= 400:
            logger.error(
                f"freee API error: {method} {path} -> "
                f"{response.status_code} {response.text}"
            )
            raise FreeeAPIError(response.status_code, response.text)

        if not response.content:
            return {}
        return response.json()

    async def _send(
        self,
        method: str,
        path: str,
        access_token: str,
        params: Optional[Dict[str, Any]],
        json_body: Optional[Dict[str, Any]],
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            return await client.request(
                method,
                f"{self.api_base_url}{path}",
                params=params,
                json=json_body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Api-Version": "2020-06-15",
                },
            )

    # --- 主要エンドポイント ---

    async def get_companies(self) -> List[Dict[str, Any]]:
        """事業所一覧"""
        data = await self.request("GET", "/api/1/companies")
        return data.get("companies", [])

    async def get_account_items(self) -> List[Dict[str, Any]]:
        """勘定科目一覧"""
        data = await self.request(
            "GET", "/api/1/account_items", params={"company_id": self.company_id}
        )
        return data.get("account_items", [])

    async def get_partners(self, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """取引先一覧"""
        params: Dict[str, Any] = {"company_id": self.company_id, "limit": 100}
        if keyword:
            params["keyword"] = keyword
        data = await self.request("GET", "/api/1/partners", params=params)
        return data.get("partners", [])

    async def get_taxes(self) -> List[Dict[str, Any]]:
        """税区分一覧"""
        data = await self.request("GET", f"/api/1/taxes/companies/{self.company_id}")
        return data.get("taxes", [])

    async def create_deal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """取引（deal）作成"""
        payload = {**payload, "company_id": self.company_id}
        data = await self.request("POST", "/api/1/deals", json_body=payload)
        return data.get("deal", {})

    async def get_deals(
        self,
        start_issue_date: Optional[str] = None,
        end_issue_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """取引一覧"""
        params: Dict[str, Any] = {"company_id": self.company_id, "limit": 100}
        if start_issue_date:
            params["start_issue_date"] = start_issue_date
        if end_issue_date:
            params["end_issue_date"] = end_issue_date
        data = await self.request("GET", "/api/1/deals", params=params)
        return data.get("deals", [])

    async def get_trial_pl(
        self, fiscal_year: int, start_month: int, end_month: int
    ) -> Dict[str, Any]:
        """損益計算書（試算表）"""
        data = await self.request(
            "GET",
            "/api/1/reports/trial_pl",
            params={
                "company_id": self.company_id,
                "fiscal_year": fiscal_year,
                "start_month": start_month,
                "end_month": end_month,
            },
        )
        return data.get("trial_pl", {})

    async def get_trial_bs(
        self, fiscal_year: int, start_month: int, end_month: int
    ) -> Dict[str, Any]:
        """貸借対照表（試算表）"""
        data = await self.request(
            "GET",
            "/api/1/reports/trial_bs",
            params={
                "company_id": self.company_id,
                "fiscal_year": fiscal_year,
                "start_month": start_month,
                "end_month": end_month,
            },
        )
        return data.get("trial_bs", {})
