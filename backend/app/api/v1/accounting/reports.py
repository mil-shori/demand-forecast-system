"""
月次レポート・試算表 API
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import report_service
from app.services.freee_client import (
    FreeeAPIClient,
    FreeeAPIError,
    FreeeNotConnectedError,
)

router = APIRouter()
logger = logging.getLogger(__name__)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _fetch_trial_pl(db: Session, year: int, month: int) -> Optional[dict]:
    """freee接続時のみ試算表（PL）を取得する。未接続・失敗時はNoneを返す"""
    try:
        client = FreeeAPIClient(db)
        return await client.get_trial_pl(
            fiscal_year=year, start_month=month, end_month=month
        )
    except FreeeNotConnectedError:
        return None
    except FreeeAPIError as e:
        logger.warning(f"trial_pl fetch failed, report continues without it: {e}")
        return None


@router.get("/reports/monthly")
async def download_monthly_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    format: str = Query(default="xlsx", pattern="^(xlsx|csv)$"),
    db: Session = Depends(get_db),
):
    """月次レポートをExcel/CSVでダウンロードする"""
    if format == "csv":
        buffer = report_service.generate_monthly_report_csv(db, year, month)
        filename = f"monthly_report_{year}-{month:02d}.csv"
        media_type = "text/csv"
    else:
        trial_pl = await _fetch_trial_pl(db, year, month)
        buffer = report_service.generate_monthly_report_xlsx(db, year, month, trial_pl)
        filename = f"monthly_report_{year}-{month:02d}.xlsx"
        media_type = XLSX_MEDIA_TYPE

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/trial-balance")
async def get_trial_balance(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    type: str = Query(default="pl", pattern="^(pl|bs)$"),
    db: Session = Depends(get_db),
):
    """freee試算表（PL/BS）を取得する"""
    try:
        client = FreeeAPIClient(db)
    except FreeeNotConnectedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )

    try:
        if type == "bs":
            data = await client.get_trial_bs(
                fiscal_year=year, start_month=month, end_month=month
            )
        else:
            data = await client.get_trial_pl(
                fiscal_year=year, start_month=month, end_month=month
            )
    except FreeeAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"freee APIエラー（{e.status_code}）: {e.message[:500]}",
        )
    return {"type": type, "year": year, "month": month, "trial_balance": data}
