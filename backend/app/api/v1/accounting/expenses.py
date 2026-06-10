"""
経費管理 API（CRUD + freee同期）
"""
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expense, ExpenseStatus
from app.services import accounting_service
from app.services.freee_client import (
    FreeeAPIClient,
    FreeeAPIError,
    FreeeNotConnectedError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ExpenseRequest(BaseModel):
    expense_date: date
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    payment_method: str = Field(default="cash", pattern="^(cash|credit_card|bank_transfer)$")
    partner_name: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    expense_date: date
    amount: float
    category: str
    description: Optional[str] = None
    payment_method: Optional[str] = None
    partner_name: Optional[str] = None
    status: ExpenseStatus
    freee_deal_id: Optional[int] = None

    class Config:
        from_attributes = True


def _get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="経費が見つかりません")
    return expense


@router.get("/expenses", response_model=List[ExpenseResponse])
async def list_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[ExpenseStatus] = Query(default=None, alias="status"),
    category: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """経費一覧（期間・ステータス・カテゴリでフィルタ）"""
    query = db.query(Expense)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if status_filter:
        query = query.filter(Expense.status == status_filter)
    if category:
        query = query.filter(Expense.category == category)
    return (
        query.order_by(Expense.expense_date.desc(), Expense.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(request: ExpenseRequest, db: Session = Depends(get_db)):
    """経費を登録する"""
    expense = Expense(**request.model_dump(), status=ExpenseStatus.DRAFT)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int, request: ExpenseRequest, db: Session = Depends(get_db)
):
    """経費を更新する（freee同期済みの経費は更新不可）"""
    expense = _get_expense(db, expense_id)
    if expense.status == ExpenseStatus.SYNCED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="freee登録済みの経費は更新できません。freee側で修正してください。",
        )
    for key, value in request.model_dump().items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """経費を削除する（freee同期済みの経費は削除不可）"""
    expense = _get_expense(db, expense_id)
    if expense.status == ExpenseStatus.SYNCED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="freee登録済みの経費は削除できません。freee側で取引を削除してください。",
        )
    db.delete(expense)
    db.commit()
    return {"deleted": expense_id}


@router.post("/expenses/{expense_id}/sync", response_model=ExpenseResponse)
async def sync_expense(expense_id: int, db: Session = Depends(get_db)):
    """経費1件をfreeeに支出取引として登録する"""
    expense = _get_expense(db, expense_id)
    if expense.status == ExpenseStatus.SYNCED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="既にfreeeに登録済みです")

    try:
        client = FreeeAPIClient(db)
    except FreeeNotConnectedError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    try:
        expense = await accounting_service.sync_expense_to_freee(db, client, expense)
    except (FreeeAPIError, ValueError) as e:
        detail = (
            f"freee APIエラー（{e.status_code}）: {e.message[:500]}"
            if isinstance(e, FreeeAPIError)
            else str(e)
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
    return expense
