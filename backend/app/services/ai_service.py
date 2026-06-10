"""
Claude APIを使ったAI経理アシスタント

- 勘定科目の自動推定（ルールベースのマッピングで判定できない取引向け）
- 月次レポートのAIサマリー（経営コメント）生成
"""
import logging
from typing import Any, Dict, List, Optional

import anthropic
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

MAX_ACCOUNT_ITEMS_IN_PROMPT = 200


class AINotConfiguredError(Exception):
    """ANTHROPIC_API_KEY が未設定"""


class AccountItemSuggestion(BaseModel):
    """Claudeによる勘定科目推定の構造化出力"""
    account_item_id: int = Field(description="選択した勘定科目のID（候補一覧から選ぶこと）")
    account_item_name: str = Field(description="選択した勘定科目の名称")
    confidence: float = Field(description="推定の確信度（0.0〜1.0）")
    reason: str = Field(description="この勘定科目を選んだ理由（日本語・1〜2文）")


def is_configured() -> bool:
    return bool(settings.anthropic_api_key)


def _get_client() -> anthropic.AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise AINotConfiguredError(
            "ANTHROPIC_API_KEY が未設定です。backend/.env に設定してください。"
        )
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def suggest_account_item(
    description: str,
    category: str,
    transaction_type: str,
    account_items: List[Dict[str, Any]],
) -> AccountItemSuggestion:
    """
    取引内容（カテゴリ・摘要）から、freeeの勘定科目一覧の中で最適なものをClaudeに推定させる。

    ルールベースのマッピング（AccountItemMapping）で判定できない場合のフォールバックとして使う。
    """
    client = _get_client()

    candidates = [
        {"id": item.get("id"), "name": item.get("name")}
        for item in account_items[:MAX_ACCOUNT_ITEMS_IN_PROMPT]
        if item.get("id") and item.get("name")
    ]
    candidates_text = "\n".join(f"- id={c['id']}: {c['name']}" for c in candidates)

    type_label = "収入（売上）" if transaction_type == "income" else "支出（経費）"

    response = await client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=(
            "あなたは日本の中小企業の経理を担当する公認会計士です。"
            "取引内容から、freee会計の勘定科目一覧の中で最も適切な勘定科目を1つ選びます。"
            "必ず候補一覧に存在するidとnameの組み合わせを返してください。"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"以下の取引に最適な勘定科目を選んでください。\n\n"
                    f"取引種別: {type_label}\n"
                    f"カテゴリ: {category}\n"
                    f"摘要: {description or '（なし）'}\n\n"
                    f"勘定科目の候補一覧:\n{candidates_text}"
                ),
            }
        ],
        output_format=AccountItemSuggestion,
    )

    suggestion = response.parsed_output
    if suggestion is None:
        raise ValueError("AIによる勘定科目の推定結果を解析できませんでした")

    # 幻覚対策: 返されたIDが候補一覧に実在することを検証する
    valid_ids = {c["id"] for c in candidates}
    if suggestion.account_item_id not in valid_ids:
        raise ValueError(
            f"AIが候補一覧に存在しない勘定科目ID（{suggestion.account_item_id}）を返しました。再実行してください。"
        )
    return suggestion


async def generate_monthly_summary(
    year: int,
    month: int,
    sales: List[Dict[str, Any]],
    total_sales: float,
    total_expenses: float,
    expense_by_category: List[Dict[str, Any]],
    sync_stats: Dict[str, int],
    prev_month_sales: Optional[float] = None,
) -> str:
    """
    月次の売上・経費・同期状況をClaudeに分析させ、日本語の経営コメントを生成する。
    """
    client = _get_client()

    sales_lines = "\n".join(
        f"- {s['period']} {s['order_type']}: ¥{float(s['amount']):,.0f}（{s['order_count']}件）"
        for s in sales
    ) or "（売上データなし）"
    expense_lines = "\n".join(
        f"- {e['category']}: ¥{float(e['amount']):,.0f}（{e['count']}件）"
        for e in expense_by_category
    ) or "（経費データなし）"
    prev_line = (
        f"前月の売上合計: ¥{prev_month_sales:,.0f}\n" if prev_month_sales is not None else ""
    )

    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=(
            "あなたは日本の中小企業（食品サブスクリプションEC）の財務アドバイザーです。"
            "月次の売上・経費データを分析し、経営者向けの簡潔な日本語サマリーを書きます。"
            "構成: (1)当月の概況 2〜3文、(2)注目ポイントを箇条書き3〜5個、(3)来月に向けた提案1〜2個。"
            "数値は必ず提供されたデータに基づき、推測で数値を作らないでください。"
            "Markdown形式で出力してください。"
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"{year}年{month}月の月次データを分析してください。\n\n"
                    f"売上合計: ¥{total_sales:,.0f}\n"
                    f"経費合計: ¥{total_expenses:,.0f}\n"
                    f"{prev_line}\n"
                    f"日別売上:\n{sales_lines}\n\n"
                    f"経費カテゴリ別:\n{expense_lines}\n\n"
                    f"freee同期状況: 登録済み{sync_stats.get('synced', 0)}件 / "
                    f"失敗{sync_stats.get('failed', 0)}件 / 未送信{sync_stats.get('pending', 0)}件"
                ),
            }
        ],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    if not text.strip():
        raise ValueError("AIサマリーの生成結果が空でした")
    return text
