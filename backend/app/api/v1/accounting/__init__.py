"""
経理業務自動化 API パッケージ
"""
from fastapi import APIRouter

from app.api.v1.accounting import ai, auth, expenses, master, reports, sales_sync

router = APIRouter(prefix="/accounting")
router.include_router(auth.router)
router.include_router(master.router)
router.include_router(sales_sync.router)
router.include_router(expenses.router)
router.include_router(reports.router)
router.include_router(ai.router)
