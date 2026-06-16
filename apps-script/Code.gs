/**
 * freee経理アシスタント — Google スプレッドシート アドオン
 *
 * 既存の需要予測システム（FastAPI + React）の経理自動化機能を、
 * Google スプレッドシート上のアドオンとして全面的に作り直したもの。
 *
 * 機能:
 *  - freee会計APIとのOAuth2連携（接続・事業所選択・切断）
 *  - スプレッドシート上の売上データを集計し、freeeに取引(deal)として一括登録
 *  - 経費の登録とfreee同期
 *  - 月次レポートのシート生成
 *  - Claude API による勘定科目のAI推定・月次サマリー生成
 *
 * 構成: Code.gs(本ファイル) / Auth.gs / FreeeClient.gs / Accounting.gs /
 *       AiService.gs / Reports.gs / Setup.gs / Sidebar.html ほか
 */

/** スプレッドシート起動時にカスタムメニューを追加 */
function onOpen(e) {
  SpreadsheetApp.getUi()
    .createMenu('💴 経理アシスタント')
    .addItem('サイドバーを開く', 'showSidebar')
    .addSeparator()
    .addItem('シートを初期化（テンプレート作成）', 'initializeSheets')
    .addItem('サンプルデータを投入', 'seedSampleData')
    .addSeparator()
    .addItem('freeeに接続', 'showAuthPrompt')
    .addItem('freee接続を解除', 'disconnectFreee')
    .addToUi();
}

/** アドオンインストール時 */
function onInstall(e) {
  onOpen(e);
}

/** メインのサイドバーUIを表示 */
function showSidebar() {
  var html = HtmlService.createTemplateFromFile('Sidebar')
    .evaluate()
    .setTitle('freee経理アシスタント')
    .setWidth(360);
  SpreadsheetApp.getUi().showSidebar(html);
}

/** HTMLファイル内で他のHTMLファイル（JS/CSS）を読み込むためのヘルパー */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * サイドバー初期表示用の集約ステータス。
 * google.script.run から1回の呼び出しでまとめて取得する。
 */
function getAppStatus() {
  return {
    freee: getFreeeStatus(),
    ai: getAiStatus(),
    sheetsReady: areSheetsInitialized(),
  };
}
