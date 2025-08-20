"""
需要予測エンジン
StatsForecastを使用した軽量・高速な時系列予測システム
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from statsforecast import StatsForecast
    from statsforecast.models import (
        AutoARIMA, AutoETS, CrostonClassic, CrostonOptimized, 
        SeasonalNaive, Naive, RandomWalkWithDrift
    )
    from statsforecast.utils import ConformalPrediction
except ImportError as e:
    logging.error(f"StatsForecast import error: {e}")
    # フォールバック実装用
    StatsForecast = None

from app.config import settings
from app.services.data_validation import DataPreprocessor

logger = logging.getLogger(__name__)


class ForecastModel(str, Enum):
    """予測モデル種別"""
    AUTO_ARIMA = "AutoARIMA"
    AUTO_ETS = "AutoETS"
    CROSTON_CLASSIC = "CrostonClassic"
    CROSTON_OPTIMIZED = "CrostonOptimized"
    SEASONAL_NAIVE = "SeasonalNaive"
    NAIVE = "Naive"
    RANDOM_WALK = "RandomWalkWithDrift"


@dataclass
class ForecastConfig:
    """予測設定"""
    horizon: int = 28  # 予測期間（日）
    frequency: str = "D"  # データ頻度
    season_length: int = 7  # 季節性の長さ（週）
    confidence_levels: List[float] = None
    models: List[ForecastModel] = None
    
    def __post_init__(self):
        if self.confidence_levels is None:
            self.confidence_levels = [80, 95]  # 80%, 95%信頼区間
        if self.models is None:
            self.models = [
                ForecastModel.AUTO_ARIMA,
                ForecastModel.AUTO_ETS,
                ForecastModel.CROSTON_CLASSIC
            ]


@dataclass
class ForecastResult:
    """予測結果"""
    sku: str
    model_used: str
    forecast_dates: List[str]
    point_forecasts: List[float]
    confidence_intervals: Dict[str, List[float]]  # {"80": [lower, upper], "95": [lower, upper]}
    historical_fitted: Optional[List[float]] = None
    model_performance: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None


class SKUClassifier:
    """SKU分類器：データ特性に応じた最適モデル選択"""
    
    @staticmethod
    def classify_sku(demand_data: pd.Series, sku_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """SKUの特性分析とモデル推奨"""
        
        # 基本統計
        non_zero_demand = demand_data[demand_data > 0]
        total_periods = len(demand_data)
        demand_periods = len(non_zero_demand)
        
        classification = {
            "sku": sku_metadata.get("sku", "unknown"),
            "total_periods": total_periods,
            "demand_periods": demand_periods,
            "intermittency": 1 - (demand_periods / total_periods) if total_periods > 0 else 1,
            "average_demand": non_zero_demand.mean() if len(non_zero_demand) > 0 else 0,
            "demand_variability": non_zero_demand.std() if len(non_zero_demand) > 1 else 0,
            "trend_strength": 0,  # 後で計算
            "seasonal_strength": 0,  # 後で計算
        }
        
        # 需要パターン分類
        if classification["intermittency"] > 0.75:
            classification["demand_pattern"] = "sporadic"
            classification["recommended_models"] = [ForecastModel.CROSTON_CLASSIC]
        elif classification["intermittency"] > 0.5:
            classification["demand_pattern"] = "intermittent"
            classification["recommended_models"] = [ForecastModel.CROSTON_OPTIMIZED, ForecastModel.AUTO_ETS]
        elif total_periods >= 90:  # 3ヶ月以上のデータがある場合
            classification["demand_pattern"] = "regular"
            classification["recommended_models"] = [ForecastModel.AUTO_ARIMA, ForecastModel.AUTO_ETS]
        elif total_periods >= 30:  # 1ヶ月以上
            classification["demand_pattern"] = "short_regular"
            classification["recommended_models"] = [ForecastModel.AUTO_ETS, ForecastModel.SEASONAL_NAIVE]
        else:
            classification["demand_pattern"] = "insufficient_data"
            classification["recommended_models"] = [ForecastModel.SEASONAL_NAIVE, ForecastModel.NAIVE]
        
        # 商品カテゴリ情報の追加
        classification["category"] = sku_metadata.get("category", "unknown")
        classification["is_set_item"] = sku_metadata.get("is_set_item", False)
        
        return classification


class SimpleForecastEngine:
    """シンプルな予測エンジン"""
    
    def __init__(self, config: Optional[ForecastConfig] = None):
        self.config = config or ForecastConfig()
        self.classifier = SKUClassifier()
        self.preprocessor = DataPreprocessor()
        
        # StatsForecast利用可否チェック
        if StatsForecast is None:
            logger.warning("StatsForecast not available, using fallback implementation")
            self.use_statsforecast = False
        else:
            self.use_statsforecast = True
    
    def generate_forecasts(
        self, 
        demand_data: pd.DataFrame,
        sku_metadata: Optional[pd.DataFrame] = None,
        horizon: Optional[int] = None
    ) -> Dict[str, ForecastResult]:
        """需要予測の実行"""
        
        logger.info(f"予測開始: {len(demand_data['sku'].unique())} SKU")
        
        horizon = horizon or self.config.horizon
        results = {}
        
        # SKU毎の予測実行
        for sku in demand_data['sku'].unique():
            try:
                sku_data = demand_data[demand_data['sku'] == sku].copy()
                sku_info = self._get_sku_metadata(sku, sku_metadata)
                
                result = self._forecast_single_sku(sku_data, sku_info, horizon)
                results[sku] = result
                
            except Exception as e:
                logger.error(f"SKU {sku} の予測でエラー: {str(e)}")
                # フォールバック予測
                results[sku] = self._fallback_forecast(sku, horizon)
        
        logger.info(f"予測完了: {len(results)} SKU")
        return results
    
    def _forecast_single_sku(
        self, 
        sku_data: pd.DataFrame, 
        sku_metadata: Dict[str, Any],
        horizon: int
    ) -> ForecastResult:
        """単一SKUの予測"""
        
        # データ準備
        ts_data = self._prepare_timeseries_data(sku_data)
        
        # SKU分類
        classification = self.classifier.classify_sku(ts_data['y'], sku_metadata)
        
        # 最適モデル選択
        best_model = self._select_best_model(classification, ts_data)
        
        # 予測実行
        if self.use_statsforecast:
            forecast_result = self._run_statsforecast(ts_data, best_model, horizon)
        else:
            forecast_result = self._run_fallback_forecast(ts_data, horizon)
        
        # 結果構築
        return ForecastResult(
            sku=sku_metadata.get('sku', 'unknown'),
            model_used=best_model.value if isinstance(best_model, ForecastModel) else str(best_model),
            forecast_dates=forecast_result['dates'],
            point_forecasts=forecast_result['values'],
            confidence_intervals=forecast_result['intervals'],
            metadata={
                'classification': classification,
                'data_points': len(ts_data),
                'last_date': ts_data['ds'].max().strftime('%Y-%m-%d')
            }
        )
    
    def _prepare_timeseries_data(self, sku_data: pd.DataFrame) -> pd.DataFrame:
        """時系列データの準備"""
        
        # 必要なカラムの存在確認
        required_cols = ['ds', 'y']
        if not all(col in sku_data.columns for col in required_cols):
            # カラム名のマッピング
            if 'order_date' in sku_data.columns and 'quantity' in sku_data.columns:
                sku_data = sku_data.rename(columns={
                    'order_date': 'ds',
                    'quantity': 'y'
                })
        
        # 日付でソート
        ts_data = sku_data[['ds', 'y']].copy()
        ts_data['ds'] = pd.to_datetime(ts_data['ds'])
        ts_data = ts_data.sort_values('ds')
        
        # 欠損日の補完（0で埋める）
        date_range = pd.date_range(
            start=ts_data['ds'].min(),
            end=ts_data['ds'].max(),
            freq='D'
        )
        
        full_range = pd.DataFrame({'ds': date_range})
        ts_data = pd.merge(full_range, ts_data, on='ds', how='left')
        ts_data['y'] = ts_data['y'].fillna(0)
        
        # unique_idカラムを追加（StatsForecast要件）
        ts_data['unique_id'] = 'sku'
        
        return ts_data[['unique_id', 'ds', 'y']]
    
    def _select_best_model(
        self, 
        classification: Dict[str, Any], 
        ts_data: pd.DataFrame
    ) -> ForecastModel:
        """最適モデルの選択"""
        
        recommended_models = classification.get('recommended_models', [])
        
        # データ量による調整
        if len(ts_data) < 30:
            return ForecastModel.SEASONAL_NAIVE
        elif len(ts_data) < 90:
            # 短期データには軽量なモデルを選択
            return ForecastModel.AUTO_ETS
        else:
            # 長期データには精度重視
            if ForecastModel.AUTO_ARIMA in recommended_models:
                return ForecastModel.AUTO_ARIMA
            elif ForecastModel.AUTO_ETS in recommended_models:
                return ForecastModel.AUTO_ETS
            else:
                return recommended_models[0] if recommended_models else ForecastModel.AUTO_ETS
    
    def _run_statsforecast(
        self, 
        ts_data: pd.DataFrame, 
        model: ForecastModel, 
        horizon: int
    ) -> Dict[str, Any]:
        """StatsForecastでの予測実行"""
        
        # モデルインスタンス作成
        model_instance = self._create_model_instance(model)
        
        # StatsForecastインスタンス作成
        sf = StatsForecast(
            models=[model_instance],
            freq=self.config.frequency,
            n_jobs=1  # 小規模運用のため並列度制限
        )
        
        try:
            # 予測実行
            forecasts = sf.forecast(df=ts_data, h=horizon)
            
            # 信頼区間計算
            forecasts_with_intervals = sf.forecast(
                df=ts_data, 
                h=horizon,
                prediction_intervals=ConformalPrediction(h=horizon)
            )
            
            # 結果の整理
            forecast_dates = pd.date_range(
                start=ts_data['ds'].max() + timedelta(days=1),
                periods=horizon,
                freq='D'
            ).strftime('%Y-%m-%d').tolist()
            
            point_forecasts = forecasts[model.value].tolist()
            
            # 信頼区間の抽出
            intervals = {}
            for level in self.config.confidence_levels:
                lo_col = f"{model.value}-lo-{level}"
                hi_col = f"{model.value}-hi-{level}"
                if lo_col in forecasts_with_intervals.columns and hi_col in forecasts_with_intervals.columns:
                    intervals[str(level)] = {
                        'lower': forecasts_with_intervals[lo_col].tolist(),
                        'upper': forecasts_with_intervals[hi_col].tolist()
                    }
            
            return {
                'dates': forecast_dates,
                'values': point_forecasts,
                'intervals': intervals
            }
            
        except Exception as e:
            logger.warning(f"StatsForecast実行エラー: {str(e)}, フォールバックを使用")
            return self._run_fallback_forecast(ts_data, horizon)
    
    def _create_model_instance(self, model: ForecastModel):
        """モデルインスタンスの作成"""
        
        season_length = self.config.season_length
        
        if model == ForecastModel.AUTO_ARIMA:
            return AutoARIMA(season_length=season_length, approximation=True)
        elif model == ForecastModel.AUTO_ETS:
            return AutoETS(season_length=season_length, model='ZZZ')
        elif model == ForecastModel.CROSTON_CLASSIC:
            return CrostonClassic()
        elif model == ForecastModel.CROSTON_OPTIMIZED:
            return CrostonOptimized()
        elif model == ForecastModel.SEASONAL_NAIVE:
            return SeasonalNaive(season_length=season_length)
        elif model == ForecastModel.NAIVE:
            return Naive()
        elif model == ForecastModel.RANDOM_WALK:
            return RandomWalkWithDrift()
        else:
            # デフォルトはAutoETS
            return AutoETS(season_length=season_length, model='ZZZ')
    
    def _run_fallback_forecast(self, ts_data: pd.DataFrame, horizon: int) -> Dict[str, Any]:
        """フォールバック予測（シンプルな手法）"""
        
        values = ts_data['y'].values
        
        # 季節性を考慮したnaive予測
        if len(values) >= 7:
            # 直近7日の平均を使用
            recent_avg = np.mean(values[-7:])
            seasonal_pattern = values[-7:] if len(values) >= 7 else [recent_avg] * 7
        else:
            recent_avg = np.mean(values) if len(values) > 0 else 0
            seasonal_pattern = [recent_avg]
        
        # 予測値生成
        forecasts = []
        for i in range(horizon):
            seasonal_idx = i % len(seasonal_pattern)
            forecast_val = max(0, seasonal_pattern[seasonal_idx])
            forecasts.append(forecast_val)
        
        # 予測日付
        forecast_dates = pd.date_range(
            start=ts_data['ds'].max() + timedelta(days=1),
            periods=horizon,
            freq='D'
        ).strftime('%Y-%m-%d').tolist()
        
        # 簡易信頼区間（±20%）
        intervals = {}
        for level in self.config.confidence_levels:
            factor = level / 100.0
            margin = np.array(forecasts) * (1 - factor) * 0.5
            intervals[str(level)] = {
                'lower': np.maximum(0, np.array(forecasts) - margin).tolist(),
                'upper': (np.array(forecasts) + margin).tolist()
            }
        
        return {
            'dates': forecast_dates,
            'values': forecasts,
            'intervals': intervals
        }
    
    def _get_sku_metadata(self, sku: str, sku_metadata: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """SKUメタデータの取得"""
        
        if sku_metadata is not None and not sku_metadata.empty:
            sku_row = sku_metadata[sku_metadata['sku'] == sku]
            if not sku_row.empty:
                return sku_row.iloc[0].to_dict()
        
        # デフォルト値
        return {
            'sku': sku,
            'category': 'unknown',
            'is_set_item': False
        }
    
    def _fallback_forecast(self, sku: str, horizon: int) -> ForecastResult:
        """エラー時のフォールバック予測"""
        
        forecast_dates = pd.date_range(
            start=datetime.now().date(),
            periods=horizon,
            freq='D'
        ).strftime('%Y-%m-%d').tolist()
        
        # 全て0の予測
        return ForecastResult(
            sku=sku,
            model_used="Fallback",
            forecast_dates=forecast_dates,
            point_forecasts=[0.0] * horizon,
            confidence_intervals={
                "80": {'lower': [0.0] * horizon, 'upper': [0.0] * horizon},
                "95": {'lower': [0.0] * horizon, 'upper': [0.0] * horizon}
            },
            metadata={'error': 'Fallback forecast used due to error'}
        )


class ForecastEvaluator:
    """予測精度評価クラス"""
    
    @staticmethod
    def calculate_accuracy_metrics(
        actual: pd.Series, 
        predicted: pd.Series
    ) -> Dict[str, float]:
        """精度指標の計算"""
        
        # 有効な値のみで計算
        mask = ~(pd.isna(actual) | pd.isna(predicted))
        actual_clean = actual[mask]
        predicted_clean = predicted[mask]
        
        if len(actual_clean) == 0:
            return {'error': 'No valid data points'}
        
        # 各指標の計算
        metrics = {}
        
        # MAE (Mean Absolute Error)
        metrics['mae'] = np.mean(np.abs(actual_clean - predicted_clean))
        
        # RMSE (Root Mean Square Error)
        metrics['rmse'] = np.sqrt(np.mean((actual_clean - predicted_clean) ** 2))
        
        # MAPE (Mean Absolute Percentage Error)
        mask_nonzero = actual_clean != 0
        if mask_nonzero.any():
            metrics['mape'] = np.mean(
                np.abs((actual_clean[mask_nonzero] - predicted_clean[mask_nonzero]) 
                       / actual_clean[mask_nonzero])
            ) * 100
        else:
            metrics['mape'] = float('inf')
        
        # wMAPE (weighted Mean Absolute Percentage Error)
        if actual_clean.sum() != 0:
            metrics['wmape'] = (
                np.sum(np.abs(actual_clean - predicted_clean)) / 
                np.sum(actual_clean)
            ) * 100
        else:
            metrics['wmape'] = float('inf')
        
        return metrics