"""
経理業務サービス

- 売上集計（orders → 日次/月次）
- 勘定科目の自動推定（AccountItemMapping）
- 仕訳（JournalEntry）の生成とfreeeへの取引（deal）登録
- 経費（Expense）のfreee同期
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    AccountItemMapping,
    Expense,
    ExpenseStatus,
    JournalEntry,
    JournalEntryStatus,
    JournalEntryType,
    MappingType,
    Order,
    OrderItem,
    OrderType,
)
from app.services import ai_service
from app.services.freee_client import FreeeAPIClient, FreeeAPIError

logger = logging.getLogger(__name__)

# マッピング未定義時のデフォルト勘定科目名（freee標準の勘定科目）
DEFAULT_SALES_ACCOUNT_NAME = "売上高"
DEFAULT_EXPENSE_ACCOUNT_NAME = "雑費"

ORDER_TYPE_LABELS = {
    OrderType.SUBSCRIPTION: "定期便売上",
    OrderType.ONEOFF: "単発売上",
}


class AccountItemResolver:
    """勘定科目の自動推定"""

    def __init__(self, db: Session, mapping_type: MappingType):
        self.mappings = (
            db.query(AccountItemMapping)
            .filter(
                AccountItemMapping.mapping_type == mapping_type,
                AccountItemMapping.active == True,  # noqa: E712
            )
            .order_by(AccountItemMapping.priority.desc())
            .all()
        )

    def resolve(
        self, source_key: str, description: str = ""
    ) -> Optional[AccountItemMapping]:
        """
        勘定科目を推定する。
        1. source_key の完全一致
        2. keywords（カンマ区切り）の部分一致（priority降順）
        """
        for mapping in self.mappings:
            if mapping.source_key == source_key:
                return mapping
        text = f"{source_key} {description}"
        for mapping in self.mappings:
            if not mapping.keywords:
                continue
            keywords = [k.strip() for k in mapping.keywords.split(",") if k.strip()]
            if any(keyword in text for keyword in keywords):
                return mapping
        return None


def aggregate_sales(
    db: Session,
    start_date: date,
    end_date: date,
    granularity: str = "daily",
) -> List[Dict[str, Any]]:
    """
    注文データを日次/月次 × 注文タイプで集計する。
    total_amount が NULL の注文は明細（quantity × unit_price × (1 - discount_rate)）から算出。
    """
    if granularity == "monthly":
        if db.get_bind().dialect.name == "sqlite":
            period_expr = func.strftime("%Y-%m", Order.order_date)
        else:
            period_expr = func.to_char(Order.order_date, "YYYY-MM")
    else:
        period_expr = Order.order_date

    # 明細からのフォールバック金額（total_amount が NULL の注文用）
    item_total = (
        db.query(
            OrderItem.order_id.label("order_id"),
            func.sum(
                OrderItem.quantity
                * func.coalesce(OrderItem.unit_price, 0)
                * (1 - func.coalesce(OrderItem.discount_rate, 0))
            ).label("items_amount"),
        )
        .group_by(OrderItem.order_id)
        .subquery()
    )

    rows = (
        db.query(
            period_expr.label("period"),
            Order.order_type.label("order_type"),
            func.sum(
                func.coalesce(Order.total_amount, item_total.c.items_amount, 0)
            ).label("amount"),
            func.count(Order.order_id).label("order_count"),
        )
        .outerjoin(item_total, Order.order_id == item_total.c.order_id)
        .filter(Order.order_date >= start_date, Order.order_date <= end_date)
        .group_by("period", Order.order_type)
        .order_by("period")
        .all()
    )

    results = []
    for row in rows:
        period = row.period if isinstance(row.period, str) else row.period.isoformat()
        results.append(
            {
                "period": period,
                "order_type": row.order_type.value
                if hasattr(row.order_type, "value")
                else str(row.order_type),
                "amount": Decimal(row.amount or 0).quantize(Decimal("0.01")),
                "order_count": row.order_count,
            }
        )
    return results


def build_sales_journal_entries(
    db: Session,
    start_date: date,
    end_date: date,
    granularity: str = "daily",
) -> List[Dict[str, Any]]:
    """
    売上集計から仕訳候補（プレビュー）を生成する。
    既存のJournalEntry（SYNCED/PENDING）と重複するものは skip 扱いにする。
    """
    resolver = AccountItemResolver(db, MappingType.SALES_CATEGORY)
    source_type = f"sales_{granularity}"
    aggregates = aggregate_sales(db, start_date, end_date, granularity)

    entries = []
    for agg in aggregates:
        if agg["amount"] <= 0:
            continue
        order_type = agg["order_type"]
        source_key = f"{agg['period']}:{order_type}"
        label = ORDER_TYPE_LABELS.get(OrderType(order_type), "売上")
        description = f"{agg['period']} {label}（需要予測システム自動連携 / {agg['order_count']}件）"

        existing = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.source_type == source_type,
                JournalEntry.source_key == source_key,
            )
            .first()
        )

        mapping = resolver.resolve(order_type, description)
        entries.append(
            {
                "source_type": source_type,
                "source_key": source_key,
                "category": order_type,
                "entry_date": agg["period"]
                if granularity == "daily"
                else f"{agg['period']}-01",
                "description": description,
                "amount": agg["amount"],
                "order_count": agg["order_count"],
                "account_item_id": mapping.freee_account_item_id if mapping else None,
                "account_item_name": (
                    mapping.freee_account_item_name
                    if mapping
                    else DEFAULT_SALES_ACCOUNT_NAME
                ),
                "tax_code": mapping.freee_tax_code if mapping else None,
                "partner_id": mapping.freee_partner_id if mapping else None,
                "already_synced": existing is not None
                and existing.status == JournalEntryStatus.SYNCED,
                "existing_status": existing.status.value if existing else None,
            }
        )
    return entries


async def resolve_default_account_item_id(
    client: FreeeAPIClient, account_name: str
) -> Optional[int]:
    """freeeの勘定科目一覧から名前一致でIDを解決する"""
    account_items = await client.get_account_items()
    return _find_account_item_by_name(account_items, account_name)


def _find_account_item_by_name(
    account_items: List[Dict[str, Any]], account_name: str
) -> Optional[int]:
    for item in account_items:
        if item.get("name") == account_name:
            return item.get("id")
    return None


async def _ai_suggest_account_item(
    account_items: List[Dict[str, Any]],
    description: str,
    category: str,
    transaction_type: str,
) -> Optional[ai_service.AccountItemSuggestion]:
    """AI推定（未設定・失敗時はNoneを返し、呼び出し側がデフォルト科目にフォールバックする）"""
    if not ai_service.is_configured():
        return None
    try:
        return await ai_service.suggest_account_item(
            description=description,
            category=category,
            transaction_type=transaction_type,
            account_items=account_items,
        )
    except Exception as e:
        logger.warning(
            f"AI account item suggestion failed, falling back to default: {e}"
        )
        return None


def _build_deal_payload(
    issue_date: str,
    deal_type: str,
    amount: Decimal,
    account_item_id: int,
    description: str,
    tax_code: Optional[int],
    partner_id: Optional[int],
) -> Dict[str, Any]:
    """freee取引（deal）登録ペイロードを組み立てる"""
    detail: Dict[str, Any] = {
        "account_item_id": account_item_id,
        "amount": int(amount),
        "description": description[:255],
    }
    if tax_code is not None:
        detail["tax_code"] = tax_code
    payload: Dict[str, Any] = {
        "issue_date": issue_date,
        "type": deal_type,
        "details": [detail],
    }
    if partner_id is not None:
        payload["partner_id"] = partner_id
    return payload


async def sync_sales_to_freee(
    db: Session,
    client: FreeeAPIClient,
    start_date: date,
    end_date: date,
    granularity: str = "daily",
) -> Dict[str, Any]:
    """
    売上集計をfreeeに収入取引として登録する。

    - UNIQUE(source_type, source_key) により再実行しても二重登録されない
    - SYNCED済みはスキップ、PENDING/FAILEDは再送
    - 1件ずつコミットし、途中で失敗しても成功分は確定する
    """
    candidates = build_sales_journal_entries(db, start_date, end_date, granularity)
    default_account_item_id: Optional[int] = None
    account_items_cache: Optional[List[Dict[str, Any]]] = None

    synced, skipped, failed = 0, 0, 0
    results = []

    for candidate in candidates:
        if candidate["already_synced"]:
            skipped += 1
            results.append({**_summary(candidate), "status": "skipped"})
            continue

        entry = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.source_type == candidate["source_type"],
                JournalEntry.source_key == candidate["source_key"],
            )
            .first()
        )
        if entry is None:
            entry = JournalEntry(
                source_type=candidate["source_type"],
                source_key=candidate["source_key"],
                entry_type=JournalEntryType.SALES,
            )
            db.add(entry)

        entry.entry_date = datetime.strptime(candidate["entry_date"], "%Y-%m-%d").date()
        entry.description = candidate["description"]
        entry.amount = candidate["amount"]
        entry.freee_company_id = client.company_id

        try:
            account_item_id = candidate["account_item_id"]
            if account_item_id is None:
                # マッピング未定義 → AI推定（設定時）→ デフォルト勘定科目の順でフォールバック
                if account_items_cache is None:
                    account_items_cache = await client.get_account_items()
                suggestion = await _ai_suggest_account_item(
                    account_items_cache,
                    description=candidate["description"],
                    category=candidate["category"],
                    transaction_type="income",
                )
                if suggestion is not None:
                    account_item_id = suggestion.account_item_id
                    candidate["account_item_name"] = suggestion.account_item_name
                else:
                    if default_account_item_id is None:
                        default_account_item_id = _find_account_item_by_name(
                            account_items_cache, DEFAULT_SALES_ACCOUNT_NAME
                        )
                    if default_account_item_id is None:
                        raise ValueError(
                            f"勘定科目マッピングが未定義で、freee側に"
                            f"「{DEFAULT_SALES_ACCOUNT_NAME}」も見つかりません。"
                            "マッピングを登録してください。"
                        )
                    account_item_id = default_account_item_id

            payload = _build_deal_payload(
                issue_date=candidate["entry_date"],
                deal_type="income",
                amount=candidate["amount"],
                account_item_id=account_item_id,
                description=candidate["description"],
                tax_code=candidate["tax_code"],
                partner_id=candidate["partner_id"],
            )
            entry.details = payload

            deal = await client.create_deal(payload)
            entry.freee_deal_id = deal.get("id")
            entry.status = JournalEntryStatus.SYNCED
            entry.error_message = None
            entry.synced_at = datetime.now(timezone.utc)
            synced += 1
            results.append(
                {
                    **_summary(candidate),
                    "status": "synced",
                    "freee_deal_id": entry.freee_deal_id,
                }
            )
        except (FreeeAPIError, ValueError) as e:
            entry.status = JournalEntryStatus.FAILED
            entry.error_message = str(e)[:2000]
            failed += 1
            results.append({**_summary(candidate), "status": "failed", "error": str(e)})
            logger.error(f"sales sync failed for {candidate['source_key']}: {e}")

        db.commit()

    return {
        "total": len(candidates),
        "synced": synced,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


def _summary(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_key": candidate["source_key"],
        "entry_date": candidate["entry_date"],
        "description": candidate["description"],
        "amount": float(candidate["amount"]),
        "account_item_name": candidate["account_item_name"],
    }


async def sync_expense_to_freee(
    db: Session,
    client: FreeeAPIClient,
    expense: Expense,
) -> Expense:
    """経費1件をfreeeに支出取引として登録する"""
    if expense.status == ExpenseStatus.SYNCED:
        return expense

    resolver = AccountItemResolver(db, MappingType.EXPENSE_CATEGORY)
    mapping = resolver.resolve(expense.category, expense.description or "")

    try:
        if mapping is not None:
            account_item_id = mapping.freee_account_item_id
            tax_code = mapping.freee_tax_code
            partner_id = mapping.freee_partner_id
        else:
            # マッピング未定義 → AI推定（設定時）→ デフォルト勘定科目の順でフォールバック
            tax_code = None
            partner_id = None
            account_items = await client.get_account_items()
            suggestion = await _ai_suggest_account_item(
                account_items,
                description=expense.description or "",
                category=expense.category,
                transaction_type="expense",
            )
            if suggestion is not None:
                account_item_id = suggestion.account_item_id
            else:
                account_item_id = _find_account_item_by_name(
                    account_items, DEFAULT_EXPENSE_ACCOUNT_NAME
                )
                if account_item_id is None:
                    raise ValueError(
                        f"経費カテゴリ「{expense.category}」のマッピングが未定義で、"
                        f"freee側に「{DEFAULT_EXPENSE_ACCOUNT_NAME}」も見つかりません。"
                    )

        description = f"{expense.category} {expense.description or ''}".strip()
        payload = _build_deal_payload(
            issue_date=expense.expense_date.isoformat(),
            deal_type="expense",
            amount=expense.amount,
            account_item_id=account_item_id,
            description=description,
            tax_code=tax_code,
            partner_id=partner_id,
        )
        deal = await client.create_deal(payload)
        expense.freee_deal_id = deal.get("id")
        expense.status = ExpenseStatus.SYNCED

        # 仕訳ログも残す（売上と同じjournal_entriesで一元管理）
        source_key = f"expense:{expense.id}"
        entry = (
            db.query(JournalEntry)
            .filter(
                JournalEntry.source_type == "expense",
                JournalEntry.source_key == source_key,
            )
            .first()
        )
        if entry is None:
            entry = JournalEntry(source_type="expense", source_key=source_key)
            db.add(entry)
        entry.entry_type = JournalEntryType.EXPENSE
        entry.entry_date = expense.expense_date
        entry.description = description
        entry.amount = expense.amount
        entry.details = payload
        entry.freee_company_id = client.company_id
        entry.freee_deal_id = expense.freee_deal_id
        entry.status = JournalEntryStatus.SYNCED
        entry.error_message = None
        entry.synced_at = datetime.now(timezone.utc)
    except (FreeeAPIError, ValueError) as e:
        expense.status = ExpenseStatus.FAILED
        logger.error(f"expense sync failed for expense_id={expense.id}: {e}")
        db.commit()
        raise

    db.commit()
    db.refresh(expense)
    return expense
