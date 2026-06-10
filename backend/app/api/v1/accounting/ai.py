"""
AI経理アシスタント API（Claude API利用）
"""
import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import JournalEntryStatus
from app.services import ai_service, report_service
from app.services.freee_client import (
    FreeeAPIClient,
    FreeeAPIError,
    FreeeNotConnectedError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class SuggestAccountItemRequest(BaseModel):
    description: str = ""
    category: str = Field(..., min_length=1, max_length=100)
    transaction_type: str = Field(default="expense", pattern="^(income|expense)$")


class SuggestAccountItemResponse(BaseModel):
    account_item_id: int
    account_item_name: str
    confidence: float
    reason: str


class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    summary: str


def _handle_ai_errors(e: Exception) -> None:
    if isinstance(e, ai_service.AINotConfiguredError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    if isinstance(e, anthropic.RateLimitError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Claude APIのレート制限に達しました。しばらく待って再実行してください。",
        )
    if isinstance(e, anthropic.APIError):
        logger.error(f"Claude API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Claude APIの呼び出しに失敗しました。時間をおいて再実行してください。",
        )
    if isinstance(e, ValueError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    raise e


@router.get("/ai/status")
async def ai_status():
    """AI機能の設定状態を返す"""
    return {
        "configured": ai_service.is_configured(),
        "model": settings.anthropic_model if ai_service.is_configured() else None,
    }


@router.post("/ai/suggest-account-item", response_model=SuggestAccountItemResponse)
async def suggest_account_item(
    request: SuggestAccountItemRequest, db: Session = Depends(get_db)
):
    """
    取引内容からClaudeが最適な勘定科目を推定する。
    freeeの勘定科目一覧を候補として使うため、freee接続が必要。
    """
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が未設定です。backend/.env に設定してください。",
        )

    try:
        client = FreeeAPIClient(db)
        account_items = await client.get_account_items()
    except FreeeNotConnectedError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except FreeeAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"freee勘定科目の取得に失敗しました（{e.status_code}）",
        )

    if not account_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="freeeから勘定科目を取得できませんでした",
        )

    try:
        suggestion = await ai_service.suggest_account_item(
            description=request.description,
            category=request.category,
            transaction_type=request.transaction_type,
            account_items=account_items,
        )
    except Exception as e:
        _handle_ai_errors(e)

    return SuggestAccountItemResponse(**suggestion.model_dump())


@router.get("/ai/monthly-summary", response_model=MonthlySummaryResponse)
async def monthly_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    """月次データをClaudeが分析し、経営者向けサマリーを生成する"""
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が未設定です。backend/.env に設定してください。",
        )

    data = report_service.collect_monthly_data(db, year, month)

    # 前月の売上合計（前月比コメント用）
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_data = report_service.collect_monthly_data(db, prev_year, prev_month)
    prev_total = float(prev_data["total_sales"]) if prev_data["sales"] else None

    sync_stats = {
        "synced": sum(1 for j in data["journal_entries"] if j.status == JournalEntryStatus.SYNCED),
        "failed": sum(1 for j in data["journal_entries"] if j.status == JournalEntryStatus.FAILED),
        "pending": sum(1 for j in data["journal_entries"] if j.status == JournalEntryStatus.PENDING),
    }

    try:
        summary = await ai_service.generate_monthly_summary(
            year=year,
            month=month,
            sales=[
                {
                    "period": s["period"],
                    "order_type": s["order_type"],
                    "amount": float(s["amount"]),
                    "order_count": s["order_count"],
                }
                for s in data["sales"]
            ],
            total_sales=float(data["total_sales"]),
            total_expenses=float(data["total_expenses"]),
            expense_by_category=[
                {"category": category, "amount": float(amount), "count": count}
                for category, amount, count in data["expense_by_category"]
            ],
            sync_stats=sync_stats,
            prev_month_sales=prev_total,
        )
    except Exception as e:
        _handle_ai_errors(e)

    return MonthlySummaryResponse(year=year, month=month, summary=summary)
