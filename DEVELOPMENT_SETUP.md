# 需要予測システム 開発環境セットアップ手順書

## 概要
このドキュメントは需要予測システムの開発環境のセットアップと起動方法を説明します。

## 前提条件

### 必要なソフトウェア
- **Docker Desktop**: 最新版
- **Git**: 2.30.0以上
- **Node.js**: 18.x以上（フロントエンド開発時のみ）
- **Python**: 3.11以上（バックエンド開発時のみ）

### システム要件
- **メモリ**: 4GB以上
- **ストレージ**: 2GB以上の空き容量
- **OS**: Windows 10/11、macOS 10.15+、Ubuntu 20.04+

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-organization/demand-forecast.git
cd demand-forecast
```

### 2. 環境変数の設定

```bash
# バックエンド環境変数
cp backend/.env.example backend/.env
```

`.env`ファイルを編集し、必要に応じて設定値を変更してください：

```env
# データベース設定
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/demand_forecast_dev
POSTGRES_DB=demand_forecast_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# アプリケーション設定
API_V1_PREFIX=/api/v1
SECRET_KEY=your-secret-key-here
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]

# Redis設定（タスクキュー用）
REDIS_URL=redis://localhost:6379/0
```

### 3. Docker環境の構築・起動

```bash
# Docker Composeでサービスを起動
docker-compose up -d

# ログを確認する場合
docker-compose logs -f
```

### 4. データベースのセットアップ

```bash
# データベースマイグレーション実行
docker-compose exec backend alembic upgrade head

# サンプルデータの投入
docker-compose exec backend python scripts/load_sample_data.py
```

## 起動確認

### 1. サービス状態の確認

```bash
# コンテナ状態確認
docker-compose ps

# 期待される出力例:
#       Name                     Command               State           Ports
# --------------------------------------------------------------------------
# demand-forecast_backend_1    uvicorn app.main:app --h ...   Up      0.0.0.0:8000->8000/tcp
# demand-forecast_frontend_1   npm run dev                    Up      0.0.0.0:3000->3000/tcp
# demand-forecast_postgres_1   docker-entrypoint.sh postgres Up      0.0.0.0:5432->5432/tcp
# demand-forecast_redis_1      docker-entrypoint.sh redis ...Up      0.0.0.0:6379->6379/tcp
```

### 2. API接続確認

```bash
# ヘルスチェックAPI
curl http://localhost:8000/api/v1/health

# 期待される出力:
# {"status":"healthy","timestamp":"2024-01-07T10:00:00Z","version":"1.0.0"}
```

### 3. フロントエンド接続確認

ブラウザで以下のURLにアクセス：
- **フロントエンド**: http://localhost:3000
- **APIドキュメント**: http://localhost:8000/docs

### 4. 機能テスト

#### A. データインポート機能
1. http://localhost:3000/data にアクセス
2. `data/sample/orders.csv`をアップロード
3. インポート成功を確認

#### B. 予測機能
1. http://localhost:3000/forecast にアクセス
2. 「予測開始」ボタンをクリック
3. 予測実行の開始を確認

## 開発時のワークフロー

### フロントエンド開発

```bash
# フロントエンドコンテナ内での作業
docker-compose exec frontend bash

# 依存関係の追加
npm install [package-name]

# 型チェック
npm run type-check

# リント
npm run lint

# テスト
npm run test
```

### バックエンド開発

```bash
# バックエンドコンテナ内での作業
docker-compose exec backend bash

# 依存関係の追加
pip install [package-name]
pip freeze > requirements.txt

# テスト実行
pytest

# マイグレーション作成
alembic revision --autogenerate -m "Description"

# マイグレーション適用
alembic upgrade head
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. TypeScriptエラー「モジュール 'react' が見つかりません」

**原因**: npm依存関係がインストールされていない

**解決方法**:
```bash
# フロントエンドの依存関係をインストール
docker-compose exec frontend npm install
```

#### 2. データベース接続エラー

**原因**: PostgreSQLコンテナが起動していない

**解決方法**:
```bash
# コンテナ状態確認
docker-compose ps

# PostgreSQLコンテナを再起動
docker-compose restart postgres

# ログ確認
docker-compose logs postgres
```

#### 3. ポート競合エラー

**原因**: 既に同じポートを使用するプロセスが動作中

**解決方法**:
```bash
# 使用中のポートを確認（macOS/Linux）
lsof -i :8000
lsof -i :3000

# プロセスを停止
kill -9 [PID]
```

#### 4. 予測実行でエラーが発生

**原因**: サンプルデータが不足またはRedisが起動していない

**解決方法**:
```bash
# Redisコンテナ確認
docker-compose logs redis

# サンプルデータ再投入
docker-compose exec backend python scripts/load_sample_data.py
```

### ログの確認方法

```bash
# 全サービスのログ
docker-compose logs -f

# 特定のサービスのログ
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis
```

### データベース操作

```bash
# PostgreSQLコンテナに接続
docker-compose exec postgres psql -U postgres -d demand_forecast_dev

# 主要テーブルの確認
\dt

# データ確認例
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM subscriptions;
```

## パフォーマンステスト

### 基本的な負荷テスト

```bash
# API負荷テスト（curlを使用）
for i in {1..10}; do
  curl -w "%{time_total}\n" -o /dev/null -s http://localhost:8000/api/v1/health
done
```

### 予測パフォーマンステスト

```bash
# 予測実行時間の測定
docker-compose exec backend python -c "
import time
from app.services.forecast_engine import ForecastEngine
engine = ForecastEngine()
start = time.time()
result = engine.generate_forecast(['VEG-ORG-001'], days=90)
print(f'Forecast time: {time.time() - start:.2f}s')
"
```

## 本番環境への移行準備

### 1. 環境変数の更新

```bash
# 本番用設定
DEBUG=False
SECRET_KEY=[強力なランダムキー]
DATABASE_URL=[本番データベースURL]
CORS_ORIGINS=["https://your-domain.com"]
```

### 2. セキュリティチェック

```bash
# 依存関係の脆弱性チェック
docker-compose exec backend pip-audit
docker-compose exec frontend npm audit
```

### 3. データバックアップ

```bash
# データベースダンプ
docker-compose exec postgres pg_dump -U postgres demand_forecast_dev > backup.sql
```

## サポートとリソース

- **技術仕様書**: `TECHNICAL_SPEC.md`
- **API仕様書**: http://localhost:8000/docs
- **問題報告**: GitHubのIssuesを使用
- **開発チーム連絡先**: [開発チームのメール]

---

**最終更新**: 2024年1月7日
**ドキュメントバージョン**: 1.0.0