"""
freee OAuth2トークンの保存・取得（Fernet暗号化）
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.config import settings
from app.models import FreeeToken

logger = logging.getLogger(__name__)

# トークン期限のこの秒数前になったらリフレッシュする
TOKEN_REFRESH_MARGIN_SECONDS = 300


class EncryptionKeyMissingError(Exception):
    """DATA_ENCRYPTION_KEY が未設定"""


def _get_fernet() -> Fernet:
    if not settings.data_encryption_key:
        raise EncryptionKeyMissingError(
            "DATA_ENCRYPTION_KEY が未設定です。"
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" '
            "で生成して .env に設定してください。"
        )
    return Fernet(settings.data_encryption_key.encode())


def encrypt_token(plain: str) -> str:
    """トークンを暗号化"""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """トークンを復号"""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def save_token(
    db: Session,
    company_id: int,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    company_name: Optional[str] = None,
    scope: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> FreeeToken:
    """
    トークンを暗号化してDBへ保存（既存事業所はUPSERT）。

    freeeのrefresh_tokenは使用のたびにローテーションされるため、
    リフレッシュ直後に必ずこの関数で保存すること。
    """
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    token = db.query(FreeeToken).filter(FreeeToken.company_id == company_id).first()
    if token is None:
        token = FreeeToken(company_id=company_id)
        db.add(token)
        # 初回接続の事業所は、他にアクティブな事業所がなければアクティブにする
        if is_active is None:
            has_active = db.query(FreeeToken).filter(FreeeToken.is_active == True).count() > 0  # noqa: E712
            is_active = not has_active

    token.access_token = encrypt_token(access_token)
    token.refresh_token = encrypt_token(refresh_token)
    token.expires_at = expires_at
    if company_name is not None:
        token.company_name = company_name
    if scope is not None:
        token.scope = scope
    if is_active is not None:
        token.is_active = is_active

    db.commit()
    db.refresh(token)
    logger.info(f"freee token saved for company_id={company_id} (expires_at={expires_at.isoformat()})")
    return token


def get_active_token(db: Session) -> Optional[FreeeToken]:
    """現在選択中（is_active）の事業所トークンを取得"""
    return db.query(FreeeToken).filter(FreeeToken.is_active == True).first()  # noqa: E712


def get_token_by_company(db: Session, company_id: int) -> Optional[FreeeToken]:
    """事業所IDでトークンを取得"""
    return db.query(FreeeToken).filter(FreeeToken.company_id == company_id).first()


def set_active_company(db: Session, company_id: int) -> FreeeToken:
    """使用する事業所を切り替える"""
    token = get_token_by_company(db, company_id)
    if token is None:
        raise ValueError(f"company_id={company_id} のトークンが見つかりません")
    db.query(FreeeToken).update({FreeeToken.is_active: False})
    token.is_active = True
    db.commit()
    db.refresh(token)
    return token


def delete_all_tokens(db: Session) -> int:
    """全トークンを削除（freee切断）"""
    count = db.query(FreeeToken).delete()
    db.commit()
    return count


def is_token_expiring(token: FreeeToken, margin_seconds: int = TOKEN_REFRESH_MARGIN_SECONDS) -> bool:
    """トークンが期限切れ間近（または期限切れ）か判定"""
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        # SQLite等でtimezone情報が落ちる場合はUTCとして扱う
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expires_at - timedelta(seconds=margin_seconds)
