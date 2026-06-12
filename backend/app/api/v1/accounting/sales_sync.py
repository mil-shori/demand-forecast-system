"""
売上→freee取引同期 API
"""
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JournalEntry, JournalEntryStatus, JournalEntryType
from app.services import accounting_service
from app.services.freee_client import (
    FreeeAPIClient,
    FreeeAPIError,
    FreeeNotConnectedError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class SalesSyncRequest(BaseModel):
    start_date: date
    end_date: date
    granularity: str = Field(default="daily", pattern="^(daily|monthly)$")
    dry_run: bool = True


class JournalEntryResponse(BaseModel):
    id: int
    entry_date: date
    entry_type: JournalEntryType
    source_type: str
    source_key: str
    description: Optional[str] = None
    amount: float
    status: JournalEntryStatus
    freee_deal_id: Optional[int] = None
    error_message: Optional[str] = None
    synced_at: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator("synced_at", mode="before")
    @classmethod
    def format_synced_at(cls, v):
        return v.isoformat() if v is not None and not isinstance(v, str) else v


@router.post("/sales/sync")
async def sync_sales(request: SalesSyncRequest, db: Session = Depends(get_db)):
    """
    注文データを集計してfreeeに収入取引として登録する。
    dry_run=true の場合は登録内容のプレビューのみ返す。
    """
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date は start_date 以降の日付を指定してください",
        )
    if request.dry_run:
        entries = accounting_service.build_sales_journal_entries(
            db, request.start_date, request.end_date, request.granularity
        )
        return {
            "dry_run": True,
            "total": len(entries),
            "entries": [
                {
                    "source_key": e["source_key"],
                    "entry_date": e["entry_date"],
                    "description": e["description"],
                    "amount": float(e["amount"]),
                    "order_count": e["order_count"],
                    "account_item_name": e["account_item_name"],
                    "already_synced": e["already_synced"],
                    "existing_status": e["existing_status"],
                }
                for e in entries
            ],
        }

    try:
        client = FreeeAPIClient(db)
    except FreeeNotConnectedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )

    result = await accounting_service.sync_sales_to_freee(
        db, client, request.start_date, request.end_date, request.granularity
    )
    return {"dry_run": False, **result}


@router.get("/journal-entries", response_model=List[JournalEntryResponse])
async def list_journal_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[JournalEntryStatus] = Query(default=None, alias="status"),
    entry_type: Optional[JournalEntryType] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """仕訳一覧（期間・ステータス・種別でフィルタ）"""
    query = db.query(JournalEntry)
    if start_date:
        query = query.filter(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(JournalEntry.entry_date <= end_date)
    if status_filter:
        query = query.filter(JournalEntry.status == status_filter)
    if entry_type:
        query = query.filter(JournalEntry.entry_type == entry_type)
    return (
        query.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/journal-entries/{entry_id}/retry", response_model=JournalEntryResponse)
async def retry_journal_entry(entry_id: int, db: Session = Depends(get_db)):
    """FAILED仕訳をfreeeへ再送する"""
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕訳が見つかりません")
    if entry.status == JournalEntryStatus.SYNCED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="既にfreeeに登録済みです"
        )
    if not entry.details:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="再送用のペイロードがありません。売上同期をやり直してください。",
        )

    try:
        client = FreeeAPIClient(db)
    except FreeeNotConnectedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )

    from datetime import datetime, timezone

    try:
        deal = await client.create_deal(entry.details)
        entry.freee_deal_id = deal.get("id")
        entry.status = JournalEntryStatus.SYNCED
        entry.error_message = None
        entry.synced_at = datetime.now(timezone.utc)
    except FreeeAPIError as e:
        entry.status = JournalEntryStatus.FAILED
        entry.error_message = str(e)[:2000]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"freee APIエラー（{e.status_code}）: {e.message[:500]}",
        )

    db.commit()
    db.refresh(entry)
    return entry
