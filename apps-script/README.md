# freee経理アシスタント — Google スプレッドシート アドオン

Google スプレッドシート上で動く経理業務自動化アドオンです。スプレッドシートの売上・経費データを
集計し、freee会計APIに取引(deal)として登録、月次レポートの生成、Claude APIによる勘定科目の
AI推定・月次サマリー生成を行います。

> もともと FastAPI + React のローカルアプリとして実装していたものを、Google スプレッドシートの
> アドオンとして全面的に作り直したものです。

## 構成

| ファイル | 役割 |
|---|---|
| `appsscript.json` | マニフェスト（OAuthスコープ、OAuth2ライブラリ依存、アドオン設定） |
| `Code.gs` | メニュー・サイドバー起動・共通ヘルパー |
| `Auth.gs` | freee OAuth2（接続・事業所選択・切断） |
| `FreeeClient.gs` | freee API 呼び出し（UrlFetchApp、429リトライ） |
| `Accounting.gs` | 売上集計・勘定科目推定・仕訳変換・freee登録・経費同期 |
| `AiService.gs` | Claude API（勘定科目AI推定・月次サマリー） |
| `Reports.gs` | 月次データ集計・レポートシート生成 |
| `Setup.gs` | データシートのテンプレート作成・サンプル投入・読み書きヘルパー |
| `Sidebar.html` ほか | サイドバーUI（HTML/CSS/JS） |

## データモデル（スプレッドシートの各シート）

| シート | 内容 |
|---|---|
| `売上データ` | order_id, user_id, order_date, order_type(subscription/oneoff), total_amount |
| `経費` | id, expense_date, amount, category, description, payment_method, partner_name, status, freee_deal_id |
| `勘定科目マッピング` | mapping_type(SALES_CATEGORY/EXPENSE_CATEGORY), source_key, keywords, account_item_id, account_item_name, tax_code, partner_id, priority, active |
| `仕訳ログ` | source_type, source_key, entry_date, entry_type, description, amount, account_item_name, status, freee_deal_id, synced_at, error |

仕訳ログの `(source_type, source_key)` で冪等性を担保し、同じ売上を二重登録しません。

---

## セットアップ（デモの動かし方）

### 1. Apps Script プロジェクトを用意する

**方法A: スプレッドシートに直接（最短）**
1. Google スプレッドシートを新規作成
2. メニュー「拡張機能 → Apps Script」を開く
3. `apps-script/` 内の各 `.gs` / `.html` を、同じファイル名でエディタに作成して貼り付け
   （`appsscript.json` は「プロジェクトの設定 → マニフェスト ファイルをエディタで表示」をオンにして上書き）

**方法B: clasp（コマンドライン）**
```bash
npm install -g @google/clasp
clasp login
cd apps-script
cp .clasp.json.example .clasp.json   # scriptId を実際のIDに書き換え
clasp push
```

### 2. OAuth2 ライブラリを追加（方法Aの場合）

Apps Script エディタ → ライブラリ → スクリプトID
`1B7FSrk5Zi6L1rSxxTDgDEUsPzlukDsi4KGuTMorsTQHhGBzBkMun4iDF` を追加し、シンボルを `OAuth2` にする。
（`appsscript.json` を貼り付け済みなら自動で入ります）

### 3. スクリプト プロパティに認証情報を登録

エディタ → プロジェクトの設定 → スクリプト プロパティ に以下を追加:

| プロパティ | 値 |
|---|---|
| `FREEE_CLIENT_ID` | freee開発者アプリの Client ID |
| `FREEE_CLIENT_SECRET` | freee開発者アプリの Client Secret |
| `ANTHROPIC_API_KEY` | Claude APIキー（AI機能を使う場合のみ） |
| `ANTHROPIC_MODEL` | 任意。省略時 `claude-opus-4-8` |

### 4. freee開発者アプリにコールバックURLを登録

freee アプリ管理画面のコールバックURLに、次を登録します（`{SCRIPT_ID}` は自分のスクリプトID）:
```
https://script.google.com/macros/d/{SCRIPT_ID}/usercallback
```
このURLはサイドバーの「接続」タブにも表示されます。

### 5. 実行

1. スプレッドシートを再読み込み → メニュー「💴 経理アシスタント → サイドバーを開く」
2. 「接続」タブ:
   - 「シートを初期化」→「サンプル投入」でデモ用データを作成
   - 「freeeに接続」→ 別タブでfreeeにログイン・許可 →「再読込」→ 事業所を選択
3. 「売上同期」タブ: 期間を指定して「プレビュー」で登録内容を確認 →「freeeに同期」
   - 再度同期しても二重登録されないこと（status=skipped）を確認
4. 「経費」タブ: 経費を追加 →（AIキー設定時）「✨ AIで勘定科目を推定」→「未同期の経費をfreeeに同期」
5. 「レポート」タブ: 年月を指定して「月次レポートシートを生成」→（AIキー設定時）「✨ AIサマリーを生成」

---

## 勘定科目の決定ロジック

売上・経費の同期時、勘定科目は次の順で決まります（既存実装と同じ3段フォールバック）:

1. **マッピングシート** … `source_key` 完全一致 → `keywords` 部分一致（priority降順）
2. **AI推定** … Claudeがfreeeの勘定科目一覧から最適な科目を選択（候補に無いIDは拒否する幻覚対策付き）
3. **デフォルト科目** … 売上は「売上高」、経費は「雑費」をfreeeの勘定科目名から解決

`ANTHROPIC_API_KEY` 未設定時やAI呼び出し失敗時も、1→3 のフォールバックで同期は成立します。

## 注意

- シークレット（Client Secret / APIキー）はスクリプト プロパティに保存し、リポジトリにコミットしません。
- freeeへの登録は本番事業所に直接反映されます。デモは検証用事業所で行ってください。
