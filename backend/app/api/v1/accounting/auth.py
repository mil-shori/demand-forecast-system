"""
freee OAuth2接続管理 API
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import FreeeToken
from app.services import freee_token_store
from app.services.freee_client import (
    FreeeAPIError,
    FreeeNotConfiguredError,
    FreeeOAuthClient,
    generate_state_token,
    verify_state_token,
)
from app.services.freee_token_store import EncryptionKeyMissingError

router = APIRouter()
logger = logging.getLogger(__name__)


class AuthUrlResponse(BaseModel):
    auth_url: str


class CompanyInfo(BaseModel):
    company_id: int
    company_name: Optional[str] = None
    is_active: bool
    expires_at: Optional[str] = None


class FreeeStatusResponse(BaseModel):
    configured: bool
    connected: bool
    companies: List[CompanyInfo] = []


class SelectCompanyRequest(BaseModel):
    company_id: int


def _check_configured() -> None:
    if not settings.freee_client_id or not settings.freee_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "freee連携が未設定です。"
                "FREEE_CLIENT_ID / FREEE_CLIENT_SECRET を backend/.env に設定してください。"
            ),
        )
    if not settings.data_encryption_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATA_ENCRYPTION_KEY が未設定です。backend/.env に設定してください。",
        )


@router.get("/freee/auth-url", response_model=AuthUrlResponse)
async def get_auth_url():
    """freee認可画面のURLを生成して返す"""
    _check_configured()
    try:
        oauth = FreeeOAuthClient()
        state = generate_state_token()
        return AuthUrlResponse(auth_url=oauth.build_authorize_url(state))
    except FreeeNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )


@router.get("/freee/callback")
async def freee_callback(code: str, state: str, db: Session = Depends(get_db)):
    """freeeからのOAuth2コールバック。トークン交換・保存後、フロントへリダイレクトする"""
    _check_configured()
    if not verify_state_token(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="state の検証に失敗しました。認可をやり直してください。",
        )

    oauth = FreeeOAuthClient()
    try:
        token_data = await oauth.exchange_code(code)
    except FreeeAPIError as e:
        logger.error(f"freee token exchange failed: {e}")
        return RedirectResponse(
            f"{settings.frontend_base_url}/accounting?connected=0&error=token_exchange"
        )

    # 事業所一覧を取得して全事業所分のトークンを保存
    access_token = token_data["access_token"]
    company_id_hint = token_data.get("company_id")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.freee_api_base_url}/api/1/companies",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        response.raise_for_status()
        companies = response.json().get("companies", [])
    except Exception as e:
        logger.error(f"freee companies fetch failed: {e}")
        companies = []

    try:
        if companies:
            for company in companies:
                freee_token_store.save_token(
                    db,
                    company_id=company["id"],
                    company_name=company.get("display_name") or company.get("name"),
                    access_token=access_token,
                    refresh_token=token_data["refresh_token"],
                    expires_in=token_data.get("expires_in", 21600),
                    scope=token_data.get("scope"),
                )
        elif company_id_hint:
            freee_token_store.save_token(
                db,
                company_id=int(company_id_hint),
                access_token=access_token,
                refresh_token=token_data["refresh_token"],
                expires_in=token_data.get("expires_in", 21600),
                scope=token_data.get("scope"),
            )
        else:
            return RedirectResponse(
                f"{settings.frontend_base_url}/accounting?connected=0&error=no_company"
            )
    except EncryptionKeyMissingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )

    return RedirectResponse(f"{settings.frontend_base_url}/accounting?connected=1")


@router.get("/freee/status", response_model=FreeeStatusResponse)
async def freee_status(db: Session = Depends(get_db)):
    """freee接続状態と事業所一覧を返す"""
    configured = bool(
        settings.freee_client_id
        and settings.freee_client_secret
        and settings.data_encryption_key
    )
    tokens = db.query(FreeeToken).order_by(FreeeToken.company_id).all()
    return FreeeStatusResponse(
        configured=configured,
        connected=len(tokens) > 0,
        companies=[
            CompanyInfo(
                company_id=t.company_id,
                company_name=t.company_name,
                is_active=t.is_active,
                expires_at=t.expires_at.isoformat() if t.expires_at else None,
            )
            for t in tokens
        ],
    )


@router.post("/freee/company", response_model=FreeeStatusResponse)
async def select_company(request: SelectCompanyRequest, db: Session = Depends(get_db)):
    """使用する事業所を切り替える"""
    try:
        freee_token_store.set_active_company(db, request.company_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return await freee_status(db)


@router.post("/freee/disconnect")
async def disconnect(db: Session = Depends(get_db)):
    """freee接続を解除する（保存済みトークンを全削除）"""
    count = freee_token_store.delete_all_tokens(db)
    return {"deleted": count, "message": "freee接続を解除しました"}
