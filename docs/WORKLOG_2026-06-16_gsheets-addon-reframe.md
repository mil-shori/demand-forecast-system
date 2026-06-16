# 作業ログ: Google スプレッドシート アドオンへの全面リフレーミング

- **作業日**: 2026-06-16
- **ブランチ**: `claude/accounting-automation-api-it0jq8`
- **検証**: `apps-script/*.gs` の構文チェック（node --check）と `appsscript.json` のJSON検証をローカル/CIで実施

## 背景・方針転換

これまで FastAPI + React のローカルWebアプリ（需要予測システムの経理モジュール）として実装してきたが、
ユーザー判断により **「ローカルアプリを全面的にやめ、Google スプレッドシート上のアドオンとして作り直す」**
方針に変更。確認の結果、以下の2点を決定:

- 既存のローカルアプリ（backend/ + frontend/）は **削除して全面置換**
- freee会計API・Claude API の認証は **OAuth2フローを実装**（freeeは apps-script-oauth2 ライブラリ）

## 実施内容

### 1. Google Apps Script アドオンを新規構築（`apps-script/`）

| ファイル | 役割 |
|---|---|
| `appsscript.json` | マニフェスト（OAuthスコープ、OAuth2ライブラリ依存、アドオン設定） |
| `Code.gs` | カスタムメニュー・サイドバー起動・共通ヘルパー |
| `Auth.gs` | freee OAuth2（接続・コールバック・事業所選択・切断） |
| `FreeeClient.gs` | freee API 呼び出し（UrlFetchApp、429リトライ、company_id自動付与） |
| `Accounting.gs` | 売上集計・勘定科目推定・仕訳変換・freee登録・経費同期 |
| `AiService.gs` | Claude API（勘定科目AI推定・月次サマリー、Messages APIを直接呼び出し） |
| `Reports.gs` | 月次データ集計・レポートシート生成 |
| `Setup.gs` | データシートのテンプレート作成・サンプル投入・読み書きヘルパー |
| `Sidebar.html` / `SidebarCss.html` / `SidebarJs.html` | サイドバーUI（接続/売上同期/経費/レポートの4タブ） |
| `README.md` / `.clasp.json.example` | セットアップ・デモ手順 / clasp設定サンプル |

### 2. データモデルの移植（PostgreSQL → スプレッドシート）

| シート | 旧テーブル相当 |
|---|---|
| `売上データ` | orders |
| `経費` | expenses |
| `勘定科目マッピング` | account_item_mappings |
| `仕訳ログ` | journal_entries（`(source_type, source_key)` で冪等性を担保） |

### 3. ロジックの移植

旧 `accounting_service.py` の売上集計・勘定科目リゾルバ（完全一致→keyword部分一致）・
deal ペイロード生成・3段フォールバック（マッピング→AI推定→デフォルト科目）・冪等同期を
そのまま Apps Script に移植。AIの幻覚対策（候補に無い勘定科目IDを拒否）も維持。

### 4. 認証方式

- **freee**: apps-script-oauth2 ライブラリで認可コードフロー。トークンは UserProperties に保存され、
  期限切れ時は自動リフレッシュ。client_id/secret は Script Properties。
  コールバックURLは `https://script.google.com/macros/d/{SCRIPT_ID}/usercallback`。
- **Claude**: API キーを Script Properties に保存し、Messages API を UrlFetchApp で直接呼び出し
  （勘定科目推定は `output_config.format` で構造化出力、月次サマリーは adaptive thinking）。

### 5. 旧ローカルアプリの削除

`backend/`、`frontend/`、`data/`、`docker-compose.yml`、`netlify.toml`、
`BUILD_DEPLOYMENT.md`、`DEVELOPMENT_SETUP.md`、`docs/DEPLOYMENT_ARCHITECTURE.md` を削除。
CI（`.github/workflows/ci.yml`）は、削除した backend/frontend のテストから、
アドオンのマニフェスト検証＋`.gs` 構文チェックに置き換え。

## デモの動かし方（概要）

1. スプレッドシート作成 → `拡張機能 → Apps Script` に `apps-script/` を取り込む（または `clasp push`）
2. スクリプト プロパティに `FREEE_CLIENT_ID` / `FREEE_CLIENT_SECRET` /（任意）`ANTHROPIC_API_KEY` を登録
3. freee開発者アプリにコールバックURLを登録
4. メニュー「💴 経理アシスタント → サイドバーを開く」→ シート初期化＆サンプル投入 → freee接続 →
   売上同期（dry-run→本実行）→ 経費追加・同期 → 月次レポート生成・AIサマリー

詳細は `apps-script/README.md` を参照。

## 追記（2026-06-16）: 拡張機能（エディタアドオン）としてインストール可能に

「拡張機能としてインストールできるか」という要望に対応。現状の `onOpen`/`onInstall` +
HtmlService サイドバー構成はエディタアドオンとしてそのまま配布できるため、以下を実施:

- `appsscript.json` をエディタアドオン向けに整理（GWA向けの `addOns` ブロックと未使用の
  `userinfo.email` スコープを削除。スコープは `spreadsheets.currentonly` /
  `script.container.ui` / `script.external_request` の最小構成）
- `apps-script/README.md` に「拡張機能（アドオン）としてインストールする」手順を追加
  - スタンドアロン化（clasp）→ テストデプロイで自分用インストール（審査不要）
  - Google Workspace Marketplace SDK で組織内（限定公開・審査不要）/ 一般公開（OAuth検証要）
- トップ README にも導線を追記

## 残課題

- [ ] 実際の Apps Script プロジェクトへのデプロイと、実freeeアカウントでのE2E動作確認
- [ ] 一般公開する場合の OAuth 検証（セキュリティ審査）対応
- [ ] GAS用のテスト（GAS単体テストは難しいため、ロジックを純関数化して clasp 外で検証する余地）
