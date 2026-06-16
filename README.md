# freee経理アシスタント（Google スプレッドシート アドオン）

Google スプレッドシート上で動く経理業務自動化アドオンです。スプレッドシートの売上・経費データを
集計して freee会計API に取引として登録し、月次レポートの生成や、Claude API による勘定科目の
AI推定・月次サマリー生成を行います。

> このリポジトリは当初 FastAPI + React のローカルWebアプリ（需要予測システムの経理モジュール）
> として開発していましたが、**Google スプレッドシートのアドオンとして全面的に作り直しました**。
> 旧ローカルアプリの実装は Git 履歴に残っています。

## 主な機能

- **freee連携（OAuth2）**: スプレッドシートのサイドバーから freee に接続・事業所選択・切断
- **売上の自動仕訳**: `売上データ` シートを期間×注文タイプで集計し、freee に収入取引として一括登録
  （`仕訳ログ` シートで冪等性を担保し、再実行しても二重登録しない。dry-runプレビュー対応）
- **経費管理**: 経費の登録と freee への支出取引同期
- **月次レポート**: 売上・経費・同期状況を集計したレポートシートを生成
- **AI機能（Claude API）**: 勘定科目のAI推定（幻覚対策付き）、月次サマリーの自動生成

勘定科目は「マッピングシート → AI推定 → デフォルト科目」の順で決定します。

## 構成

```
demand-forecast-system/
├── apps-script/                  # Google Apps Script アドオン本体
│   ├── appsscript.json           # マニフェスト
│   ├── Code.gs / Auth.gs / FreeeClient.gs / Accounting.gs
│   ├── AiService.gs / Reports.gs / Setup.gs
│   ├── Sidebar.html / SidebarCss.html / SidebarJs.html
│   ├── .clasp.json.example
│   └── README.md                 # セットアップ・デモ手順（詳細）
├── docs/                         # 作業ログ
└── .github/workflows/ci.yml      # マニフェスト/構文チェック
```

## セットアップとデモの動かし方

詳細な手順は **[`apps-script/README.md`](apps-script/README.md)** を参照してください。概要:

1. Google スプレッドシートを作成し、`拡張機能 → Apps Script` で `apps-script/` の各ファイルを取り込む
   （または `clasp push`）
2. スクリプト プロパティに `FREEE_CLIENT_ID` / `FREEE_CLIENT_SECRET` /（任意）`ANTHROPIC_API_KEY` を登録
3. freee開発者アプリのコールバックURLに `https://script.google.com/macros/d/{SCRIPT_ID}/usercallback` を登録
4. スプレッドシートのメニュー「💴 経理アシスタント → サイドバーを開く」から操作

## 注意

- シークレット（Client Secret / APIキー）はスクリプト プロパティに保存し、リポジトリにはコミットしません。
- freeeへの登録は本番事業所に直接反映されます。デモは検証用事業所で行ってください。
