"""
データベース設定とセッション管理
"""
import logging
from typing import Generator

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# データベースエンジン作成
if settings.environment == "development":
    # 開発環境では接続プール設定を緩く
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug,  # SQLログ出力
    )
else:
    # 本番環境ではより厳密な設定
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
    )

# セッション作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラス
Base = declarative_base()

# メタデータ（マイグレーション用）
metadata = MetaData()


def get_db() -> Generator[Session, None, None]:
    """
    データベースセッションの取得（依存性注入用）
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """
    テーブル作成（開発用）
    本番環境ではAlembicマイグレーションを使用
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_tables():
    """
    テーブル削除（テスト用）
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


async def check_database_connection() -> bool:
    """
    データベース接続確認
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


class DatabaseHealthCheck:
    """データベースヘルスチェック"""

    @staticmethod
    def check_connection() -> dict:
        """接続状況チェック"""
        try:
            db = SessionLocal()
            result = db.execute(text("SELECT 1")).fetchone()
            db.close()

            if result:
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                }
            else:
                return {"status": "unhealthy", "message": "Database query failed"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection error: {str(e)}",
            }

    @staticmethod
    def check_tables() -> dict:
        """テーブル存在確認"""
        try:
            db = SessionLocal()

            # 主要テーブルの存在確認
            required_tables = [
                "orders",
                "order_items",
                "products",
                "subscriptions",
                "product_sets",
            ]

            existing_tables = []
            for table in required_tables:
                result = db.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = :table)"
                    ),
                    {"table": table},
                ).fetchone()

                if result and result[0]:
                    existing_tables.append(table)

            db.close()

            missing_tables = set(required_tables) - set(existing_tables)

            if not missing_tables:
                return {
                    "status": "healthy",
                    "message": "All required tables exist",
                    "existing_tables": existing_tables,
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Missing tables: {list(missing_tables)}",
                    "existing_tables": existing_tables,
                    "missing_tables": list(missing_tables),
                }
        except Exception as e:
            return {"status": "unhealthy", "message": f"Table check error: {str(e)}"}
