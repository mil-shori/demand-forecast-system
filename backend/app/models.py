"""
データベースモデル定義
"""
from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Decimal, Boolean, 
    Text, ForeignKey, Index, Enum as SQLEnum, UniqueConstraint
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
    total_amount = Column(Decimal(10, 2), nullable=True)
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
    unit_price = Column(Decimal(8, 2), nullable=True)
    discount_rate = Column(Decimal(3, 2), default=0.0)
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
    base_price = Column(Decimal(8, 2), nullable=True)
    cost = Column(Decimal(8, 2), nullable=True)
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