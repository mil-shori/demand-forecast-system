"""
データ検証・前処理サービス
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """検証ルール"""

    field: str
    rule_type: str  # required, type, range, pattern, custom
    parameters: Dict[str, Any]
    error_message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationResult:
    """検証結果"""

    valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]
    row_count: int
    processed_data: Optional[pd.DataFrame] = None
    statistics: Optional[Dict[str, Any]] = None


class DataValidator:
    """データ検証クラス"""

    def __init__(self):
        self.validation_rules = self._load_validation_rules()

    def _load_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """検証ルールを読み込む"""
        return {
            "orders": [
                ValidationRule(
                    field="order_id",
                    rule_type="required",
                    parameters={},
                    error_message="order_id は必須です",
                ),
                ValidationRule(
                    field="order_id",
                    rule_type="pattern",
                    parameters={"pattern": r"^ORD\d+$"},
                    error_message="order_id は 'ORD' で始まる形式である必要があります",
                ),
                ValidationRule(
                    field="user_id",
                    rule_type="required",
                    parameters={},
                    error_message="user_id は必須です",
                ),
                ValidationRule(
                    field="order_date",
                    rule_type="type",
                    parameters={"expected_type": "datetime"},
                    error_message="order_date は有効な日付形式である必要があります",
                ),
                ValidationRule(
                    field="order_date",
                    rule_type="range",
                    parameters={
                        "min_date": "2020-01-01",
                        "max_date": datetime.now().strftime("%Y-%m-%d"),
                    },
                    error_message="order_date は 2020年以降、今日以前である必要があります",
                ),
                ValidationRule(
                    field="order_type",
                    rule_type="choice",
                    parameters={"choices": ["subscription", "oneoff"]},
                    error_message="order_type は 'subscription' または 'oneoff' である必要があります",
                ),
                ValidationRule(
                    field="total_amount",
                    rule_type="range",
                    parameters={"min": 0, "max": 100000},
                    error_message="total_amount は 0円以上10万円以下である必要があります",
                    severity="warning",
                ),
                ValidationRule(
                    field="channel",
                    rule_type="choice",
                    parameters={"choices": ["web", "mobile", "phone", "other"]},
                    error_message="channel は有効なチャネル名である必要があります",
                    severity="warning",
                ),
            ],
            "order_items": [
                ValidationRule(
                    field="order_id",
                    rule_type="required",
                    parameters={},
                    error_message="order_id は必須です",
                ),
                ValidationRule(
                    field="sku",
                    rule_type="required",
                    parameters={},
                    error_message="sku は必須です",
                ),
                ValidationRule(
                    field="quantity",
                    rule_type="range",
                    parameters={"min": 1, "max": 100},
                    error_message="quantity は 1以上100以下である必要があります",
                ),
                ValidationRule(
                    field="unit_price",
                    rule_type="range",
                    parameters={"min": 0, "max": 50000},
                    error_message="unit_price は 0円以上5万円以下である必要があります",
                    severity="warning",
                ),
                ValidationRule(
                    field="discount_rate",
                    rule_type="range",
                    parameters={"min": 0.0, "max": 1.0},
                    error_message="discount_rate は 0.0以上1.0以下である必要があります",
                ),
            ],
            "products": [
                ValidationRule(
                    field="sku",
                    rule_type="required",
                    parameters={},
                    error_message="sku は必須です",
                ),
                ValidationRule(
                    field="sku",
                    rule_type="unique",
                    parameters={},
                    error_message="sku は一意である必要があります",
                ),
                ValidationRule(
                    field="product_name",
                    rule_type="required",
                    parameters={},
                    error_message="product_name は必須です",
                ),
                ValidationRule(
                    field="product_name",
                    rule_type="length",
                    parameters={"min": 1, "max": 200},
                    error_message="product_name は 1文字以上200文字以下である必要があります",
                ),
                ValidationRule(
                    field="base_price",
                    rule_type="range",
                    parameters={"min": 0, "max": 100000},
                    error_message="base_price は 0円以上10万円以下である必要があります",
                    severity="warning",
                ),
                ValidationRule(
                    field="is_set_item",
                    rule_type="boolean",
                    parameters={},
                    error_message="is_set_item は boolean値である必要があります",
                ),
            ],
        }

    def validate_dataframe(self, df: pd.DataFrame, data_type: str) -> ValidationResult:
        """データフレーム全体の検証"""

        if data_type not in self.validation_rules:
            return ValidationResult(
                valid=False,
                errors=[f"未対応のデータタイプ: {data_type}"],
                warnings=[],
                info=[],
                row_count=0,
            )

        rules = self.validation_rules[data_type]
        errors = []
        warnings = []
        info = []

        # 基本統計情報収集
        statistics = self._collect_statistics(df, data_type)

        # ルールごとの検証実行
        for rule in rules:
            result = self._apply_validation_rule(df, rule)

            if result["severity"] == "error":
                errors.extend(result["messages"])
            elif result["severity"] == "warning":
                warnings.extend(result["messages"])
            else:
                info.extend(result["messages"])

        # データクリーニング実行
        cleaned_df = self._clean_dataframe(df, data_type)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
            row_count=len(df),
            processed_data=cleaned_df,
            statistics=statistics,
        )

    def _apply_validation_rule(
        self, df: pd.DataFrame, rule: ValidationRule
    ) -> Dict[str, Any]:
        """個別ルールの適用"""

        messages = []

        if rule.field not in df.columns:
            if rule.rule_type == "required":
                messages.append(f"必須カラム '{rule.field}' が見つかりません")
            return {"severity": rule.severity, "messages": messages}

        series = df[rule.field]

        # ルール別処理
        if rule.rule_type == "required":
            null_count = series.isnull().sum()
            if null_count > 0:
                messages.append(f"{rule.field}: {null_count}件の欠損値があります")

        elif rule.rule_type == "type":
            expected_type = rule.parameters["expected_type"]
            if expected_type == "datetime":
                try:
                    pd.to_datetime(series, errors="coerce")
                except Exception as e:
                    messages.append(f"{rule.field}: 日付変換エラー - {str(e)}")

        elif rule.rule_type == "range":
            if "min" in rule.parameters:
                min_val = rule.parameters["min"]
                invalid_count = (series < min_val).sum()
                if invalid_count > 0:
                    messages.append(
                        f"{rule.field}: {invalid_count}件が最小値({min_val})未満です"
                    )

            if "max" in rule.parameters:
                max_val = rule.parameters["max"]
                invalid_count = (series > max_val).sum()
                if invalid_count > 0:
                    messages.append(
                        f"{rule.field}: {invalid_count}件が最大値({max_val})を超えています"
                    )

        elif rule.rule_type == "choice":
            choices = rule.parameters["choices"]
            invalid_mask = ~series.isin(choices)
            invalid_count = invalid_mask.sum()
            if invalid_count > 0:
                invalid_values = series[invalid_mask].unique()[:5]  # 最初の5件のみ表示
                messages.append(
                    f"{rule.field}: {invalid_count}件が無効な値です "
                    f"(例: {list(invalid_values)})"
                )

        elif rule.rule_type == "pattern":
            pattern = rule.parameters["pattern"]
            try:
                invalid_mask = ~series.str.match(pattern, na=False)
                invalid_count = invalid_mask.sum()
                if invalid_count > 0:
                    messages.append(f"{rule.field}: {invalid_count}件がパターンに一致しません")
            except Exception as e:
                messages.append(f"{rule.field}: パターン検証エラー - {str(e)}")

        elif rule.rule_type == "unique":
            duplicate_count = series.duplicated().sum()
            if duplicate_count > 0:
                duplicates = series[series.duplicated()].unique()[:5]
                messages.append(
                    f"{rule.field}: {duplicate_count}件の重複があります "
                    f"(例: {list(duplicates)})"
                )

        elif rule.rule_type == "length":
            min_len = rule.parameters.get("min", 0)
            max_len = rule.parameters.get("max", float("inf"))

            lengths = series.str.len()
            invalid_short = (lengths < min_len).sum()
            invalid_long = (lengths > max_len).sum()

            if invalid_short > 0:
                messages.append(f"{rule.field}: {invalid_short}件が短すぎます")
            if invalid_long > 0:
                messages.append(f"{rule.field}: {invalid_long}件が長すぎます")

        elif rule.rule_type == "boolean":
            try:
                # boolean変換テスト
                pd.to_numeric(series, errors="coerce")
            except Exception:
                messages.append(f"{rule.field}: boolean変換できない値があります")

        return {"severity": rule.severity, "messages": messages}

    def _clean_dataframe(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """データクリーニング"""

        cleaned_df = df.copy()

        # データタイプ別のクリーニング処理
        if data_type == "orders":
            # 日付の正規化
            if "order_date" in cleaned_df.columns:
                cleaned_df["order_date"] = pd.to_datetime(
                    cleaned_df["order_date"], errors="coerce"
                )

            # 金額のクリーニング
            if "total_amount" in cleaned_df.columns:
                cleaned_df["total_amount"] = pd.to_numeric(
                    cleaned_df["total_amount"], errors="coerce"
                )
                # 負の値を0に変換
                cleaned_df.loc[cleaned_df["total_amount"] < 0, "total_amount"] = 0

        elif data_type == "order_items":
            # 数量・価格のクリーニング
            numeric_fields = ["quantity", "unit_price", "discount_rate"]
            for field in numeric_fields:
                if field in cleaned_df.columns:
                    cleaned_df[field] = pd.to_numeric(
                        cleaned_df[field], errors="coerce"
                    )

        elif data_type == "products":
            # 価格のクリーニング
            if "base_price" in cleaned_df.columns:
                cleaned_df["base_price"] = pd.to_numeric(
                    cleaned_df["base_price"], errors="coerce"
                )

            # boolean値のクリーニング
            if "is_set_item" in cleaned_df.columns:
                cleaned_df["is_set_item"] = cleaned_df["is_set_item"].astype(bool)

            # activeフィールドのデフォルト値設定
            if "active" in cleaned_df.columns:
                cleaned_df["active"] = cleaned_df["active"].fillna(True)

        return cleaned_df

    def _collect_statistics(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """統計情報収集"""

        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "null_counts": df.isnull().sum().to_dict(),
            "data_types": df.dtypes.astype(str).to_dict(),
        }

        # データタイプ別の追加統計
        if data_type == "orders":
            if "order_date" in df.columns:
                try:
                    dates = pd.to_datetime(df["order_date"], errors="coerce")
                    stats["date_range"] = {
                        "min_date": dates.min().strftime("%Y-%m-%d")
                        if dates.min()
                        else None,
                        "max_date": dates.max().strftime("%Y-%m-%d")
                        if dates.max()
                        else None,
                    }
                except Exception:
                    pass

            if "order_type" in df.columns:
                stats["order_type_distribution"] = (
                    df["order_type"].value_counts().to_dict()
                )

            if "total_amount" in df.columns:
                amounts = pd.to_numeric(df["total_amount"], errors="coerce")
                stats["amount_statistics"] = {
                    "mean": round(amounts.mean(), 2)
                    if not amounts.isna().all()
                    else None,
                    "median": round(amounts.median(), 2)
                    if not amounts.isna().all()
                    else None,
                    "min": round(amounts.min(), 2)
                    if not amounts.isna().all()
                    else None,
                    "max": round(amounts.max(), 2)
                    if not amounts.isna().all()
                    else None,
                }

        elif data_type == "products":
            if "category" in df.columns:
                stats["category_distribution"] = df["category"].value_counts().to_dict()

            if "is_set_item" in df.columns:
                stats["set_item_distribution"] = (
                    df["is_set_item"].value_counts().to_dict()
                )

        return stats


class DataPreprocessor:
    """データ前処理クラス"""

    def __init__(self):
        self.validator = DataValidator()

    def preprocess_for_forecasting(
        self,
        orders_df: pd.DataFrame,
        order_items_df: pd.DataFrame,
        products_df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """予測用データの前処理"""

        logger.info("予測用データ前処理を開始")

        # 1. データ結合
        merged_df = self._merge_order_data(orders_df, order_items_df, products_df)

        # 2. 期間フィルタリング
        if start_date or end_date:
            merged_df = self._filter_by_date_range(merged_df, start_date, end_date)

        # 3. 日別需要データの作成
        daily_demand = self._create_daily_demand_data(merged_df)

        # 4. SKU別メタデータの作成
        sku_metadata = self._create_sku_metadata(merged_df, products_df)

        # 5. 特徴量の生成
        features = self._generate_features(daily_demand, merged_df)

        logger.info(f"前処理完了: {len(daily_demand)} レコード生成")

        return {
            "daily_demand": daily_demand,
            "sku_metadata": sku_metadata,
            "features": features,
            "raw_merged": merged_df,
        }

    def _merge_order_data(
        self,
        orders_df: pd.DataFrame,
        order_items_df: pd.DataFrame,
        products_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """注文関連データの結合"""

        # 注文と注文明細を結合
        merged = pd.merge(order_items_df, orders_df, on="order_id", how="left")

        # 商品情報を結合
        merged = pd.merge(
            merged,
            products_df[
                ["sku", "product_name", "category", "subcategory", "is_set_item"]
            ],
            on="sku",
            how="left",
        )

        # 日付型変換
        merged["order_date"] = pd.to_datetime(merged["order_date"])

        return merged

    def _filter_by_date_range(
        self, df: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]
    ) -> pd.DataFrame:
        """日付範囲フィルタリング"""

        filtered_df = df.copy()

        if start_date:
            start = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df["order_date"] >= start]

        if end_date:
            end = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df["order_date"] <= end]

        return filtered_df

    def _create_daily_demand_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """日別需要データの作成"""

        # SKU × 日付別の需要集計
        daily_demand = (
            df.groupby(["sku", "order_date"])
            .agg(
                {
                    "quantity": "sum",
                    "order_id": "nunique",
                    "total_amount": "sum",
                    "order_type": lambda x: (x == "subscription").sum(),  # 定期便数
                    "category": "first",
                    "subcategory": "first",
                }
            )
            .reset_index()
        )

        daily_demand.columns = [
            "sku",
            "ds",
            "y",
            "order_count",
            "revenue",
            "subscription_count",
            "category",
            "subcategory",
        ]

        # 単発セット数を計算
        daily_demand["oneoff_count"] = (
            daily_demand["order_count"] - daily_demand["subscription_count"]
        )

        return daily_demand

    def _create_sku_metadata(
        self, merged_df: pd.DataFrame, products_df: pd.DataFrame
    ) -> pd.DataFrame:
        """SKU別メタデータの作成"""

        sku_stats = (
            merged_df.groupby("sku")
            .agg(
                {
                    "quantity": ["sum", "mean", "std", "count"],
                    "order_date": ["min", "max"],
                    "order_type": lambda x: (x == "subscription").mean(),
                    "total_amount": "mean",
                }
            )
            .reset_index()
        )

        # カラム名の平坦化
        sku_stats.columns = [
            "sku",
            "total_quantity",
            "avg_quantity",
            "std_quantity",
            "order_frequency",
            "first_order_date",
            "last_order_date",
            "subscription_ratio",
            "avg_order_value",
        ]

        # 商品マスタ情報をマージ
        sku_metadata = pd.merge(sku_stats, products_df, on="sku", how="left")

        return sku_metadata

    def _generate_features(
        self, daily_demand: pd.DataFrame, merged_df: pd.DataFrame
    ) -> pd.DataFrame:
        """特徴量生成"""

        features_df = daily_demand.copy()

        # 日付特徴量
        features_df["dayofweek"] = features_df["ds"].dt.dayofweek
        features_df["month"] = features_df["ds"].dt.month
        features_df["quarter"] = features_df["ds"].dt.quarter
        features_df["is_weekend"] = features_df["dayofweek"].isin([5, 6]).astype(int)

        # ラグ特徴量（7日前、30日前）
        for lag in [7, 30]:
            features_df[f"lag_{lag}"] = (
                features_df.groupby("sku")["y"].shift(lag).fillna(0)
            )

        # 移動平均特徴量
        for window in [7, 14, 30]:
            features_df[f"ma_{window}"] = (
                features_df.groupby("sku")["y"]
                .rolling(window=window, min_periods=1)
                .mean()
                .reset_index(0, drop=True)
            )

        return features_df
