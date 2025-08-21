# ビルド・デプロイ手順書
# Build & Deployment Guide

需要予測システムのビルド・デプロイメント完全ガイド

## 目次

1. [前提条件](#前提条件)
2. [初回セットアップ](#初回セットアップ)
3. [ローカル開発環境](#ローカル開発環境)
4. [フロントエンドデプロイ](#フロントエンドデプロイ)
5. [バックエンドデプロイ](#バックエンドデプロイ)
6. [環境変数設定](#環境変数設定)
7. [継続的デプロイメント](#継続的デプロイメント)
8. [トラブルシューティング](#トラブルシューティング)

## 前提条件

### 必要なツール
- Node.js 18.17.0以上
- npm 9.6.7以上
- Git
- Docker & Docker Compose
- PostgreSQL (本番環境)

### 必要なアカウント
- GitHub アカウント
- Netlify アカウント
- クラウドプロバイダー (AWS/GCP/Azure) アカウント

## 初回セットアップ

### 1. リポジトリのクローン
```bash
git clone https://github.com/your-org/demand-forecast.git
cd demand-forecast
```

### 2. 環境変数ファイルの作成

#### フロントエンド環境変数
```bash
# フロントエンド環境変数をコピー
cp frontend/.env.example frontend/.env.local

# 開発環境用の設定を編集
nano frontend/.env.local
```

#### バックエンド環境変数
```bash
# バックエンド環境変数をコピー
cp backend/.env.example backend/.env

# データベース接続情報等を設定
nano backend/.env
```

### 3. 依存関係のインストール

#### フロントエンド
```bash
cd frontend
npm install
```

#### バックエンド
```bash
cd backend
pip install -r requirements.txt
```

## ローカル開発環境

### Docker Composeを使用した開発環境

#### 全体の起動
```bash
# プロジェクトルートで実行
docker-compose up -d
```

#### 個別サービスの起動
```bash
# データベースのみ
docker-compose up -d postgres redis

# フロントエンドのみ
docker-compose up -d frontend

# バックエンドのみ
docker-compose up -d backend
```

### 手動起動方法

#### データベース (PostgreSQL)
```bash
# Docker でPostgreSQLを起動
docker run --name demand-forecast-db \
  -e POSTGRES_DB=demand_forecast \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15
```

#### バックエンド起動
```bash
cd backend

# データベースマイグレーション実行
alembic upgrade head

# FastAPI開発サーバー起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### フロントエンド起動
```bash
cd frontend

# 開発サーバー起動
npm run dev
```

### 開発環境確認
- フロントエンド: http://localhost:3000
- バックエンド API: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

## フロントエンドデプロイ

### Netlifyへのデプロイ

#### 1. Netlifyアカウント設定
1. https://netlify.com にアクセス
2. GitHubアカウントでサインイン
3. "New site from Git" を選択
4. リポジトリを選択

#### 2. ビルド設定
```bash
# Build command
npm ci && npm run build

# Publish directory
frontend/dist

# Base directory
frontend/
```

#### 3. 環境変数設定 (Netlify Dashboard)
```bash
# 本番環境用環境変数
VITE_API_BASE_URL=https://api.demand-forecast.example.com
VITE_APP_VERSION=$COMMIT_REF
VITE_ENVIRONMENT=production
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_ERROR_REPORTING=true
VITE_GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX
VITE_SENTRY_DSN=https://xxxxxxxxxx@sentry.io/xxxxxxx
```

#### 4. ドメイン設定
```bash
# カスタムドメインを設定する場合
# Netlify Dashboard > Domain settings > Custom domains
# DNS設定: CNAMEレコードでNetlifyを指定
```

#### 5. デプロイ確認
```bash
# デプロイログの確認
# Netlify Dashboard > Deploys > View deploy

# サイトの動作確認
# https://your-site-name.netlify.app
```

### 手動ビルド・デプロイ

#### ローカルビルド
```bash
cd frontend

# 依存関係インストール
npm ci

# 型チェック
npm run type-check

# リンター実行
npm run lint

# ビルド実行
npm run build

# ビルド結果確認
npm run preview
```

#### ビルド結果の確認
```bash
# dist フォルダの内容確認
ls -la frontend/dist/

# ビルドサイズの確認
du -sh frontend/dist/
```

## バックエンドデプロイ

### 前提条件

#### データベース準備
```bash
# PostgreSQL データベースの作成
createdb demand_forecast

# マイグレーション実行
cd backend
alembic upgrade head
```

### コンテナ化

#### Dockerイメージの作成
```bash
# プロダクション用Dockerfileの作成
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# ポート公開
EXPOSE 8000

# アプリケーション起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

#### イメージのビルド
```bash
cd backend

# Dockerイメージのビルド
docker build -t demand-forecast-backend:latest .

# イメージの確認
docker images | grep demand-forecast
```

### AWS ECS デプロイ例

#### 1. ECRリポジトリの作成
```bash
# AWS CLIでECRリポジトリ作成
aws ecr create-repository --repository-name demand-forecast-backend

# Docker loginコマンド取得
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.ap-northeast-1.amazonaws.com
```

#### 2. イメージのプッシュ
```bash
# イメージにタグ付け
docker tag demand-forecast-backend:latest \
  123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/demand-forecast-backend:latest

# ECRにプッシュ
docker push 123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/demand-forecast-backend:latest
```

#### 3. ECSタスク定義
```json
{
  "family": "demand-forecast-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/demand-forecast-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:region:account:secret:name"},
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:region:account:secret:name"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/demand-forecast-backend",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## 環境変数設定

### フロントエンド環境変数

#### 開発環境 (`.env.local`)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
VITE_ENABLE_DEBUG_MODE=true
```

#### 本番環境 (Netlify設定)
```bash
VITE_API_BASE_URL=https://api.demand-forecast.example.com
VITE_ENVIRONMENT=production
VITE_ENABLE_DEBUG_MODE=false
VITE_GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX
```

### バックエンド環境変数

#### 開発環境 (`.env`)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/demand_forecast
SECRET_KEY=development-secret-key-change-in-production
ENVIRONMENT=development
DEBUG=true
```

#### 本番環境 (AWS Secrets Manager等)
```bash
DATABASE_URL=postgresql://user:pass@prod-db.amazonaws.com:5432/demand_forecast
SECRET_KEY=production-secret-key-32-characters-long
ENVIRONMENT=production
DEBUG=false
SENTRY_DSN=https://xxxxxxxxxx@sentry.io/xxxxxxx
```

## 継続的デプロイメント

### GitHub Actions設定

#### フロントエンド CI/CD
```yaml
# .github/workflows/frontend.yml
name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
    paths: ['frontend/**']
  pull_request:
    branches: [main]
    paths: ['frontend/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18.17.0'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Type check
        run: cd frontend && npm run type-check
      
      - name: Lint
        run: cd frontend && npm run lint
      
      - name: Test
        run: cd frontend && npm run test
      
      - name: Build
        run: cd frontend && npm run build
```

#### バックエンド CI/CD
```yaml
# .github/workflows/backend.yml
name: Backend CI/CD

on:
  push:
    branches: [main, develop]
    paths: ['backend/**']
  pull_request:
    branches: [main]
    paths: ['backend/**']

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd backend
          pytest
        env:
          DATABASE_URL: postgresql://postgres:password@localhost:5432/test_db

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to AWS ECS
        run: |
          # AWS ECS デプロイスクリプト
          echo "Deploy to production"
```

### デプロイフロー

#### 開発フロー
```bash
# 1. フィーチャーブランチで開発
git checkout -b feature/new-feature

# 2. 開発・テスト
git add .
git commit -m "Add new feature"

# 3. プルリクエスト作成
git push origin feature/new-feature
# GitHub上でPRを作成

# 4. コードレビュー・CI実行

# 5. developブランチにマージ
# → ステージング環境に自動デプロイ

# 6. mainブランチにマージ
# → 本番環境に自動デプロイ
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. フロントエンドビルドエラー
```bash
# Node.jsバージョン確認
node --version  # 18.17.0以上必要

# npm キャッシュクリア
npm cache clean --force

# node_modules再インストール
rm -rf node_modules package-lock.json
npm install
```

#### 2. API接続エラー
```bash
# CORS設定確認
# backend/app/main.py の allowed_origins 確認

# 環境変数確認
echo $VITE_API_BASE_URL

# ネットワーク接続テスト
curl -I https://api.demand-forecast.example.com/health
```

#### 3. データベース接続エラー
```bash
# 接続文字列確認
echo $DATABASE_URL

# データベース接続テスト
psql $DATABASE_URL -c "SELECT 1"

# マイグレーション状態確認
cd backend
alembic current
alembic upgrade head
```

#### 4. Netlify デプロイエラー
```bash
# ビルドログ確認
# Netlify Dashboard > Deploys > Failed deploy

# 環境変数確認
# Netlify Dashboard > Site settings > Environment variables

# ローカルビルドテスト
cd frontend
npm run build
```

### ログ確認方法

#### フロントエンド
```bash
# ブラウザコンソール
# F12 > Console タブ

# Netlify Function ログ
# Netlify Dashboard > Functions > View logs
```

#### バックエンド
```bash
# AWS CloudWatch ログ
aws logs describe-log-groups

# コンテナログ
docker logs container-name

# アプリケーションログ
tail -f /var/log/app.log
```

### パフォーマンス最適化

#### フロントエンド最適化
```bash
# バンドルサイズ分析
cd frontend
npm run build
npm run analyze

# 軽量化のポイント
- Code splitting実装
- 画像最適化
- CDN活用
- キャッシュ戦略
```

#### バックエンド最適化
```bash
# データベースクエリ最適化
- インデックス追加
- N+1問題解消
- クエリキャッシュ
- 接続プール設定
```

## セキュリティチェックリスト

### 本番デプロイ前チェック

- [ ] 環境変数に機密情報が含まれていない
- [ ] HTTPS通信が有効
- [ ] CORS設定が適切
- [ ] セキュリティヘッダーが設定済み
- [ ] APIキーが適切に管理されている
- [ ] データベース接続が暗号化されている
- [ ] ログに機密情報が出力されていない
- [ ] 依存関係の脆弱性チェック完了

### 定期メンテナンス

- [ ] 依存関係の更新 (月次)
- [ ] セキュリティパッチ適用 (随時)
- [ ] データベースバックアップ確認 (週次)
- [ ] ログローテーション設定 (必要に応じて)
- [ ] モニタリング設定確認 (月次)

## 関連ドキュメント

- [デプロイアーキテクチャ設計書](docs/DEPLOYMENT_ARCHITECTURE.md)
- [開発環境セットアップ](DEVELOPMENT_SETUP.md)
- [API仕様書](docs/API_SPECIFICATION.md)
- [Netlify公式ドキュメント](https://docs.netlify.com/)

---

**更新履歴**
- 2024-01-20: 初版作成
- 2024-01-20: Netlify設定追加
- 2024-01-20: CI/CD設定追加

**メンテナンス担当**: 開発チーム
**最終更新**: 2024-01-20