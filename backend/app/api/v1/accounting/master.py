"""
freeeマスタ（勘定科目・取引先）と勘定科目マッピング API
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccountItemMapping, MappingType
from app.services.accounting_service import AccountItemResolver
from app.services.freee_client import (
    FreeeAPIClient,
    FreeeAPIError,
    FreeeNotConnectedError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class MappingRequest(BaseModel):
    mapping_type: MappingType
    source_key: str = Field(..., min_length=1, max_length=100)
    keywords: Optional[str] = None
    freee_account_item_id: int
    freee_account_item_name: Optional[str] = None
    freee_tax_code: Optional[int] = None
    freee_partner_id: Optional[int] = None
    priority: int = 0
    active: bool = True


class MappingResponse(MappingRequest):
    id: int

    class Config:
        from_attributes = True


class SuggestRequest(BaseModel):
    mapping_type: MappingType
    source_key: str
    description: str = ""


def _get_client(db: Session) -> FreeeAPIClient:
    try:
        return FreeeAPIClient(db)
    except FreeeNotConnectedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )


def _handle_freee_error(e: FreeeAPIError) -> None:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"freee APIエラー（{e.status_code}）: {e.message[:500]}",
    )


@router.get("/account-items")
async def list_account_items(db: Session = Depends(get_db)):
    """freee勘定科目一覧を取得する"""
    client = _get_client(db)
    try:
        items = await client.get_account_items()
    except FreeeAPIError as e:
        _handle_freee_error(e)
    return {"account_items": items}


@router.get("/partners")
async def list_partners(keyword: Optional[str] = None, db: Session = Depends(get_db)):
    """freee取引先一覧を取得する"""
    client = _get_client(db)
    try:
        partners = await client.get_partners(keyword)
    except FreeeAPIError as e:
        _handle_freee_error(e)
    return {"partners": partners}


@router.get("/mappings", response_model=List[MappingResponse])
async def list_mappings(
    mapping_type: Optional[MappingType] = None, db: Session = Depends(get_db)
):
    """勘定科目マッピング一覧"""
    query = db.query(AccountItemMapping)
    if mapping_type:
        query = query.filter(AccountItemMapping.mapping_type == mapping_type)
    return query.order_by(
        AccountItemMapping.priority.desc(), AccountItemMapping.id
    ).all()


@router.post(
    "/mappings", response_model=MappingResponse, status_code=status.HTTP_201_CREATED
)
async def create_mapping(request: MappingRequest, db: Session = Depends(get_db)):
    """勘定科目マッピングを登録する"""
    mapping = AccountItemMapping(**request.model_dump())
    db.add(mapping)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"同じ種別・キー（{request.source_key}）のマッピングが既に存在します",
        )
    db.refresh(mapping)
    return mapping


@router.put("/mappings/{mapping_id}", response_model=MappingResponse)
async def update_mapping(
    mapping_id: int, request: MappingRequest, db: Session = Depends(get_db)
):
    """勘定科目マッピングを更新する"""
    mapping = (
        db.query(AccountItemMapping).filter(AccountItemMapping.id == mapping_id).first()
    )
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="マッピングが見つかりません"
        )
    for key, value in request.model_dump().items():
        setattr(mapping, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"同じ種別・キー（{request.source_key}）のマッピングが既に存在します",
        )
    db.refresh(mapping)
    return mapping


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """勘定科目マッピングを削除する"""
    mapping = (
        db.query(AccountItemMapping).filter(AccountItemMapping.id == mapping_id).first()
    )
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="マッピングが見つかりません"
        )
    db.delete(mapping)
    db.commit()
    return {"deleted": mapping_id}


@router.post("/mappings/suggest")
async def suggest_account_item(request: SuggestRequest, db: Session = Depends(get_db)):
    """カテゴリ・摘要から勘定科目を推定して返す"""
    resolver = AccountItemResolver(db, request.mapping_type)
    mapping = resolver.resolve(request.source_key, request.description)
    if mapping is None:
        return {"matched": False, "mapping": None}
    return {
        "matched": True,
        "mapping": MappingResponse.model_validate(mapping).model_dump(),
    }
