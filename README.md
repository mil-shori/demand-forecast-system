# 需要予測システム (Demand Forecast System)

定期便（中身変更可能）と単発セット購入を同時に扱う需要予測システムです。

## システム概要

- **対象規模**: 月間注文数〜10万件、SKU数〜1000、同時利用者〜10名
- **予測手法**: StatsForecast (AutoARIMA/AutoETS/Croston)
- **アーキテクチャ**: Python/FastAPI + React + PostgreSQL

## プロジェクト構造

```
demand-forecast/
├── backend/                # Python/FastAPI バックエンド
│   ├── app/               # アプリケーションコード
│   ├── alembic/           # DBマイグレーション
│   ├── tests/             # テストコード
│   └── requirements.txt   # Python依存関係
├── frontend/              # React フロントエンド
│   ├── src/               # ソースコード
│   ├── public/            # 静的ファイル
│   └── package.json       # Node.js依存関係
├── data/                  # サンプルデータ・CSV
├── docs/                  # ドキュメント
├── infrastructure/        # AWS CloudFormation/CDK
├── scripts/               # 運用スクリプト
└── docker-compose.yml     # 開発環境
```

## クイックスタート

### 開発環境セットアップ

```bash
# リポジトリクローン
git clone <repository-url>
cd demand-forecast

# Docker Compose で開発環境起動
docker-compose up -d

# バックエンド開発サーバー起動
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# フロントエンド開発サーバー起動
cd frontend
npm install
npm start
```

### 主要機能

1. **データ管理**
   - Excel/CSV ファイル取り込み
   - データ品質チェック・検証
   - データ前処理・クレンジング

2. **需要予測**
   - SKU別需要予測（日次・週次）
   - 定期便ミックス予測
   - 季節性・トレンド分析

3. **発注提案**
   - サービスレベル別推奨発注量
   - 在庫シミュレーション
   - MOQ・リードタイム考慮

4. **監視・分析**
   - 予測精度監視
   - ビジネス指標ダッシュボード
   - アラート・通知

## 技術スタック

### バックエンド
- **Python 3.11**
- **FastAPI** - REST API フレームワーク
- **SQLAlchemy** - ORM
- **PostgreSQL** - データベース
- **StatsForecast** - 時系列予測
- **Pandas/Polars** - データ処理

### フロントエンド
- **React 18** + **TypeScript**
- **Tailwind CSS** - スタイリング
- **Chart.js** - グラフ表示
- **React Query** - API状態管理

### インフラストラクチャ
- **AWS EC2** (t3.small) - アプリケーションサーバー
- **AWS RDS** (PostgreSQL) - データベース
- **AWS S3** - ファイルストレージ
- **AWS CloudWatch** - 監視・ログ

## 開発・運用

### 開発フロー
1. 機能ブランチ作成
2. 開発・テスト実装
3. プルリクエスト作成
4. レビュー・承認
5. メインブランチマージ
6. CI/CDによる自動デプロイ

### 運用監視
- **ヘルスチェック**: `/health` エンドポイント
- **メトリクス**: CloudWatch メトリクス
- **ログ**: 構造化ログ (JSON形式)
- **アラート**: Slack通知

## ライセンス

MIT License

## サポート

- **技術的な問い合わせ**: [技術サポート連絡先]
- **運用に関する問い合わせ**: [運用サポート連絡先]