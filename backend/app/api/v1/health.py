"""
ヘルスチェック API エンドポイント
"""
import os
from datetime import datetime

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import DatabaseHealthCheck, get_db

router = APIRouter()


@router.get("/health")
async def basic_health_check():
    """基本ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """詳細ヘルスチェック"""

    # システムリソース情報
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=1)

    # データベース接続確認
    db_connection = DatabaseHealthCheck.check_connection()
    db_tables = DatabaseHealthCheck.check_tables()

    # アプリケーション設定確認
    config_check = check_configuration()

    # 全体のヘルス状態判定
    components = [db_connection, db_tables, config_check]
    overall_healthy = all(component["status"] == "healthy" for component in components)

    # レスポンス構築
    response = {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "system": {
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
                "status": "healthy" if memory.percent < 85 else "warning",
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": round((disk.used / disk.total) * 100, 2),
                "status": "healthy" if (disk.used / disk.total) < 0.8 else "warning",
            },
            "cpu": {
                "percent_used": cpu_percent,
                "status": "healthy" if cpu_percent < 80 else "warning",
            },
        },
        "database": {"connection": db_connection, "tables": db_tables},
        "configuration": config_check,
    }

    return response


@router.get("/health/database")
async def database_health_check():
    """データベース専用ヘルスチェック"""

    connection_check = DatabaseHealthCheck.check_connection()
    tables_check = DatabaseHealthCheck.check_tables()

    return {
        "status": "healthy"
        if (
            connection_check["status"] == "healthy"
            and tables_check["status"] == "healthy"
        )
        else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "connection": connection_check,
        "tables": tables_check,
    }


@router.get("/health/system")
async def system_health_check():
    """システムリソース専用ヘルスチェック"""

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=1)

    # プロセス情報
    process = psutil.Process(os.getpid())
    process_memory = process.memory_info()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": round((disk.used / disk.total) * 100, 2),
            },
            "cpu": {"percent_used": cpu_percent, "core_count": psutil.cpu_count()},
        },
        "process": {
            "pid": os.getpid(),
            "memory_mb": round(process_memory.rss / (1024**2), 2),
            "memory_virtual_mb": round(process_memory.vms / (1024**2), 2),
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
        },
    }


def check_configuration() -> dict:
    """設定確認"""
    try:
        issues = []

        # 必須設定の確認
        if not settings.secret_key or len(settings.secret_key) < 32:
            issues.append("SECRET_KEY is not properly configured")

        if not settings.database_url:
            issues.append("DATABASE_URL is not configured")

        if settings.environment not in ["development", "staging", "production"]:
            issues.append(f"Invalid environment: {settings.environment}")

        # ディレクトリの存在確認
        if not os.path.exists(settings.upload_dir):
            try:
                os.makedirs(settings.upload_dir, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create upload directory: {e}")

        return {
            "status": "healthy" if not issues else "warning",
            "message": "Configuration is valid"
            if not issues
            else "Configuration issues found",
            "issues": issues if issues else None,
            "settings": {
                "environment": settings.environment,
                "debug": settings.debug,
                "upload_dir": settings.upload_dir,
                "max_upload_size_mb": round(settings.max_upload_size / (1024**2), 2),
                "forecast_horizon": settings.forecast_default_horizon,
                "allowed_origins_count": len(settings.allowed_origins),
            },
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Configuration check failed: {str(e)}",
        }
