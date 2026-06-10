"""
経理APIエンドポイントのテスト
"""
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import httpx
import respx

from app.config import settings
from app.models import Expense, ExpenseStatus, Order, OrderType
from app.services import freee_token_store

API_BASE = settings.freee_api_base_url


def _connect_freee(db):
    return freee_token_store.save_token(
        db, company_id=101, access_token="a", refresh_token="r", expires_in=21600,
        company_name="テスト事業所",
    )


# --- freee接続管理 ---

def test_auth_url(client):
    response = client.get("/api/v1/accounting/freee/auth-url")
    assert response.status_code == 200
    url = urlparse(response.json()["auth_url"])
    assert url.netloc == "accounts.secure.freee.co.jp"
    assert "state" in parse_qs(url.query)


def test_callback_rejects_invalid_state(client):
    response = client.get(
        "/api/v1/accounting/freee/callback",
        params={"code": "abc", "state": "invalid-state"},
    )
    assert response.status_code == 400


def test_status_not_connected(client):
    response = client.get("/api/v1/accounting/freee/status")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["connected"] is False
    assert body["companies"] == []


def test_status_connected(client, db_session):
    _connect_freee(db_session)
    body = client.get("/api/v1/accounting/freee/status").json()
    assert body["connected"] is True
    assert body["companies"][0]["company_id"] == 101
    assert body["companies"][0]["is_active"] is True


def test_select_company_and_disconnect(client, db_session):
    _connect_freee(db_session)
    freee_token_store.save_token(
        db_session, company_id=202, access_token="a", refresh_token="r", expires_in=21600
    )

    response = client.post("/api/v1/accounting/freee/company", json={"company_id": 202})
    assert response.status_code == 200
    active = [c for c in response.json()["companies"] if c["is_active"]]
    assert active[0]["company_id"] == 202

    assert client.post("/api/v1/accounting/freee/company", json={"company_id": 999}).status_code == 404

    response = client.post("/api/v1/accounting/freee/disconnect")
    assert response.status_code == 200
    assert response.json()["deleted"] == 2


def test_account_items_requires_connection(client):
    response = client.get("/api/v1/accounting/account-items")
    assert response.status_code == 503


# --- 勘定科目マッピング ---

def test_mapping_crud_and_suggest(client):
    payload = {
        "mapping_type": "sales_category",
        "source_key": "subscription",
        "keywords": "定期便,サブスク",
        "freee_account_item_id": 10,
        "freee_account_item_name": "売上高（定期）",
        "freee_tax_code": 21,
    }
    response = client.post("/api/v1/accounting/mappings", json=payload)
    assert response.status_code == 201
    mapping_id = response.json()["id"]

    # 重複登録は409
    assert client.post("/api/v1/accounting/mappings", json=payload).status_code == 409

    # 一覧
    response = client.get("/api/v1/accounting/mappings", params={"mapping_type": "sales_category"})
    assert len(response.json()) == 1

    # 推定（完全一致）
    response = client.post("/api/v1/accounting/mappings/suggest", json={
        "mapping_type": "sales_category", "source_key": "subscription",
    })
    assert response.json()["matched"] is True
    assert response.json()["mapping"]["freee_account_item_id"] == 10

    # 推定（キーワード一致）
    response = client.post("/api/v1/accounting/mappings/suggest", json={
        "mapping_type": "sales_category", "source_key": "unknown", "description": "5月分サブスク売上",
    })
    assert response.json()["matched"] is True

    # 推定（不一致）
    response = client.post("/api/v1/accounting/mappings/suggest", json={
        "mapping_type": "sales_category", "source_key": "unknown", "description": "該当なし",
    })
    assert response.json()["matched"] is False

    # 更新・削除
    payload["freee_account_item_name"] = "売上高"
    assert client.put(f"/api/v1/accounting/mappings/{mapping_id}", json=payload).status_code == 200
    assert client.delete(f"/api/v1/accounting/mappings/{mapping_id}").status_code == 200
    assert client.delete(f"/api/v1/accounting/mappings/{mapping_id}").status_code == 404


# --- 売上同期 ---

def test_sales_sync_dry_run(client, db_session):
    db_session.add(Order(order_id="O1", user_id="U1", order_date=date(2026, 5, 1),
                         order_type=OrderType.SUBSCRIPTION, total_amount=Decimal("5000")))
    db_session.commit()

    response = client.post("/api/v1/accounting/sales/sync", json={
        "start_date": "2026-05-01", "end_date": "2026-05-31",
        "granularity": "daily", "dry_run": True,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["total"] == 1
    assert body["entries"][0]["amount"] == 5000.0
    assert body["entries"][0]["already_synced"] is False


def test_sales_sync_requires_connection_when_not_dry_run(client, db_session):
    response = client.post("/api/v1/accounting/sales/sync", json={
        "start_date": "2026-05-01", "end_date": "2026-05-31", "dry_run": False,
    })
    assert response.status_code == 503


def test_sales_sync_rejects_invalid_date_range(client):
    response = client.post("/api/v1/accounting/sales/sync", json={
        "start_date": "2026-05-31", "end_date": "2026-05-01", "dry_run": True,
    })
    assert response.status_code == 422


@respx.mock
def test_sales_sync_real_run(client, db_session):
    db_session.add(Order(order_id="O1", user_id="U1", order_date=date(2026, 5, 1),
                         order_type=OrderType.SUBSCRIPTION, total_amount=Decimal("5000")))
    db_session.commit()
    _connect_freee(db_session)
    client_payload = {
        "mapping_type": "sales_category", "source_key": "subscription",
        "freee_account_item_id": 10, "freee_account_item_name": "売上高",
    }
    assert client.post("/api/v1/accounting/mappings", json=client_payload).status_code == 201

    respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 8888}})
    )
    response = client.post("/api/v1/accounting/sales/sync", json={
        "start_date": "2026-05-01", "end_date": "2026-05-31", "dry_run": False,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["synced"] == 1

    # 仕訳一覧に反映される
    entries = client.get("/api/v1/accounting/journal-entries").json()
    assert len(entries) == 1
    assert entries[0]["status"] == "synced"
    assert entries[0]["freee_deal_id"] == 8888


# --- 経費 ---

def test_expense_crud(client):
    payload = {
        "expense_date": "2026-05-10", "amount": 1200, "category": "交通費",
        "description": "客先訪問のタクシー代", "payment_method": "cash",
    }
    response = client.post("/api/v1/accounting/expenses", json=payload)
    assert response.status_code == 201
    expense_id = response.json()["id"]
    assert response.json()["status"] == "draft"

    # バリデーション: 金額0以下は422
    assert client.post("/api/v1/accounting/expenses", json={**payload, "amount": 0}).status_code == 422

    # 一覧・フィルタ
    assert len(client.get("/api/v1/accounting/expenses").json()) == 1
    assert len(client.get("/api/v1/accounting/expenses", params={"category": "会議費"}).json()) == 0

    # 更新
    response = client.put(f"/api/v1/accounting/expenses/{expense_id}", json={**payload, "amount": 1500})
    assert response.status_code == 200
    assert response.json()["amount"] == 1500.0

    # 削除
    assert client.delete(f"/api/v1/accounting/expenses/{expense_id}").status_code == 200
    assert client.get("/api/v1/accounting/expenses").json() == []


def test_expense_synced_cannot_be_modified(client, db_session):
    expense = Expense(expense_date=date(2026, 5, 10), amount=Decimal("1000"),
                      category="交通費", status=ExpenseStatus.SYNCED, freee_deal_id=1)
    db_session.add(expense)
    db_session.commit()

    payload = {"expense_date": "2026-05-10", "amount": 1000, "category": "交通費"}
    assert client.put(f"/api/v1/accounting/expenses/{expense.id}", json=payload).status_code == 409
    assert client.delete(f"/api/v1/accounting/expenses/{expense.id}").status_code == 409
    assert client.post(f"/api/v1/accounting/expenses/{expense.id}/sync").status_code == 409


@respx.mock
def test_expense_sync(client, db_session):
    _connect_freee(db_session)
    mapping = {
        "mapping_type": "expense_category", "source_key": "交通費",
        "freee_account_item_id": 30, "freee_account_item_name": "旅費交通費",
    }
    assert client.post("/api/v1/accounting/mappings", json=mapping).status_code == 201

    response = client.post("/api/v1/accounting/expenses", json={
        "expense_date": "2026-05-10", "amount": 1200, "category": "交通費",
    })
    expense_id = response.json()["id"]

    respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 5555}})
    )
    response = client.post(f"/api/v1/accounting/expenses/{expense_id}/sync")
    assert response.status_code == 200
    assert response.json()["status"] == "synced"
    assert response.json()["freee_deal_id"] == 5555


# --- レポート ---

def test_monthly_report_xlsx_download(client, db_session):
    db_session.add(Order(order_id="O1", user_id="U1", order_date=date(2026, 5, 1),
                         order_type=OrderType.ONEOFF, total_amount=Decimal("3000")))
    db_session.commit()

    response = client.get("/api/v1/accounting/reports/monthly",
                          params={"year": 2026, "month": 5, "format": "xlsx"})
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert 'monthly_report_2026-05.xlsx' in response.headers["content-disposition"]


def test_monthly_report_csv_download(client, db_session):
    db_session.add(Order(order_id="O1", user_id="U1", order_date=date(2026, 5, 1),
                         order_type=OrderType.ONEOFF, total_amount=Decimal("3000")))
    db_session.commit()

    response = client.get("/api/v1/accounting/reports/monthly",
                          params={"year": 2026, "month": 5, "format": "csv"})
    assert response.status_code == 200
    assert "3000" in response.text


def test_trial_balance_requires_connection(client):
    response = client.get("/api/v1/accounting/reports/trial-balance",
                          params={"year": 2026, "month": 5, "type": "pl"})
    assert response.status_code == 503
