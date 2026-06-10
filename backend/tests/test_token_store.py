"""
freee_token_store のテスト（暗号化往復・UPSERT・期限判定・事業所切替）
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import freee_token_store


def test_encrypt_decrypt_roundtrip():
    plain = "secret-access-token-12345"
    encrypted = freee_token_store.encrypt_token(plain)
    assert encrypted != plain
    assert freee_token_store.decrypt_token(encrypted) == plain


def test_save_token_encrypts_and_activates_first_company(db_session):
    token = freee_token_store.save_token(
        db_session,
        company_id=101,
        access_token="access-1",
        refresh_token="refresh-1",
        expires_in=21600,
        company_name="テスト事業所",
    )
    # 暗号化されて格納される
    assert token.access_token != "access-1"
    assert freee_token_store.decrypt_token(token.access_token) == "access-1"
    assert freee_token_store.decrypt_token(token.refresh_token) == "refresh-1"
    # 最初の事業所は自動的にアクティブになる
    assert token.is_active is True


def test_save_token_upserts_existing_company(db_session):
    freee_token_store.save_token(
        db_session, company_id=101, access_token="a1", refresh_token="r1", expires_in=21600
    )
    updated = freee_token_store.save_token(
        db_session, company_id=101, access_token="a2", refresh_token="r2", expires_in=21600
    )
    assert freee_token_store.decrypt_token(updated.access_token) == "a2"
    assert freee_token_store.decrypt_token(updated.refresh_token) == "r2"
    # レコードは増えない
    from app.models import FreeeToken

    assert db_session.query(FreeeToken).count() == 1


def test_second_company_is_not_active_by_default(db_session):
    freee_token_store.save_token(
        db_session, company_id=101, access_token="a", refresh_token="r", expires_in=21600
    )
    second = freee_token_store.save_token(
        db_session, company_id=202, access_token="a", refresh_token="r", expires_in=21600
    )
    assert second.is_active is False
    active = freee_token_store.get_active_token(db_session)
    assert active.company_id == 101


def test_set_active_company_switches(db_session):
    freee_token_store.save_token(
        db_session, company_id=101, access_token="a", refresh_token="r", expires_in=21600
    )
    freee_token_store.save_token(
        db_session, company_id=202, access_token="a", refresh_token="r", expires_in=21600
    )
    freee_token_store.set_active_company(db_session, 202)
    active = freee_token_store.get_active_token(db_session)
    assert active.company_id == 202


def test_set_active_company_unknown_raises(db_session):
    with pytest.raises(ValueError):
        freee_token_store.set_active_company(db_session, 999)


def test_is_token_expiring(db_session):
    token = freee_token_store.save_token(
        db_session, company_id=101, access_token="a", refresh_token="r", expires_in=21600
    )
    assert freee_token_store.is_token_expiring(token) is False

    # 期限切れ間近（マージン5分以内）
    token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
    assert freee_token_store.is_token_expiring(token) is True

    # 完全に期限切れ
    token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    assert freee_token_store.is_token_expiring(token) is True


def test_delete_all_tokens(db_session):
    freee_token_store.save_token(
        db_session, company_id=101, access_token="a", refresh_token="r", expires_in=21600
    )
    assert freee_token_store.delete_all_tokens(db_session) == 1
    assert freee_token_store.get_active_token(db_session) is None
