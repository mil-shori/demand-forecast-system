# せたがや子育て支援ナビ（非公式）

世田谷区の子育て家庭が、ご家庭の状況（妊娠中・子どもの年齢・ひとり親・障害・保育の利用状況など）を選ぶだけで、
申請できる可能性のある補助・手当を絞り込み、必要な提出書類のチェックリストを作成できる静的ウェブサイトです。

> **注意**: 本サイトは世田谷区の公式サイトではありません。掲載情報は 2026年7月時点の調査に基づく参考情報です。
> 金額・所得制限・必要書類は年度や個別の状況により変わるため、申請前に必ず
> [世田谷区公式ホームページ](https://www.city.setagaya.lg.jp/kodomokyouiku/kosodate/13020.html) または各窓口でご確認ください。

## 機能

1. **制度の絞り込み** — 妊娠中／子どもの年齢層／ひとり親世帯／障害のあるお子さん／保育・幼稚園の利用状況／所得制限の有無で、18の支援制度から該当候補を表示
2. **制度カード表示** — 支給額・対象・申請窓口・公式ページへのリンクを表示
3. **提出書類チェックリスト生成** — 選択した制度の必要書類を一覧化。複数の申請で共通する書類は先頭にまとめて表示
4. **出力** — 印刷（ブラウザのPDF保存）、テキストコピー、テキストファイルのダウンロードに対応

入力内容はすべてブラウザ内で処理され、外部に送信されません。

## 使い方

ビルド不要の静的サイトです。`index.html` をブラウザで開くだけで動作します。

```bash
# ローカルサーバーで開く場合
cd setagaya-benefits-finder
python3 -m http.server 8080
# → http://localhost:8080 を開く
```

## 構成

```
setagaya-benefits-finder/
├── index.html              # メインページ
├── css/style.css           # スタイル（印刷用CSS含む）
├── js/data.js              # 支援制度データ（制度・対象条件・必要書類）
├── js/matcher.js           # 絞り込み・チェックリスト生成ロジック（純粋関数）
├── js/app.js               # 画面制御
└── tests/matcher.test.mjs  # ロジックのテスト
```

## テスト

Node.js（v18以降）の標準テストランナーで実行できます。

```bash
node --test setagaya-benefits-finder/tests/
```

## 制度データの更新方法

`js/data.js` の `BENEFITS` 配列に制度を追加・修正します。各制度は以下の形式です。

```js
{
  id: 'unique-id',
  name: '制度名',
  category: '手当・給付金',
  amount: '支給額の目安',
  summary: '制度の概要',
  target: '対象者の説明',
  audience: { pregnancy: true, ages: ['0-2'] }, // いずれかに合致で対象
  requires: { singleParent: true },             // すべて満たす必要あり
  incomeLimit: true,                            // 所得制限の有無
  window: '申請窓口',
  url: '公式ページURL',
  documents: ['必要書類1', '必要書類2'],
  notes: '補足事項',
}
```

データを更新したら `node --test setagaya-benefits-finder/tests/` で整合性チェックが通ることを確認してください。
