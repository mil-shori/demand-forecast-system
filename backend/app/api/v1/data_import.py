"""
データインポート API エンドポイント
CSV/Excelファイルの取り込み機能
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
import json
from datetime import datetime
import logging

from app.database import get_db
from app.config import settings
from app.models import Order, OrderItem, Product, Subscription, UserProfile

router = APIRouter()
logger = logging.getLogger(__name__)


class DataImportValidator:
    """データインポート検証クラス"""
    
    @staticmethod
    def validate_orders_data(df: pd.DataFrame) -> dict:
        """注文データの検証"""
        errors = []
        warnings = []
        
        # 必須カラムチェック
        required_columns = ['order_id', 'user_id', 'order_date', 'order_type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"必須カラムが不足: {missing_columns}")
        
        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # データ型・値の検証
        try:
            df['order_date'] = pd.to_datetime(df['order_date'])
        except Exception as e:
            errors.append(f"order_date の日付形式が正しくありません: {str(e)}")
        
        # order_typeの値チェック
        valid_order_types = ['subscription', 'oneoff']
        invalid_types = df[~df['order_type'].isin(valid_order_types)]['order_type'].unique()
        if len(invalid_types) > 0:
            errors.append(f"無効なorder_type: {list(invalid_types)}")
        
        # 重複チェック
        duplicates = df[df.duplicated(['order_id'])]['order_id'].tolist()
        if duplicates:
            warnings.append(f"重複するorder_id: {duplicates[:10]}")  # 最初の10件のみ表示
        
        # 金額の妥当性チェック
        if 'total_amount' in df.columns:
            negative_amounts = df[df['total_amount'] < 0]['order_id'].tolist()
            if negative_amounts:
                errors.append(f"負の金額の注文: {negative_amounts[:5]}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(df),
            "duplicate_count": len(duplicates)
        }
    
    @staticmethod
    def validate_order_items_data(df: pd.DataFrame) -> dict:
        """注文明細データの検証"""
        errors = []
        warnings = []
        
        required_columns = ['order_id', 'sku', 'quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"必須カラムが不足: {missing_columns}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # 数量の妥当性チェック
        invalid_quantities = df[df['quantity'] <= 0]['order_id'].tolist()
        if invalid_quantities:
            errors.append(f"無効な数量（0以下）の注文: {invalid_quantities[:5]}")
        
        # 単価の妥当性チェック
        if 'unit_price' in df.columns:
            negative_prices = df[df['unit_price'] < 0]['order_id'].tolist()
            if negative_prices:
                warnings.append(f"負の単価: {negative_prices[:5]}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(df)
        }
    
    @staticmethod
    def validate_products_data(df: pd.DataFrame) -> dict:
        """商品データの検証"""
        errors = []
        warnings = []
        
        required_columns = ['sku', 'product_name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"必須カラムが不足: {missing_columns}")
        
        # SKU重複チェック
        duplicates = df[df.duplicated(['sku'])]['sku'].tolist()
        if duplicates:
            errors.append(f"重複するSKU: {duplicates}")
        
        # 価格の妥当性チェック
        if 'base_price' in df.columns:
            negative_prices = df[df['base_price'] < 0]['sku'].tolist()
            if negative_prices:
                warnings.append(f"負の価格の商品: {negative_prices}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(df),
            "duplicate_count": len(duplicates)
        }


@router.post("/import/orders")
async def import_orders(
    file: UploadFile = File(...),
    validate_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    注文データのインポート
    
    Args:
        file: CSVファイル
        validate_only: True の場合、検証のみ実行（データは保存しない）
        db: データベースセッション
    """
    
    # ファイル形式チェック
    if not file.filename.lower().endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSVまたはExcelファイルのみサポートしています"
        )
    
    # ファイルサイズチェック
    content = await file.read()
    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"ファイルサイズが上限（{settings.max_upload_size}バイト）を超えています"
        )
    
    try:
        # ファイル読み込み
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        # データ検証
        validation_result = DataImportValidator.validate_orders_data(df)
        
        if not validation_result["valid"]:
            return {
                "status": "error",
                "message": "データ検証に失敗しました",
                "validation": validation_result
            }
        
        # 検証のみの場合はここで終了
        if validate_only:
            return {
                "status": "success",
                "message": "データ検証が完了しました",
                "validation": validation_result
            }
        
        # データベースへの保存
        inserted_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            # 既存データチェック
            existing_order = db.query(Order).filter(
                Order.order_id == row['order_id']
            ).first()
            
            if existing_order:
                # 更新
                for column in df.columns:
                    if hasattr(existing_order, column) and pd.notna(row[column]):
                        setattr(existing_order, column, row[column])
                updated_count += 1
            else:
                # 新規作成
                order_data = {
                    'order_id': row['order_id'],
                    'user_id': row['user_id'],
                    'order_date': row['order_date'],
                    'order_type': row['order_type'],
                    'subscription_id': row.get('subscription_id'),
                    'total_amount': row.get('total_amount'),
                    'channel': row.get('channel', 'web')
                }
                
                # NaN値を除去
                order_data = {k: v for k, v in order_data.items() if pd.notna(v)}
                
                order = Order(**order_data)
                db.add(order)
                inserted_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": "注文データのインポートが完了しました",
            "summary": {
                "total_rows": len(df),
                "inserted": inserted_count,
                "updated": updated_count
            },
            "validation": validation_result
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Order import error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"インポート中にエラーが発生しました: {str(e)}"
        )


@router.post("/import/order-items")  
async def import_order_items(
    file: UploadFile = File(...),
    validate_only: bool = False,
    db: Session = Depends(get_db)
):
    """注文明細データのインポート"""
    
    if not file.filename.lower().endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSVまたはExcelファイルのみサポートしています"
        )
    
    content = await file.read()
    
    try:
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        validation_result = DataImportValidator.validate_order_items_data(df)
        
        if not validation_result["valid"]:
            return {
                "status": "error", 
                "message": "データ検証に失敗しました",
                "validation": validation_result
            }
        
        if validate_only:
            return {
                "status": "success",
                "message": "データ検証が完了しました", 
                "validation": validation_result
            }
        
        # データベースへの保存
        inserted_count = 0
        
        for _, row in df.iterrows():
            item_data = {
                'order_id': row['order_id'],
                'sku': row['sku'],
                'quantity': row['quantity'],
                'unit_price': row.get('unit_price'),
                'discount_rate': row.get('discount_rate', 0.0),
                'promotion_code': row.get('promotion_code')
            }
            
            item_data = {k: v for k, v in item_data.items() if pd.notna(v)}
            
            order_item = OrderItem(**item_data)
            db.add(order_item)
            inserted_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": "注文明細データのインポートが完了しました",
            "summary": {
                "total_rows": len(df),
                "inserted": inserted_count
            },
            "validation": validation_result
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Order items import error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"インポート中にエラーが発生しました: {str(e)}"
        )


@router.post("/import/products")
async def import_products(
    file: UploadFile = File(...),
    validate_only: bool = False,
    db: Session = Depends(get_db)
):
    """商品データのインポート"""
    
    if not file.filename.lower().endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSVまたはExcelファイルのみサポートしています"
        )
    
    content = await file.read()
    
    try:
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        validation_result = DataImportValidator.validate_products_data(df)
        
        if not validation_result["valid"]:
            return {
                "status": "error",
                "message": "データ検証に失敗しました",
                "validation": validation_result
            }
        
        if validate_only:
            return {
                "status": "success",
                "message": "データ検証が完了しました",
                "validation": validation_result
            }
        
        # データベースへの保存
        inserted_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            existing_product = db.query(Product).filter(
                Product.sku == row['sku']
            ).first()
            
            if existing_product:
                # 更新
                for column in df.columns:
                    if hasattr(existing_product, column) and pd.notna(row[column]):
                        setattr(existing_product, column, row[column])
                updated_count += 1
            else:
                # 新規作成
                product_data = {
                    'sku': row['sku'],
                    'product_name': row['product_name'],
                    'category': row.get('category'),
                    'subcategory': row.get('subcategory'),
                    'brand': row.get('brand'),
                    'is_set_item': row.get('is_set_item', False),
                    'base_price': row.get('base_price'),
                    'active': row.get('active', True)
                }
                
                product_data = {k: v for k, v in product_data.items() if pd.notna(v)}
                
                product = Product(**product_data)
                db.add(product)
                inserted_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": "商品データのインポートが完了しました",
            "summary": {
                "total_rows": len(df),
                "inserted": inserted_count,
                "updated": updated_count
            },
            "validation": validation_result
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Products import error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"インポート中にエラーが発生しました: {str(e)}"
        )


@router.get("/import/status")
async def get_import_status():
    """インポート設定・制限情報の取得"""
    return {
        "max_file_size_mb": round(settings.max_upload_size / (1024 * 1024), 2),
        "supported_formats": ["csv", "xlsx"],
        "upload_directory": settings.upload_dir,
        "supported_tables": [
            {
                "name": "orders",
                "endpoint": "/import/orders",
                "required_columns": ["order_id", "user_id", "order_date", "order_type"],
                "optional_columns": ["subscription_id", "total_amount", "channel"]
            },
            {
                "name": "order_items", 
                "endpoint": "/import/order-items",
                "required_columns": ["order_id", "sku", "quantity"],
                "optional_columns": ["unit_price", "discount_rate", "promotion_code"]
            },
            {
                "name": "products",
                "endpoint": "/import/products", 
                "required_columns": ["sku", "product_name"],
                "optional_columns": ["category", "subcategory", "brand", "base_price", "active"]
            }
        ]
    }