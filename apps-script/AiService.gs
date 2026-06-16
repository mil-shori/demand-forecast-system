/**
 * Claude API（Anthropic）連携 — UrlFetchApp 経由
 *
 * - ANTHROPIC_API_KEY は Script Properties に保存
 * - 勘定科目のAI推定: 構造化出力(output_config.format)でJSONを強制し、候補に無いIDは拒否
 * - 月次サマリー: adaptive thinking で経営者向けコメントを生成
 *
 * Apps Script は公式SDKを使えないため Messages API を直接叩く。
 */

var ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';
var ANTHROPIC_VERSION = '2023-06-01';
var DEFAULT_MODEL = 'claude-opus-4-8';
var MAX_ACCOUNT_ITEMS_IN_PROMPT = 200;

/** AI機能が設定済みか */
function isAiConfigured() {
  return !!PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
}

function getAiStatus() {
  var props = PropertiesService.getScriptProperties();
  var configured = isAiConfigured();
  return { configured: configured, model: configured ? (props.getProperty('ANTHROPIC_MODEL') || DEFAULT_MODEL) : null };
}

function callClaude(body) {
  var props = PropertiesService.getScriptProperties();
  var key = props.getProperty('ANTHROPIC_API_KEY');
  if (!key) throw new Error('ANTHROPIC_API_KEY が未設定です。スクリプト プロパティに登録してください。');
  body.model = body.model || props.getProperty('ANTHROPIC_MODEL') || DEFAULT_MODEL;

  var resp = UrlFetchApp.fetch(ANTHROPIC_API_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'x-api-key': key, 'anthropic-version': ANTHROPIC_VERSION },
    payload: JSON.stringify(body),
    muteHttpExceptions: true,
  });
  var code = resp.getResponseCode();
  var text = resp.getContentText();
  if (code === 429) throw new Error('Claude APIのレート制限に達しました。しばらく待って再実行してください。');
  if (code >= 400) throw new Error('Claude API エラー (' + code + '): ' + text);
  return JSON.parse(text);
}

/** content 配列から text ブロックを連結 */
function extractText(response) {
  return (response.content || [])
    .filter(function (b) { return b.type === 'text'; })
    .map(function (b) { return b.text; })
    .join('');
}

/**
 * 取引内容から最適な勘定科目をClaudeに推定させる。
 * 候補一覧に存在しないIDが返った場合はエラー（幻覚対策）。
 * @return {{account_item_id:number, account_item_name:string, confidence:number, reason:string}}
 */
function aiSuggestAccountItem(accountItems, description, category, transactionType) {
  var candidates = accountItems
    .filter(function (i) { return i.id && i.name; })
    .slice(0, MAX_ACCOUNT_ITEMS_IN_PROMPT)
    .map(function (i) { return { id: i.id, name: i.name }; });
  var candidatesText = candidates.map(function (c) { return '- id=' + c.id + ': ' + c.name; }).join('\n');
  var typeLabel = transactionType === 'income' ? '収入（売上）' : '支出（経費）';

  var schema = {
    type: 'object',
    properties: {
      account_item_id: { type: 'integer' },
      account_item_name: { type: 'string' },
      confidence: { type: 'number' },
      reason: { type: 'string' },
    },
    required: ['account_item_id', 'account_item_name', 'confidence', 'reason'],
    additionalProperties: false,
  };

  var response = callClaude({
    max_tokens: 1024,
    system: 'あなたは日本の中小企業の経理を担当する公認会計士です。取引内容から、freee会計の勘定科目一覧の中で最も適切な勘定科目を1つ選びます。必ず候補一覧に存在するidとnameの組み合わせを返してください。',
    output_config: { format: { type: 'json_schema', schema: schema } },
    messages: [{
      role: 'user',
      content: '以下の取引に最適な勘定科目を選んでください。\n\n' +
        '取引種別: ' + typeLabel + '\n' +
        'カテゴリ: ' + category + '\n' +
        '摘要: ' + (description || '（なし）') + '\n\n' +
        '勘定科目の候補一覧:\n' + candidatesText,
    }],
  });

  var parsed = JSON.parse(extractText(response));
  var validIds = {};
  candidates.forEach(function (c) { validIds[c.id] = true; });
  if (!validIds[parsed.account_item_id]) {
    throw new Error('AIが候補一覧に存在しない勘定科目ID（' + parsed.account_item_id + '）を返しました。');
  }
  return parsed;
}

/** AI推定の安全版: 未設定・失敗時は null を返し、呼び出し側がデフォルト科目にフォールバック */
function aiSuggestAccountItemSafe(accountItems, description, category, transactionType) {
  if (!isAiConfigured()) return null;
  try {
    return aiSuggestAccountItem(accountItems, description, category, transactionType);
  } catch (e) {
    Logger.log('AI suggestion failed, falling back to default: ' + e);
    return null;
  }
}

/**
 * 月次データをClaudeが分析し、経営者向けサマリー(Markdown)を生成する。
 * サイドバーから呼ばれる（year, month）。
 */
function generateMonthlySummary(year, month) {
  if (!isAiConfigured()) throw new Error('ANTHROPIC_API_KEY が未設定です。スクリプト プロパティに登録してください。');
  var data = collectMonthlyData(year, month);

  var salesLines = data.sales.map(function (s) {
    return '- ' + s.period + ' ' + (ORDER_TYPE_LABELS[s.order_type] || s.order_type) +
      ': ¥' + Math.round(s.amount).toLocaleString() + '（' + s.order_count + '件）';
  }).join('\n') || '（売上データなし）';
  var expenseLines = data.expenseByCategory.map(function (e) {
    return '- ' + e.category + ': ¥' + Math.round(e.amount).toLocaleString() + '（' + e.count + '件）';
  }).join('\n') || '（経費データなし）';

  var response = callClaude({
    max_tokens: 16000,
    thinking: { type: 'adaptive' },
    system: 'あなたは日本の中小企業（食品サブスクリプションEC）の財務アドバイザーです。' +
      '月次の売上・経費データを分析し、経営者向けの簡潔な日本語サマリーを書きます。' +
      '構成: (1)当月の概況 2〜3文、(2)注目ポイントを箇条書き3〜5個、(3)来月に向けた提案1〜2個。' +
      '数値は必ず提供されたデータに基づき、推測で数値を作らないでください。Markdown形式で出力してください。',
    messages: [{
      role: 'user',
      content: year + '年' + month + '月の月次データを分析してください。\n\n' +
        '売上合計: ¥' + Math.round(data.totalSales).toLocaleString() + '\n' +
        '経費合計: ¥' + Math.round(data.totalExpenses).toLocaleString() + '\n\n' +
        '日別売上:\n' + salesLines + '\n\n' +
        '経費カテゴリ別:\n' + expenseLines + '\n\n' +
        'freee同期状況: 登録済み' + data.syncStats.synced + '件 / 失敗' + data.syncStats.failed + '件 / 未送信' + data.syncStats.pending + '件',
    }],
  });

  var summary = extractText(response);
  if (!summary.trim()) throw new Error('AIサマリーの生成結果が空でした');
  return { year: year, month: month, summary: summary };
}
