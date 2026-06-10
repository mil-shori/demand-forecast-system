"""
freee_client のテスト（respxでHTTPモック）

- 認可URL生成・state検証
- 認可コード→トークン交換
- refreshローテーション後の即時保存
- 401→リフレッシュ→リトライ、429→Retry-After待機リトライ
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from app.config import settings
from app.services import freee_token_store
from app.services.freee_client import (
    FreeeAPIClient,
    FreeeAPIError,
    FreeeNotConnectedError,
    FreeeOAuthClient,
    generate_state_token,
    verify_state_token,
)

TOKEN_URL = f"{settings.freee_auth_base_url}/public_api/token"
API_BASE = settings.freee_api_base_url


def _token_response(access="new-access", refresh="new-refresh"):
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": 21600,
        "scope": "read write",
    }


def _connect(db_session, expires_in=21600):
    return freee_token_store.save_token(
        db_session,
        company_id=101,
        access_token="current-access",
        refresh_token="current-refresh",
        expires_in=expires_in,
    )


def test_state_token_roundtrip():
    state = generate_state_token()
    assert verify_state_token(state) is True
    assert verify_state_token("tampered-state") is False


def test_build_authorize_url_contains_required_params():
    oauth = FreeeOAuthClient()
    state = generate_state_token()
    url = oauth.build_authorize_url(state)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.path == "/public_api/authorize"
    assert params["client_id"] == [settings.freee_client_id]
    assert params["response_type"] == ["code"]
    assert params["redirect_uri"] == [settings.freee_redirect_uri]
    assert params["state"] == [state]


@pytest.mark.asyncio
@respx.mock
async def test_exchange_code():
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response())
    )
    oauth = FreeeOAuthClient()
    data = await oauth.exchange_code("auth-code-123")
    assert data["access_token"] == "new-access"
    sent = parse_qs(route.calls[0].request.content.decode())
    assert sent["grant_type"] == ["authorization_code"]
    assert sent["code"] == ["auth-code-123"]


@pytest.mark.asyncio
@respx.mock
async def test_exchange_code_error_raises():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(401, json={"error": "invalid_grant"}))
    oauth = FreeeOAuthClient()
    with pytest.raises(FreeeAPIError):
        await oauth.exchange_code("bad-code")


def test_api_client_requires_connection(db_session):
    with pytest.raises(FreeeNotConnectedError):
        FreeeAPIClient(db_session)


@pytest.mark.asyncio
@respx.mock
async def test_request_refreshes_expiring_token_and_saves_rotated_refresh(db_session):
    # 期限切れ間近のトークンで接続
    token = _connect(db_session, expires_in=60)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response("rotated-access", "rotated-refresh"))
    )
    respx.get(f"{API_BASE}/api/1/account_items").mock(
        return_value=httpx.Response(200, json={"account_items": [{"id": 1, "name": "売上高"}]})
    )

    client = FreeeAPIClient(db_session, token)
    items = await client.get_account_items()
    assert items[0]["name"] == "売上高"

    # ローテーションされたrefresh_tokenがDBに即保存されている
    saved = freee_token_store.get_token_by_company(db_session, 101)
    assert freee_token_store.decrypt_token(saved.access_token) == "rotated-access"
    assert freee_token_store.decrypt_token(saved.refresh_token) == "rotated-refresh"


@pytest.mark.asyncio
@respx.mock
async def test_request_retries_once_on_401(db_session):
    token = _connect(db_session)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response("after-401-access", "after-401-refresh"))
    )
    api_route = respx.get(f"{API_BASE}/api/1/companies").mock(
        side_effect=[
            httpx.Response(401, json={"message": "expired"}),
            httpx.Response(200, json={"companies": [{"id": 101, "display_name": "テスト"}]}),
        ]
    )

    client = FreeeAPIClient(db_session, token)
    companies = await client.get_companies()
    assert companies[0]["id"] == 101
    assert api_route.call_count == 2
    saved = freee_token_store.get_token_by_company(db_session, 101)
    assert freee_token_store.decrypt_token(saved.refresh_token) == "after-401-refresh"


@pytest.mark.asyncio
@respx.mock
async def test_request_retries_once_on_429(db_session):
    token = _connect(db_session)
    api_route = respx.get(f"{API_BASE}/api/1/partners").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"partners": [{"id": 5, "name": "取引先A"}]}),
        ]
    )

    client = FreeeAPIClient(db_session, token)
    partners = await client.get_partners()
    assert partners[0]["id"] == 5
    assert api_route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_request_raises_on_api_error(db_session):
    token = _connect(db_session)
    respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(400, json={"errors": [{"messages": ["金額が不正です"]}]})
    )
    client = FreeeAPIClient(db_session, token)
    with pytest.raises(FreeeAPIError) as exc_info:
        await client.create_deal({"issue_date": "2026-05-01", "type": "income", "details": []})
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@respx.mock
async def test_create_deal_includes_company_id(db_session):
    token = _connect(db_session)
    route = respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 999}})
    )
    client = FreeeAPIClient(db_session, token)
    deal = await client.create_deal({"issue_date": "2026-05-01", "type": "income", "details": []})
    assert deal["id"] == 999
    import json

    sent = json.loads(route.calls[0].request.content)
    assert sent["company_id"] == 101
