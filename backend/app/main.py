"""
FastAPI メインアプリケーション
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import accounting, data_import, forecast, health
from app.config import settings
from app.database import check_database_connection, create_tables

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーション起動・終了時の処理"""

    # 起動時処理
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    # データベース接続確認
    if await check_database_connection():
        logger.info("Database connection successful")
    else:
        logger.error("Database connection failed")
        raise Exception("Cannot connect to database")

    # 開発環境でのみテーブル自動作成
    if settings.environment == "development":
        try:
            create_tables()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")

    yield

    # 終了時処理
    logger.info("Shutting down application")


# FastAPIアプリケーション作成
app = FastAPI(
    title=settings.app_name,
    description="定期便と単発セット購入の需要予測システム API",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# セキュリティミドルウェア
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"],
    )


# リクエスト処理時間ミドルウェア
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """処理時間をヘッダーに追加"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ログミドルウェア
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """リクエスト・レスポンスログ"""
    start_time = time.time()

    # リクエストログ
    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    # レスポンスログ
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")

    return response


# カスタム例外ハンドラー
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """バリデーションエラーハンドラー"""
    logger.warning(f"Validation error for {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "リクエストデータが正しくありません。入力内容を確認してください。",
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """内部サーバーエラーハンドラー"""
    logger.error(f"Internal error for {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "サーバー内部エラーが発生しました。管理者にお問い合わせください。",
        },
    )


# ルーター登録
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(data_import.router, prefix="/api/v1", tags=["data"])
app.include_router(forecast.router, prefix="/api/v1", tags=["forecast"])
app.include_router(accounting.router, prefix="/api/v1", tags=["accounting"])


# ルートエンドポイント
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "environment": settings.environment,
        "status": "running",
    }


# システム情報エンドポイント
@app.get("/system/info")
async def system_info():
    """システム情報取得"""
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug,
        "allowed_origins": settings.allowed_origins,
        "max_upload_size": settings.max_upload_size,
        "forecast_settings": {
            "default_horizon": settings.forecast_default_horizon,
            "max_horizon": settings.max_forecast_horizon,
            "batch_size": settings.forecast_batch_size,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
