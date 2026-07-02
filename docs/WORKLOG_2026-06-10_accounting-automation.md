# 作業ログ: freee会計API連携 経理業務自動化モジュール + Claude AI機能

- **作業日**: 2026-06-10
- **ブランチ**: `claude/accounting-automation-api-it0jq8`
- **変更規模**: 45ファイル / +15,437行 / -65行（7コミット）
- **検証状態**: バックエンドテスト **59件全パス**、フロントエンド型チェック・本番ビルド成功

---

## 1. 背景・目的

経理業務（仕訳処理・売上集計と仕訳作成・経費精算・月次レポート出力）を自動化するため、
会計SaaS「freee」のAPIと連携する経理モジュールを既存の需要予測システム
（FastAPI + React + PostgreSQL、docker-compose構成）に統合した。
さらにClaude API（Anthropic）を活用したAI経理アシスタント機能を追加した。

### 期待されるアウトカム

- 売上の集計→仕訳起票→freee入力という手作業が「期間を選んで同期ボタンを押すだけ」になる
- 勘定科目の推定ルール化・AI推定と冪等な同期処理により、入力ミス・二重計上を仕組みで防ぐ
- 月次レポートが即時にExcel/CSVで出力でき、freee試算表と自社データを突き合わせられる

---

## 2. 実装した機能

### 2.1 freee接続管理（OAuth2）

- 認可コードフローによる実freeeアカウント接続（`GET /api/v1/accounting/freee/auth-url` → freee認可画面 → `GET /api/v1/accounting/freee/callback`）
- CSRF対策: stateにJWT署名（exp=10分）を使用
- トークンはFernet（`DATA_ENCRYPTION_KEY`）で暗号化してDB保存
- アクセストークンは期限5分前に自動リフレッシュ。401時は1回だけリフレッシュ&リトライ、429時は`Retry-After`を見て1回リトライ
- freeeのrefresh_tokenはローテーションされるため、リフレッシュ成功後に即DB保存
- 事業所(company)の選択・接続状態確認・切断API

### 2.2 売上の自動仕訳・freee自動登録

- 既存の注文データ(orders)を期間指定で日次/月次に集計し、freeeに収入取引(deals)として一括登録（`POST /api/v1/accounting/sales/sync`）
- `dry_run=true` で登録内容のプレビューが可能
- `JournalEntry` テーブルの UNIQUE(source_type, source_key) 制約により再実行しても二重登録されない（冪等）
- 失敗分は `POST /api/v1/accounting/journal-entries/{id}/retry` で再送可能
- 勘定科目マッピング（カテゴリ→freee勘定科目）のCRUD API

### 2.3 経費精算・支出管理

- 経費のCRUD（日付・金額・カテゴリ・支払方法・取引先・摘要）
- `POST /api/v1/accounting/expenses/{id}/sync` でfreeeに支出取引として登録

### 2.4 月次レポート出力

- `GET /api/v1/accounting/reports/monthly?year=&month=&format=xlsx|csv`
- Excelは4シート構成: 売上集計 / 経費一覧 / freee試算表（接続時のみ）/ 同期状況（openpyxl使用）
- freee損益計算書(PL)/貸借対照表(BS)試算表のJSON取得API

### 2.5 Claude AI機能（Anthropic公式SDK / claude-opus-4-8）

- **勘定科目のAI推定** (`POST /api/v1/accounting/ai/suggest-account-item`):
  取引のカテゴリ・摘要からfreeeの勘定科目一覧の中で最適な科目を構造化出力
  （科目ID・科目名・確信度・理由）で推定。候補に無いIDを返した場合は拒否する幻覚対策付き
- **月次レポートのAIサマリー** (`GET /api/v1/accounting/ai/monthly-summary`):
  売上・経費・前月比・同期状況をClaudeが分析し、経営者向けコメント
  （当月の概況／注目ポイント／来月への提案）を日本語Markdownで生成
- **同期フローへのAI自動仕訳統合**:
  売上/経費同期時の勘定科目決定が「マッピングルール → AI推定 → デフォルト科目」の
  3段フォールバックに。AI未設定・失敗時も同期は必ず成立する
- `ANTHROPIC_API_KEY` 未設定時はAI機能のみ503を返し、他機能には影響しない

### 2.6 フロントエンド（経理ページ）

- `http://localhost:3000/accounting` に「経理」ページを追加（ナビゲーションにも追加）
- タブ構成: freee接続 / 売上同期（dry_runプレビュー・仕訳一覧）/ 経費管理 / 月次レポート
- 経費フォームに「AIで勘定科目を推定」ボタン（確信度・理由を表示）
- 月次レポートタブに「AIサマリーを生成」ボタン
- 既存スタック（TanStack Query + react-hot-toast + Tailwind）を踏襲

---

## 3. コミット履歴

| コミット | 内容 |
|---|---|
| `64a5fd6` | fix: SQLAlchemy 2.0で起動不能になる既存バグを修正 |
| `d8880e2` | feat: freee会計API連携の経理自動化バックエンドを追加 |
| `55ce4f9` | test: 経理モジュールのpytestテスト一式を追加 |
| `c718226` | fix: フロントエンドのビルドを通らなくしていた既存エラーを修正 |
| `b637f46` | feat: 経理ページ（freee接続・売上同期・経費管理・月次レポート）を追加 |
| `4540f88` | feat: Claude APIによるAI経理アシスタント機能を追加 |
| `0459b20` | feat: 同期フローへのAI自動仕訳統合と経費フォームのAI科目サジェストを追加 |

---

## 4. 主な追加・変更ファイル

### バックエンド

```
backend/app/services/freee_token_store.py   # トークンのFernet暗号化保存・期限判定
backend/app/services/freee_client.py        # OAuthクライアント + freee APIクライアント（httpx）
backend/app/services/accounting_service.py  # 売上集計→仕訳生成→deals登録、勘定科目解決（ルール→AI→デフォルト）
backend/app/services/report_service.py      # 月次データ集計とExcel/CSV生成
backend/app/services/ai_service.py          # Claude API連携（科目推定・月次サマリー）
backend/app/api/v1/accounting/              # auth / master / sales_sync / expenses / reports / ai
backend/app/models.py                       # FreeeToken / AccountItemMapping / JournalEntry / Expense を追加
backend/alembic/versions/002_add_accounting_tables.py
backend/tests/                              # conftest + テスト59件（freee APIはrespx、Claude APIはスタブでモック）
backend/env.freee.example                   # 環境変数サンプル（FREEE_* / DATA_ENCRYPTION_KEY / ANTHROPIC_API_KEY）
backend/requirements.txt                    # respx==0.20.2, anthropic==0.109.1 を追加
```

### フロントエンド

```
frontend/src/api/accounting.ts                              # APIクライアント・型定義
frontend/src/pages/Accounting.tsx                           # タブ切替コンテナ
frontend/src/components/accounting/FreeeConnectionCard.tsx  # 接続状態・事業所選択・切断
frontend/src/components/accounting/SalesSyncPanel.tsx       # 期間指定・プレビュー・同期・仕訳一覧
frontend/src/components/accounting/ExpensePanel.tsx         # 経費CRUD・同期・AI科目サジェスト
frontend/src/components/accounting/MonthlyReportPanel.tsx   # レポートDL・試算表・AIサマリー
frontend/src/App.tsx, components/Layout.tsx                 # ルーティング・ナビ追加
```

### 既存バグ修正（今回の機能と独立）

- `backend/app/database.py`: SQLAlchemy 2.0 で `db.execute("SELECT 1")` が `text()` ラップ必須になっていた問題
- フロントエンドの型エラー等でビルドが通らなかった問題

---

## 5. セットアップ手順（ローカル）

```bash
git clone https://github.com/mil-shori/demand-forecast-system.git
cd demand-forecast-system
git checkout claude/accounting-automation-api-it0jq8

# 環境変数を設定（コミット禁止）
cp backend/env.freee.example backend/.env
# - FREEE_CLIENT_ID / FREEE_CLIENT_SECRET: freee開発者アプリの値
#   （redirect_uri に http://localhost:8000/api/v1/accounting/freee/callback を登録）
# - DATA_ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# - ANTHROPIC_API_KEY: https://platform.claude.com/ で取得（AI機能を使う場合）

docker compose up -d
docker compose exec backend alembic upgrade head

# 動作確認
# - http://localhost:8000/docs  … accountingタグのAPI一覧
# - http://localhost:3000/accounting … 経理ページ
docker compose exec backend pytest tests -v   # テスト実行
```

---

## 6. 設計上のポイント

- **冪等性**: `journal_entries` の UNIQUE(source_type, source_key) で二重登録を防止。SYNCEDはスキップ、FAILEDのみ再送対象
- **セキュリティ**: シークレットは `.env` 管理（.gitignore済み）。トークンはFernet暗号化してDB保存
- **graceful degradation**: freee未接続・AI未設定でも該当機能のみ503になり、既存の需要予測機能には一切影響しない
- **テスト**: 外部API（freee/Claude）は全てモック化し、ネットワーク無しで59件が実行可能
- **AI幻覚対策**: Claudeの科目推定は候補一覧のIDと突合し、実在しないIDは拒否

## 7. 残課題・今後の拡張候補

- [x] mainへのPR作成（2026-06-12 実施）
- [ ] freee経費精算API（申請フロー型）対応 — 現状は支出deal方式
- [ ] 勘定科目マッピングの管理UI（現状はAPIのみ。CRUDは `/api/v1/accounting/mappings`）
- [ ] 経費フォームのAI推定結果をマッピングとしてワンクリック保存する機能
- [x] CIワークフローへの `pytest` / `tsc` 組み込み（既存CIにあり。下記の通りCIが通る状態に修復）

---

## 8. 追記（2026-06-12）: CIグリーン化とPR作成

引き継ぎセッションでCI（.github/workflows/ci.yml）が通らない要因を全て解消した。

### 修正内容

| コミット | 内容 |
|---|---|
| `style:` setup.cfg追加 | flake8/isortに設定がなくblackと競合（行長79 vs 88）。設定を追加しbackend全体にblack/isortを適用、未使用import除去・E501/E712/E722解消 |
| `fix:` ESLint設定修正 | `.eslintrc.cjs` の `@typescript-eslint/recommended` は `plugin:` プレフィックス必須（初期コミット由来でlintが常に失敗）。あわせて `error: any` を `getApiErrorMessage` ヘルパーに置換 |
| `test:` jest整備 | jest設定が存在せず `npm test` が "No tests found" でexit 1。jest.config.cjs（ts-jest）と `getApiErrorMessage` の単体テスト5件を追加 |
| `fix:` pytest-cov追加 | CIは `pytest --cov=app` を実行するが pytest-cov 未導入で失敗していた |

### 検証結果（ローカル、CI同等コマンド）

- backend: `black --check` / `isort --check-only` / `flake8` / `pytest --cov=app` → **59件全パス**
- frontend: `npm run lint`（--max-warnings 0）/ `npm run type-check` / `npm test` / `npm run build` → 全て成功
