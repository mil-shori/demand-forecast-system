"""
需要予測 API エンドポイント
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderItem, Product
from app.services.data_validation import DataPreprocessor
from app.services.forecast_engine import (
    ForecastConfig,
    ForecastResult,
    SimpleForecastEngine,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic モデル定義
class ForecastRequest(BaseModel):
    """予測リクエスト"""

    sku_list: Optional[List[str]] = Field(None, description="予測対象SKUリスト（省略時は全SKU）")
    horizon: int = Field(28, ge=1, le=365, description="予測期間（日数）")
    start_date: Optional[str] = Field(None, description="学習データ開始日 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="学習データ終了日 (YYYY-MM-DD)")
    confidence_levels: List[int] = Field([80, 95], description="信頼区間レベル")
    models: Optional[List[str]] = Field(None, description="使用モデルリスト")


class ForecastResponse(BaseModel):
    """予測レスポンス"""

    status: str
    message: str
    forecast_id: str
    sku_count: int
    horizon: int
    execution_time_seconds: Optional[float] = None
    results: Optional[Dict[str, Any]] = None


class ForecastSummary(BaseModel):
    """予測サマリー"""

    total_skus: int
    successful_forecasts: int
    failed_forecasts: int
    average_accuracy: Optional[float] = None
    execution_time: float
    created_at: datetime


# グローバル変数（本来はRedisなどで管理）
forecast_cache = {}
forecast_results = {}


@router.post("/forecast/run", response_model=ForecastResponse)
async def run_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    需要予測の実行
    """

    try:
        # 予測ID生成
        forecast_id = f"forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 即座にレスポンスを返し、バックグラウンドで処理実行
        background_tasks.add_task(
            _execute_forecast_background, forecast_id, request, db
        )

        return ForecastResponse(
            status="accepted",
            message="予測処理を開始しました。結果は後で取得してください。",
            forecast_id=forecast_id,
            sku_count=0,  # バックグラウンド処理後に更新
            horizon=request.horizon,
        )

    except Exception as e:
        logger.error(f"予測開始エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予測処理の開始に失敗しました: {str(e)}",
        )


@router.get("/forecast/{forecast_id}/status")
async def get_forecast_status(forecast_id: str):
    """
    予測処理の状況確認
    """

    if forecast_id not in forecast_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="指定された予測IDが見つかりません"
        )

    cache_data = forecast_cache[forecast_id]

    return {
        "forecast_id": forecast_id,
        "status": cache_data["status"],
        "progress": cache_data.get("progress", 0),
        "message": cache_data.get("message", ""),
        "created_at": cache_data["created_at"],
        "completed_at": cache_data.get("completed_at"),
        "error": cache_data.get("error"),
    }


@router.get("/forecast/{forecast_id}/results")
async def get_forecast_results(forecast_id: str, sku: Optional[str] = None):
    """
    予測結果の取得
    """

    if forecast_id not in forecast_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="予測結果が見つかりません"
        )

    results = forecast_results[forecast_id]

    if sku:
        # 特定SKUの結果のみ返す
        if sku not in results["forecasts"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SKU '{sku}' の予測結果が見つかりません",
            )

        return {
            "forecast_id": forecast_id,
            "sku": sku,
            "result": _format_forecast_result(results["forecasts"][sku]),
            "metadata": results["metadata"],
        }
    else:
        # 全結果を返す
        formatted_results = {}
        for sku_key, forecast_result in results["forecasts"].items():
            formatted_results[sku_key] = _format_forecast_result(forecast_result)

        return {
            "forecast_id": forecast_id,
            "results": formatted_results,
            "summary": results["summary"],
            "metadata": results["metadata"],
        }


@router.get("/forecast/{forecast_id}/summary")
async def get_forecast_summary(forecast_id: str):
    """
    予測結果のサマリー取得
    """

    if forecast_id not in forecast_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="予測結果が見つかりません"
        )

    results = forecast_results[forecast_id]

    return {
        "forecast_id": forecast_id,
        "summary": results["summary"],
        "metadata": results["metadata"],
    }


@router.post("/forecast/batch")
async def run_batch_forecast(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    バッチ予測の実行（全SKU対象）
    """

    try:
        # デフォルト設定で全SKU予測
        request = ForecastRequest()
        forecast_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        background_tasks.add_task(
            _execute_forecast_background, forecast_id, request, db
        )

        return {
            "status": "accepted",
            "forecast_id": forecast_id,
            "message": "バッチ予測を開始しました",
        }

    except Exception as e:
        logger.error(f"バッチ予測開始エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"バッチ予測の開始に失敗しました: {str(e)}",
        )


@router.get("/forecast/models/available")
async def get_available_models():
    """
    利用可能な予測モデル一覧
    """

    return {
        "models": [
            {
                "name": "AutoARIMA",
                "description": "自動ARIMA：季節性・トレンドを自動検出",
                "suitable_for": "長期データ（3ヶ月以上）、規則的な需要",
                "parameters": ["season_length"],
            },
            {
                "name": "AutoETS",
                "description": "自動指数平滑法：軽量で高速",
                "suitable_for": "中期データ（1ヶ月以上）、ある程度規則的な需要",
                "parameters": ["season_length", "model"],
            },
            {
                "name": "CrostonClassic",
                "description": "Croston法：間欠需要に特化",
                "suitable_for": "不規則・間欠需要（欠品率50%以上）",
                "parameters": [],
            },
            {
                "name": "CrostonOptimized",
                "description": "最適化Croston法：間欠需要の改良版",
                "suitable_for": "不規則・間欠需要（欠品率30-75%）",
                "parameters": [],
            },
            {
                "name": "SeasonalNaive",
                "description": "季節ナイーブ法：シンプルな季節性予測",
                "suitable_for": "短期データ、フォールバック用",
                "parameters": ["season_length"],
            },
        ],
        "default_selection_logic": {
            "high_frequency": "AutoARIMA（月間100件以上の注文）",
            "medium_frequency": "AutoETS（月間10-100件）",
            "low_frequency": "CrostonClassic（月間10件未満）",
            "insufficient_data": "SeasonalNaive（データ不足時）",
        },
    }


@router.delete("/forecast/{forecast_id}")
async def delete_forecast(forecast_id: str):
    """
    予測結果の削除
    """

    deleted_count = 0

    if forecast_id in forecast_cache:
        del forecast_cache[forecast_id]
        deleted_count += 1

    if forecast_id in forecast_results:
        del forecast_results[forecast_id]
        deleted_count += 1

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="指定された予測IDが見つかりません"
        )

    return {
        "message": f"予測結果を削除しました (forecast_id: {forecast_id})",
        "deleted_items": deleted_count,
    }


async def _execute_forecast_background(
    forecast_id: str, request: ForecastRequest, db: Session
):
    """
    バックグラウンドで予測実行
    """

    start_time = datetime.now()

    try:
        # キャッシュにステータス登録
        forecast_cache[forecast_id] = {
            "status": "running",
            "progress": 0,
            "message": "データ準備中...",
            "created_at": start_time,
            "request": request.dict(),
        }

        # データ準備
        forecast_cache[forecast_id]["message"] = "データベースからデータを取得中..."

        # 注文データ取得
        orders_query = db.query(Order)
        if request.start_date:
            orders_query = orders_query.filter(Order.order_date >= request.start_date)
        if request.end_date:
            orders_query = orders_query.filter(Order.order_date <= request.end_date)

        orders_data = pd.read_sql(orders_query.statement, db.bind)

        if orders_data.empty:
            raise Exception("指定期間にデータが見つかりません")

        forecast_cache[forecast_id]["progress"] = 10

        # 注文明細データ取得
        order_items_data = pd.read_sql(db.query(OrderItem).statement, db.bind)

        # 商品データ取得
        products_data = pd.read_sql(db.query(Product).statement, db.bind)

        forecast_cache[forecast_id]["progress"] = 20
        forecast_cache[forecast_id]["message"] = "データ前処理中..."

        # データ前処理
        preprocessor = DataPreprocessor()
        processed_data = preprocessor.preprocess_for_forecasting(
            orders_data,
            order_items_data,
            products_data,
            request.start_date,
            request.end_date,
        )

        daily_demand = processed_data["daily_demand"]
        sku_metadata = processed_data["sku_metadata"]

        # SKUフィルタリング
        if request.sku_list:
            daily_demand = daily_demand[daily_demand["sku"].isin(request.sku_list)]
            sku_metadata = sku_metadata[sku_metadata["sku"].isin(request.sku_list)]

        forecast_cache[forecast_id]["progress"] = 30
        forecast_cache[forecast_id]["message"] = "予測実行中..."

        # 予測設定
        config = ForecastConfig(
            horizon=request.horizon, confidence_levels=request.confidence_levels
        )

        # 予測実行
        engine = SimpleForecastEngine(config)
        forecast_results_dict = engine.generate_forecasts(
            daily_demand, sku_metadata, request.horizon
        )

        forecast_cache[forecast_id]["progress"] = 80
        forecast_cache[forecast_id]["message"] = "結果処理中..."

        # 結果サマリー作成
        successful_forecasts = len(forecast_results_dict)
        failed_forecasts = 0  # エラー処理は内部で行われるため

        execution_time = (datetime.now() - start_time).total_seconds()

        summary = {
            "total_skus": len(daily_demand["sku"].unique()),
            "successful_forecasts": successful_forecasts,
            "failed_forecasts": failed_forecasts,
            "execution_time_seconds": execution_time,
            "created_at": start_time.isoformat(),
        }

        # 結果保存
        forecast_results[forecast_id] = {
            "forecasts": forecast_results_dict,
            "summary": summary,
            "metadata": {
                "request": request.dict(),
                "data_period": {
                    "start": daily_demand["ds"].min().strftime("%Y-%m-%d"),
                    "end": daily_demand["ds"].max().strftime("%Y-%m-%d"),
                    "total_days": len(daily_demand["ds"].unique()),
                },
            },
        }

        # 完了ステータス更新
        forecast_cache[forecast_id].update(
            {
                "status": "completed",
                "progress": 100,
                "message": "予測完了",
                "completed_at": datetime.now(),
                "results_summary": summary,
            }
        )

        logger.info(
            f"予測完了: {forecast_id}, SKU数: {successful_forecasts}, "
            f"処理時間: {execution_time:.2f}秒"
        )

    except Exception as e:
        logger.error(f"予測処理エラー ({forecast_id}): {str(e)}")

        # エラーステータス更新
        forecast_cache[forecast_id].update(
            {
                "status": "failed",
                "progress": 0,
                "message": f"予測処理に失敗しました: {str(e)}",
                "completed_at": datetime.now(),
                "error": str(e),
            }
        )


def _format_forecast_result(forecast_result: ForecastResult) -> Dict[str, Any]:
    """
    予測結果のフォーマット
    """

    return {
        "sku": forecast_result.sku,
        "model_used": forecast_result.model_used,
        "forecast": [
            {
                "date": date_str,
                "value": value,
                "confidence_intervals": {
                    level: {
                        "lower": intervals["lower"][i]
                        if i < len(intervals["lower"])
                        else None,
                        "upper": intervals["upper"][i]
                        if i < len(intervals["upper"])
                        else None,
                    }
                    for level, intervals in forecast_result.confidence_intervals.items()
                },
            }
            for i, (date_str, value) in enumerate(
                zip(forecast_result.forecast_dates, forecast_result.point_forecasts)
            )
        ],
        "metadata": forecast_result.metadata,
    }
