"""
accounting_service のテスト（売上集計・勘定科目推定・冪等性）
"""
from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from app.config import settings
from app.models import (
    AccountItemMapping,
    JournalEntry,
    JournalEntryStatus,
    MappingType,
    Order,
    OrderItem,
    OrderType,
    Product,
)
from app.services import accounting_service, freee_token_store
from app.services.accounting_service import AccountItemResolver
from app.services.freee_client import FreeeAPIClient

API_BASE = settings.freee_api_base_url


def _seed_orders(db):
    db.add(Product(sku="VEG001", product_name="野菜セット"))
    db.add_all(
        [
            Order(
                order_id="O1",
                user_id="U1",
                order_date=date(2026, 5, 1),
                order_type=OrderType.SUBSCRIPTION,
                total_amount=Decimal("3000"),
            ),
            Order(
                order_id="O2",
                user_id="U2",
                order_date=date(2026, 5, 1),
                order_type=OrderType.SUBSCRIPTION,
                total_amount=Decimal("2000"),
            ),
            Order(
                order_id="O3",
                user_id="U3",
                order_date=date(2026, 5, 1),
                order_type=OrderType.ONEOFF,
                total_amount=Decimal("1500"),
            ),
            # total_amount NULL → 明細からフォールバック集計される注文
            Order(
                order_id="O4",
                user_id="U4",
                order_date=date(2026, 5, 2),
                order_type=OrderType.ONEOFF,
                total_amount=None,
            ),
        ]
    )
    db.add(
        OrderItem(
            order_id="O4",
            sku="VEG001",
            quantity=2,
            unit_price=Decimal("1000"),
            discount_rate=Decimal("0.1"),
        )
    )
    db.commit()


def test_aggregate_sales_daily(db_session):
    _seed_orders(db_session)
    results = accounting_service.aggregate_sales(
        db_session, date(2026, 5, 1), date(2026, 5, 31), "daily"
    )
    by_key = {(r["period"], r["order_type"]): r for r in results}
    assert by_key[("2026-05-01", "subscription")]["amount"] == Decimal("5000.00")
    assert by_key[("2026-05-01", "subscription")]["order_count"] == 2
    assert by_key[("2026-05-01", "oneoff")]["amount"] == Decimal("1500.00")
    # NULLフォールバック: 2 × 1000 × (1 - 0.1) = 1800
    assert by_key[("2026-05-02", "oneoff")]["amount"] == Decimal("1800.00")


def test_aggregate_sales_monthly(db_session):
    _seed_orders(db_session)
    results = accounting_service.aggregate_sales(
        db_session, date(2026, 5, 1), date(2026, 5, 31), "monthly"
    )
    by_type = {r["order_type"]: r for r in results}
    assert by_type["subscription"]["amount"] == Decimal("5000.00")
    assert by_type["oneoff"]["amount"] == Decimal("3300.00")
    assert all(r["period"] == "2026-05" for r in results)


def test_resolver_exact_match_wins_over_keywords(db_session):
    db_session.add_all(
        [
            AccountItemMapping(
                mapping_type=MappingType.SALES_CATEGORY,
                source_key="subscription",
                freee_account_item_id=10,
                freee_account_item_name="売上高（定期）",
            ),
            AccountItemMapping(
                mapping_type=MappingType.SALES_CATEGORY,
                source_key="other",
                keywords="subscription,定期",
                priority=100,
                freee_account_item_id=20,
                freee_account_item_name="その他売上",
            ),
        ]
    )
    db_session.commit()
    resolver = AccountItemResolver(db_session, MappingType.SALES_CATEGORY)
    assert resolver.resolve("subscription").freee_account_item_id == 10


def test_resolver_keyword_match(db_session):
    db_session.add(
        AccountItemMapping(
            mapping_type=MappingType.EXPENSE_CATEGORY,
            source_key="交通費",
            keywords="タクシー,電車,バス",
            freee_account_item_id=30,
            freee_account_item_name="旅費交通費",
        )
    )
    db_session.commit()
    resolver = AccountItemResolver(db_session, MappingType.EXPENSE_CATEGORY)
    found = resolver.resolve("その他", "帰社時のタクシー代")
    assert found.freee_account_item_id == 30
    assert resolver.resolve("その他", "該当なしの摘要") is None


def test_build_sales_journal_entries_marks_synced(db_session):
    _seed_orders(db_session)
    db_session.add(
        JournalEntry(
            source_type="sales_daily",
            source_key="2026-05-01:subscription",
            entry_type="sales",
            entry_date=date(2026, 5, 1),
            amount=Decimal("5000"),
            status=JournalEntryStatus.SYNCED,
        )
    )
    db_session.commit()

    entries = accounting_service.build_sales_journal_entries(
        db_session, date(2026, 5, 1), date(2026, 5, 31), "daily"
    )
    by_key = {e["source_key"]: e for e in entries}
    assert by_key["2026-05-01:subscription"]["already_synced"] is True
    assert by_key["2026-05-01:oneoff"]["already_synced"] is False


@pytest.mark.asyncio
@respx.mock
async def test_sync_sales_to_freee_idempotent(db_session):
    """同期→再同期で二重登録されないこと（冪等性）"""
    _seed_orders(db_session)
    db_session.add(
        AccountItemMapping(
            mapping_type=MappingType.SALES_CATEGORY,
            source_key="subscription",
            freee_account_item_id=10,
            freee_account_item_name="売上高",
            freee_tax_code=21,
        )
    )
    db_session.add(
        AccountItemMapping(
            mapping_type=MappingType.SALES_CATEGORY,
            source_key="oneoff",
            freee_account_item_id=11,
            freee_account_item_name="売上高",
            freee_tax_code=21,
        )
    )
    db_session.commit()
    token = freee_token_store.save_token(
        db_session,
        company_id=101,
        access_token="a",
        refresh_token="r",
        expires_in=21600,
    )

    deal_route = respx.post(f"{API_BASE}/api/1/deals").mock(
        return_value=httpx.Response(201, json={"deal": {"id": 7777}})
    )
    client = FreeeAPIClient(db_session, token)

    result1 = await accounting_service.sync_sales_to_freee(
        db_session, client, date(2026, 5, 1), date(2026, 5, 31), "daily"
    )
    assert result1["synced"] == 3
    assert result1["failed"] == 0
    first_call_count = deal_route.call_count

    # 再実行 → 全てスキップされ、freee APIは呼ばれない
    result2 = await accounting_service.sync_sales_to_freee(
        db_session, client, date(2026, 5, 1), date(2026, 5, 31), "daily"
    )
    assert result2["synced"] == 0
    assert result2["skipped"] == 3
    assert deal_route.call_count == first_call_count

    entries = db_session.query(JournalEntry).all()
    assert len(entries) == 3
    assert all(e.status == JournalEntryStatus.SYNCED for e in entries)
    assert all(e.freee_deal_id == 7777 for e in entries)


@pytest.mark.asyncio
@respx.mock
async def test_sync_sales_records_failure_and_continues(db_session):
    """1件失敗しても残りは同期され、失敗はFAILEDで記録される"""
    _seed_orders(db_session)
    db_session.add(
        AccountItemMapping(
            mapping_type=MappingType.SALES_CATEGORY,
            source_key="subscription",
            freee_account_item_id=10,
            freee_account_item_name="売上高",
        )
    )
    db_session.add(
        AccountItemMapping(
            mapping_type=MappingType.SALES_CATEGORY,
            source_key="oneoff",
            freee_account_item_id=11,
            freee_account_item_name="売上高",
        )
    )
    db_session.commit()
    token = freee_token_store.save_token(
        db_session,
        company_id=101,
        access_token="a",
        refresh_token="r",
        expires_in=21600,
    )

    respx.post(f"{API_BASE}/api/1/deals").mock(
        side_effect=[
            httpx.Response(400, json={"errors": [{"messages": ["invalid"]}]}),
            httpx.Response(201, json={"deal": {"id": 1}}),
            httpx.Response(201, json={"deal": {"id": 2}}),
        ]
    )
    client = FreeeAPIClient(db_session, token)
    result = await accounting_service.sync_sales_to_freee(
        db_session, client, date(2026, 5, 1), date(2026, 5, 31), "daily"
    )
    assert result["synced"] == 2
    assert result["failed"] == 1

    failed = (
        db_session.query(JournalEntry)
        .filter(JournalEntry.status == JournalEntryStatus.FAILED)
        .all()
    )
    assert len(failed) == 1
    assert failed[0].error_message
