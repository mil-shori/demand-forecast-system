"""
pytest共通フィクスチャ

注意: app.config の Settings は import時に環境変数を読むため、
アプリモジュールのimportより先に環境変数を設定する。
"""
import os

from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-1234567890abcdef")
os.environ.setdefault("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("FREEE_CLIENT_ID", "test-client-id")
os.environ.setdefault("FREEE_CLIENT_SECRET", "test-client-secret")
# database.py は development 以外で pool_size 等を指定するため、SQLiteでは development にする
os.environ.setdefault("ENVIRONMENT", "development")
# DEBUG=false だと TrustedHostMiddleware が有効になり TestClient(host=testserver) が400になる
os.environ.setdefault("DEBUG", "true")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_session():
    """テストごとに独立したSQLite in-memory DBセッション"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """get_dbをテストDBに差し替えたTestClient（lifespanは起動しない）"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
