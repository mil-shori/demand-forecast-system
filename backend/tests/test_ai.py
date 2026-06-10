"""
AI経理アシスタント（Claude API連携）のテスト

Claude API呼び出しは ai_service._get_client をスタブに差し替えてモックする。
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.config import settings
from app.models import Expense, ExpenseStatus, Order, OrderType
from app.services import ai_service, freee_token_store
from app.services.ai_service import AccountItemSuggestion

API_BASE = settings.freee_api_base_url


class _StubMessages:
    """anthropic.AsyncAnthropic().messages の差し替え用スタブ"""

    def __init__(self, parsed=None, text="", parse_error=None):
        self._parsed = parsed
        self._text = text
        self._parse_error = parse_error
        self.parse_calls = []
        self.create_calls = []

    async def parse(self, **kwargs):
        self.parse_calls.append(kwargs)
        if self._parse_error is not None:
            raise self._parse_error
        return SimpleNamespace(parsed_output=self._parsed)

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        block = SimpleNamespace(type="text", text=self._text)
        return SimpleNamespace(content=[block])


def _stub_client(monkeypatch, parsed=None, text="", parse_error=None):
    messages = _StubMessages(parsed=parsed, text=text, parse_error=parse_error)
    client = SimpleNamespace(messages=messages)
    monkeypatch.setattr(ai_service, "_get_client", lambda: client)
    return messages


def _enable_ai(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-api-key")


def _connect_freee(db):
    return freee_token_store.save_token(
        db, company_id=101, access_token="a", refresh_token="r", expires_in=21600
    )


# --- 設定状態 ---

def test_ai_status_not_configured(client):
    body = client.get("/api/v1/accounting/ai/status").json()
    assert body["configured"] is False
    assert body["model"] is None


def test_ai_status_configured(client, monkeypatch):
    _enable_ai(monkeypatch)
    body = client.get("/api/v1/accounting/ai/status").json()
    assert body["configured"] is True
    assert body["model"] == settings.anthropic_model


# --- 勘定科目のAI推定 ---

def test_suggest_requires_api_key(client):
    response = client.post("/api/v1/accounting/ai/suggest-account-item", json={
        "category": "交通費", "description": "タクシー代",
    })
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_suggest_requires_freee_connection(client, monkeypatch):
    _enable_ai(monkeypatch)
    response = client.post("/api/v1/accounting/ai/suggest-account-item", json={
        "category": "交通費",
    })
    assert response.status_code == 503
    assert "freee" in response.json()["detail"]


@respx.mock
def test_suggest_account_item(client, db_session, monkeypatch):
    _enable_ai(monkeypatch)
    _connect_freee(db_session)
    respx.get(f"{API_BASE}/api/1/account_items").mock(
        return_value=httpx.Response(200, json={"account_items": [
            {"id": 30, "name": "旅費交通費"},
            {"id": 31, "name": "会議費"},
        ]})
    )
    messages = _stub_client(monkeypatch, parsed=AccountItemSuggestion(
        account_item_id=30, account_item_name="旅費交通費",
        confidence=0.95, reason="タクシー代は旅費交通費に該当します。",
    ))

    response = client.post("/api/v1/accounting/ai/suggest-account-item", json={
        "category": "交通費", "description": "客先訪問のタクシー代",
        "transaction_type": "expense",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["account_item_id"] == 30
    assert body["account_item_name"] == "旅費交通費"
    assert 0 <= body["confidence"] <= 1

    # プロンプトに勘定科目候補と取引内容が含まれている
    assert len(messages.parse_calls) == 1
    prompt = messages.parse_calls[0]["messages"][0]["content"]
    assert "旅費交通費" in prompt
    assert "タクシー代" in prompt


@respx.mock
def test_suggest_rejects_hallucinated_account_item(client, db_session, monkeypatch):
    """AIが候補一覧に無いIDを返した場合は502で弾く"""
    _enable_ai(monkeypatch)
    _connect_freee(db_session)
    respx.get(f"{API_BASE}/api/1/account_items").mock(
        return_value=httpx.Response(200, json={"account_items": [
            {"id": 30, "name": "旅費交通費"},
        ]})
    )
    _stub_client(monkeypatch, parsed=AccountItemSuggestion(
        account_item_id=999, account_item_name="存在しない科目",
        confidence=0.9, reason="幻覚",
    ))

    response = client.post("/api/v1/accounting/ai/suggest-account-item", json={
        "category": "交通費",
    })
    assert response.status_code == 502
    assert "999" in response.json()["detail"]


# --- 月次AIサマリー ---

def test_monthly_summary_requires_api_key(client):
    response = client.get("/api/v1/accounting/ai/monthly-summary",
                          params={"year": 2026, "month": 5})
    assert response.status_code == 503


def test_monthly_summary(client, db_session, monkeypatch):
    _enable_ai(monkeypatch)
    db_session.add_all([
        Order(order_id="O1", user_id="U1", order_date=date(2026, 5, 1),
              order_type=OrderType.SUBSCRIPTION, total_amount=Decimal("5000")),
        Expense(expense_date=date(2026, 5, 10), amount=Decimal("1200"), category="交通費",
                payment_method="cash", status=ExpenseStatus.DRAFT),
    ])
    db_session.commit()
    messages = _stub_client(
        monkeypatch,
        text="## 2026年5月の概況\n売上は¥5,000でした。",
    )

    response = client.get("/api/v1/accounting/ai/monthly-summary",
                          params={"year": 2026, "month": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2026
    assert body["month"] == 5
    assert "2026年5月" in body["summary"]

    # プロンプトに当月の実データが含まれている
    assert len(messages.create_calls) == 1
    prompt = messages.create_calls[0]["messages"][0]["content"]
    assert "5,000" in prompt
    assert "交通費" in prompt


# --- 同期フローへのAI自動仕訳統合 ---

@respx.mock
def test_expense_sync_uses_ai_when_no_mapping(client, db_session, monkeypatch):
    """マッピング未定義の経費同期で、AI推定の勘定科目が使われる"""
    _enable_ai(monkeypatch)
    _connect_freee(db_session)
    respx.get(f"{API_BASE}/api/1/account_items").mock(
        return_value=httpx.Response(200, json={"account_items": [
            {"id": 30, "name": "旅費交通費"},
            {"id": 50, "name": "雑費"},
        ]})
    )
    deal_route = respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 1234}})
    )
    _stub_client(monkeypatch, parsed=AccountItemSuggestion(
        account_item_id=30, account_item_name="旅費交通費",
        confidence=0.9, reason="交通費のため",
    ))

    expense_id = client.post("/api/v1/accounting/expenses", json={
        "expense_date": "2026-05-10", "amount": 1200, "category": "交通費",
        "description": "タクシー代",
    }).json()["id"]

    response = client.post(f"/api/v1/accounting/expenses/{expense_id}/sync")
    assert response.status_code == 200
    assert response.json()["freee_deal_id"] == 1234

    import json
    payload = json.loads(deal_route.calls[0].request.content)
    assert payload["details"][0]["account_item_id"] == 30  # AI推定の科目


@respx.mock
def test_expense_sync_falls_back_to_default_when_ai_fails(client, db_session, monkeypatch):
    """AI呼び出しが失敗してもデフォルト科目（雑費）で同期が成立する"""
    _enable_ai(monkeypatch)
    _connect_freee(db_session)
    respx.get(f"{API_BASE}/api/1/account_items").mock(
        return_value=httpx.Response(200, json={"account_items": [
            {"id": 50, "name": "雑費"},
        ]})
    )
    deal_route = respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 5678}})
    )
    _stub_client(monkeypatch, parse_error=RuntimeError("AI unavailable"))

    expense_id = client.post("/api/v1/accounting/expenses", json={
        "expense_date": "2026-05-10", "amount": 800, "category": "未知カテゴリ",
    }).json()["id"]

    response = client.post(f"/api/v1/accounting/expenses/{expense_id}/sync")
    assert response.status_code == 200

    import json
    payload = json.loads(deal_route.calls[0].request.content)
    assert payload["details"][0]["account_item_id"] == 50  # デフォルト「雑費」


@respx.mock
def test_sales_sync_uses_ai_when_no_mapping(client, db_session, monkeypatch):
    """マッピング未定義の売上同期で、AI推定の勘定科目が使われる"""
    _enable_ai(monkeypatch)
    _connect_freee(db_session)
    db_session.add(Order(order_id="O1", user_id="U1", order_date=date(2026, 5, 1),
                         order_type=OrderType.SUBSCRIPTION, total_amount=Decimal("5000")))
    db_session.commit()

    respx.get(f"{API_BASE}/api/1/account_items").mock(
        return_value=httpx.Response(200, json={"account_items": [
            {"id": 77, "name": "売上高（定期便）"},
            {"id": 78, "name": "売上高"},
        ]})
    )
    deal_route = respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 9999}})
    )
    _stub_client(monkeypatch, parsed=AccountItemSuggestion(
        account_item_id=77, account_item_name="売上高（定期便）",
        confidence=0.92, reason="定期便売上のため",
    ))

    response = client.post("/api/v1/accounting/sales/sync", json={
        "start_date": "2026-05-01", "end_date": "2026-05-31", "dry_run": False,
    })
    assert response.status_code == 200
    assert response.json()["synced"] == 1

    import json
    payload = json.loads(deal_route.calls[0].request.content)
    assert payload["details"][0]["account_item_id"] == 77  # AI推定の科目


# --- ai_service単体 ---

@pytest.mark.asyncio
async def test_get_client_raises_without_key(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    with pytest.raises(ai_service.AINotConfiguredError):
        ai_service._get_client()


@pytest.mark.asyncio
async def test_generate_monthly_summary_rejects_empty_response(monkeypatch):
    _enable_ai(monkeypatch)
    _stub_client(monkeypatch, text="   ")
    with pytest.raises(ValueError):
        await ai_service.generate_monthly_summary(
            year=2026, month=5, sales=[], total_sales=0, total_expenses=0,
            expense_by_category=[], sync_stats={},
        )
