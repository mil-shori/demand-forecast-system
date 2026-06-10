"""
アプリケーション設定管理
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """アプリケーション設定クラス"""
    
    # アプリケーション基本設定
    app_name: str = "需要予測システム"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    # データベース設定
    database_url: str
    database_test_url: str = ""
    
    # セキュリティ設定
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8時間
    
    # データ暗号化
    data_encryption_key: str = ""
    
    # CORS設定
    allowed_origins: List[str] = ["http://localhost:3000"]
    
    # ファイルアップロード設定
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "./uploads"
    
    # 監視・ログ設定
    sentry_dsn: str = ""
    log_level: str = "INFO"
    
    # メール設定（アラート用）
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    
    # 需要予測設定
    forecast_default_horizon: int = 28  # 日
    max_forecast_horizon: int = 365     # 日
    forecast_batch_size: int = 100      # バッチあたりSKU数
    
    # ビジネス設定
    default_service_level: float = 0.95
    default_lead_time_days: int = 7

    # freee API連携設定
    freee_client_id: str = ""
    freee_client_secret: str = ""
    freee_redirect_uri: str = "http://localhost:8000/api/v1/accounting/freee/callback"
    freee_api_base_url: str = "https://api.freee.co.jp"
    freee_auth_base_url: str = "https://accounts.secure.freee.co.jp"
    frontend_base_url: str = "http://localhost:3000"
    
    @validator('allowed_origins', pre=True)
    def parse_cors_origins(cls, v):
        """CORS オリジンの解析"""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator('secret_key')
    def secret_key_must_be_present(cls, v):
        """秘密鍵の検証"""
        if not v:
            raise ValueError('SECRET_KEY must be set')
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v
    
    @validator('database_url')
    def database_url_must_be_present(cls, v):
        """データベースURLの検証"""
        if not v:
            raise ValueError('DATABASE_URL must be set')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# グローバル設定インスタンス
settings = Settings()


def get_database_url() -> str:
    """データベースURL取得"""
    return settings.database_url


def get_test_database_url() -> str:
    """テスト用データベースURL取得"""
    return settings.database_test_url or settings.database_url.replace(
        "/demand_forecast", "/demand_forecast_test"
    )


def is_development() -> bool:
    """開発環境判定"""
    return settings.environment.lower() == "development"


def is_production() -> bool:
    """本番環境判定"""
    return settings.environment.lower() == "production"