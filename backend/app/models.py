"""
データベースモデル定義
"""
from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Numeric, Boolean,
    Text, ForeignKey, Index, Enum as SQLEnum, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
import enum

from app.database import Base


class OrderType(str, Enum):
    """注文タイプ"""
    SUBSCRIPTION = "subscription"  # 定期便
    ONEOFF = "oneoff"             # 単発


class SubscriptionStatus(str, Enum):
    """定期便ステータス"""
    ACTIVE = "active"       # アクティブ
    PAUSED = "paused"       # 一時停止
    CANCELLED = "cancelled" # 解約済み


class Channel(str, Enum):
    """販売チャネル"""
    WEB = "web"
    MOBILE = "mobile"
    PHONE = "phone"
    OTHER = "other"


class Order(Base):
    """注文テーブル"""
    __tablename__ = "orders"
    
    order_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    order_date = Column(Date, nullable=False, index=True)
    order_type = Column(SQLEnum(OrderType), nullable=False, index=True)
    subscription_id = Column(String(50), ForeignKey('subscriptions.subscription_id'), nullable=True, index=True)
    total_amount = Column(Numeric(10, 2), nullable=True)
    channel = Column(SQLEnum(Channel), default=Channel.WEB, nullable=False)
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # リレーション
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="orders")
    
    # インデックス
    __table_args__ = (
        Index('ix_orders_date_type', 'order_date', 'order_type'),
        Index('ix_orders_user_date', 'user_id', 'order_date'),
    )


class OrderItem(Base):
    """注文明細テーブル"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey('orders.order_id'), nullable=False, index=True)
    sku = Column(String(100), ForeignKey('products.sku'), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(8, 2), nullable=True)
    discount_rate = Column(Numeric(3, 2), default=0.0)
    promotion_code = Column(String(20), nullable=True)
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    
    # インデックス
    __table_args__ = (
        Index('ix_order_items_sku_date', 'sku', 'created_at'),
        Index('ix_order_items_order_sku', 'order_id', 'sku'),
    )


class Product(Base):
    """商品マスタテーブル"""
    __tablename__ = "products"
    
    sku = Column(String(100), primary_key=True, index=True)
    product_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True, index=True)
    subcategory = Column(String(50), nullable=True)
    brand = Column(String(50), nullable=True)
    is_set_item = Column(Boolean, default=False, index=True)
    base_price = Column(Numeric(8, 2), nullable=True)
    cost = Column(Numeric(8, 2), nullable=True)
    weight_grams = Column(Integer, nullable=True)
    dimensions = Column(String(50), nullable=True)  # "L×W×H" format
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, index=True)
    
    # 在庫関連
    min_order_quantity = Column(Integer, default=1)
    lead_time_days = Column(Integer, default=7)
    supplier_code = Column(String(50), nullable=True)
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # リレーション
    order_items = relationship("OrderItem", back_populates="product")
    set_components = relationship("ProductSet", foreign_keys="ProductSet.set_sku", back_populates="set_product")
    component_of_sets = relationship("ProductSet", foreign_keys="ProductSet.component_sku", back_populates="component_product")
    
    # インデックス
    __table_args__ = (
        Index('ix_products_category_active', 'category', 'active'),
        Index('ix_products_brand_category', 'brand', 'category'),
    )


class Subscription(Base):
    """定期便テーブル"""
    __tablename__ = "subscriptions"
    
    subscription_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    frequency_days = Column(Integer, default=30)  # 配送間隔（日）
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False, index=True)
    next_delivery_date = Column(Date, nullable=True, index=True)
    pause_until_date = Column(Date, nullable=True)
    cancellation_date = Column(Date, nullable=True)
    cancellation_reason = Column(String(200), nullable=True)
    
    # 配送設定
    delivery_address = Column(Text, nullable=True)
    delivery_instructions = Column(Text, nullable=True)
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # リレーション
    orders = relationship("Order", back_populates="subscription")
    
    # インデックス
    __table_args__ = (
        Index('ix_subscriptions_user_status', 'user_id', 'status'),
        Index('ix_subscriptions_next_delivery', 'next_delivery_date', 'status'),
    )


class ProductSet(Base):
    """セット商品構成テーブル"""
    __tablename__ = "product_sets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    set_sku = Column(String(100), ForeignKey('products.sku'), nullable=False, index=True)
    component_sku = Column(String(100), ForeignKey('products.sku'), nullable=False, index=True)
    component_quantity = Column(Integer, nullable=False, default=1)
    is_optional = Column(Boolean, default=False)  # オプション構成要素かどうか
    sort_order = Column(Integer, default=0)  # 表示順序
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    set_product = relationship("Product", foreign_keys=[set_sku], back_populates="set_components")
    component_product = relationship("Product", foreign_keys=[component_sku], back_populates="component_of_sets")
    
    # 制約
    __table_args__ = (
        UniqueConstraint('set_sku', 'component_sku', name='uq_product_sets_sku_component'),
        Index('ix_product_sets_set_sku', 'set_sku'),
    )


class UserProfile(Base):
    """ユーザープロファイル（簡易版）"""
    __tablename__ = "user_profiles"
    
    user_id = Column(String(50), primary_key=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # 顧客セグメント情報
    customer_segment = Column(String(50), nullable=True)  # VIP, Regular, New, etc.
    acquisition_channel = Column(String(50), nullable=True)
    registration_date = Column(Date, nullable=True)
    
    # プリファレンス
    preferred_delivery_day = Column(String(10), nullable=True)  # Monday, Tuesday, etc.
    dietary_restrictions = Column(String(200), nullable=True)
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # インデックス
    __table_args__ = (
        Index('ix_user_profiles_email', 'email'),
        Index('ix_user_profiles_segment', 'customer_segment'),
    )


class MappingType(str, Enum):
    """勘定科目マッピング種別"""
    SALES_CATEGORY = "sales_category"      # 売上カテゴリ
    EXPENSE_CATEGORY = "expense_category"  # 経費カテゴリ


class JournalEntryType(str, Enum):
    """仕訳種別"""
    SALES = "sales"      # 売上
    EXPENSE = "expense"  # 経費


class JournalEntryStatus(str, Enum):
    """仕訳の同期ステータス"""
    PENDING = "pending"  # 未送信
    SYNCED = "synced"    # freee登録済み
    FAILED = "failed"    # 送信失敗
    SKIPPED = "skipped"  # スキップ（対象外）


class ExpenseStatus(str, Enum):
    """経費ステータス"""
    DRAFT = "draft"          # 下書き
    CONFIRMED = "confirmed"  # 確定（同期待ち）
    SYNCED = "synced"        # freee登録済み
    FAILED = "failed"        # 送信失敗


class FreeeToken(Base):
    """freee OAuth2トークン（access/refresh はFernetで暗号化して格納）"""
    __tablename__ = "freee_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, unique=True, index=True)  # freee事業所ID
    company_name = Column(String(200), nullable=True)
    access_token = Column(Text, nullable=False)   # 暗号化済み
    refresh_token = Column(Text, nullable=False)  # 暗号化済み
    token_type = Column(String(20), default="bearer")
    scope = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=False, index=True)  # 現在選択中の事業所

    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccountItemMapping(Base):
    """勘定科目マッピング（カテゴリ→freee勘定科目の自動推定ルール）"""
    __tablename__ = "account_item_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mapping_type = Column(SQLEnum(MappingType), nullable=False, index=True)
    source_key = Column(String(100), nullable=False)  # 商品カテゴリ名 or 経費カテゴリ名
    keywords = Column(Text, nullable=True)  # カンマ区切り。摘要からの部分一致推定に使用
    freee_account_item_id = Column(Integer, nullable=False)
    freee_account_item_name = Column(String(200), nullable=True)
    freee_tax_code = Column(Integer, nullable=True)
    freee_partner_id = Column(Integer, nullable=True)
    priority = Column(Integer, default=0)
    active = Column(Boolean, default=True, index=True)

    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 制約
    __table_args__ = (
        UniqueConstraint('mapping_type', 'source_key', name='uq_account_item_mappings_type_key'),
    )


class JournalEntry(Base):
    """仕訳（freee取引との対応・同期ログ）"""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_date = Column(Date, nullable=False, index=True)
    entry_type = Column(SQLEnum(JournalEntryType), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # 'sales_daily' | 'sales_monthly' | 'expense'
    source_key = Column(String(100), nullable=False)  # 例: '2026-05-01', 'expense:42'
    description = Column(String(500), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    details = Column(JSON, nullable=True)  # freee dealペイロード
    freee_company_id = Column(Integer, nullable=True)
    freee_deal_id = Column(Integer, nullable=True, index=True)
    status = Column(SQLEnum(JournalEntryStatus), default=JournalEntryStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 制約・インデックス（UNIQUE制約が再実行時の二重登録を防止する）
    __table_args__ = (
        UniqueConstraint('source_type', 'source_key', name='uq_journal_entries_source'),
        Index('ix_journal_entries_date_status', 'entry_date', 'status'),
    )


class Expense(Base):
    """経費テーブル"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    payment_method = Column(String(30), default="cash")  # cash / credit_card / bank_transfer
    partner_name = Column(String(200), nullable=True)
    receipt_filename = Column(String(255), nullable=True)
    status = Column(SQLEnum(ExpenseStatus), default=ExpenseStatus.DRAFT, nullable=False, index=True)
    freee_deal_id = Column(Integer, nullable=True)
    created_by = Column(String(100), nullable=True)

    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # インデックス
    __table_args__ = (
        Index('ix_expenses_date_status', 'expense_date', 'status'),
    )


class InventorySnapshot(Base):
    """在庫スナップショット（日次）"""
    __tablename__ = "inventory_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    sku = Column(String(100), ForeignKey('products.sku'), nullable=False, index=True)
    on_hand_quantity = Column(Integer, nullable=False, default=0)
    allocated_quantity = Column(Integer, nullable=False, default=0)  # 予約済み
    available_quantity = Column(Integer, nullable=False, default=0)  # 利用可能
    inbound_quantity = Column(Integer, nullable=False, default=0)    # 入荷予定
    
    # メタデータ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    product = relationship("Product")
    
    # 制約・インデックス
    __table_args__ = (
        UniqueConstraint('snapshot_date', 'sku', name='uq_inventory_snapshots_date_sku'),
        Index('ix_inventory_snapshots_date_sku', 'snapshot_date', 'sku'),
    )