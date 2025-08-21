# デプロイアーキテクチャ設計書
# Deployment Architecture Design

需要予測システムのフロントエンドとバックエンドの分離デプロイ戦略

## 概要

本システムは、フロントエンド（React/Vite）とバックエンド（FastAPI/Python）を独立してデプロイする分離アーキテクチャを採用しています。

## アーキテクチャ図

```
┌─────────────────┐    HTTPS/API    ┌─────────────────┐
│   Frontend      │ ←──────────────→ │    Backend      │
│   (Netlify)     │                  │  (Cloud Service)│
│                 │                  │                 │
│ - React/Vite    │                  │ - FastAPI       │
│ - Static Assets │                  │ - PostgreSQL    │
│ - CDN           │                  │ - Redis         │
└─────────────────┘                  └─────────────────┘
         │                                    │
         │                                    │
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│   Monitoring    │                  │   Database      │
│                 │                  │                 │
│ - Lighthouse    │                  │ - PostgreSQL    │
│ - Analytics     │                  │ - Backup        │
│ - Error Track   │                  │ - Monitoring    │
└─────────────────┘                  └─────────────────┘
```

## フロントエンド デプロイ戦略

### プラットフォーム: Netlify

#### メリット
- 自動的なCDN配信
- HTTPS証明書の自動管理
- ブランチデプロイとプレビュー機能
- Form handling機能
- Edge Functions対応
- 高いパフォーマンス
- 簡単なセットアップ

#### デプロイフロー
1. **開発ブランチ**: 自動デプロイとプレビューURL生成
2. **プルリクエスト**: デプロイプレビューでレビュー
3. **マスターブランチ**: 本番環境への自動デプロイ

#### 環境設定
- **Production**: `main`ブランチからの自動デプロイ
- **Staging**: `develop`ブランチからの自動デプロイ
- **Preview**: プルリクエストからの一時的デプロイ

## バックエンド デプロイ戦略

### 推奨プラットフォーム候補

#### 1. AWS (推奨)
- **ECS Fargate**: コンテナベースのデプロイ
- **RDS PostgreSQL**: マネージドデータベース
- **ElastiCache Redis**: セッション管理・キャッシュ
- **Application Load Balancer**: ロードバランシング
- **CloudFront**: API向けCDN

#### 2. Google Cloud Platform
- **Cloud Run**: サーバーレスコンテナ
- **Cloud SQL**: マネージドPostgreSQL
- **Memorystore**: Redis管理サービス

#### 3. Microsoft Azure
- **Container Instances**: コンテナデプロイ
- **Azure Database for PostgreSQL**: マネージドDB
- **Azure Cache for Redis**: Redis管理サービス

## API通信設定

### CORS設定
```python
# backend/app/main.py
allowed_origins = [
    "https://demand-forecast.netlify.app",
    "https://develop--demand-forecast.netlify.app",
    "https://deploy-preview-*--demand-forecast.netlify.app"
]
```

### APIエンドポイント設定
- **Production**: `https://api.demand-forecast.example.com`
- **Staging**: `https://staging-api.demand-forecast.example.com`
- **Development**: `http://localhost:8000`

## セキュリティ戦略

### SSL/TLS
- フロントエンド: Netlifyが自動的にHTTPS証明書を管理
- バックエンド: CloudFrontまたはロードバランサーでSSL termination

### 認証・認可
- JWT tokenベースの認証
- HTTPS必須通信
- CORS適切な設定
- セキュリティヘッダーの設定

### 環境変数管理
- フロントエンド: Netlify環境変数
- バックエンド: クラウドプロバイダーのSecrets Manager

## CI/CDパイプライン

### フロントエンド (Netlify)
```yaml
# 自動的に実行される処理
Build Command: npm ci && npm run build
Publish Directory: frontend/dist
Environment Variables: Netlify Dashboard経由で設定
```

### バックエンド (GitHub Actions例)
```yaml
name: Deploy Backend
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to AWS ECS
        # デプロイスクリプト実行
```

## モニタリング戦略

### フロントエンド監視
- **Lighthouse CI**: パフォーマンス監視
- **Google Analytics**: ユーザー行動分析
- **Sentry**: エラートラッキング
- **Netlify Analytics**: サイト統計

### バックエンド監視
- **CloudWatch/Stackdriver**: システムメトリクス
- **Sentry**: エラートラッキング
- **Datadog/New Relic**: APM
- **Database監視**: クエリパフォーマンス

## 災害復旧戦略

### データバックアップ
- **データベース**: 日次自動バックアップ
- **ファイル**: S3/Cloud Storageでバックアップ
- **設定情報**: Infrastructure as Codeで管理

### RTO/RPO目標
- **RTO (Recovery Time Objective)**: 4時間以内
- **RPO (Recovery Point Objective)**: 1時間以内

## コスト最適化

### フロントエンド
- Netlify Free tier: 100GB bandwidth/month
- Pro plan: $19/month (追加機能・帯域)

### バックエンド
- 使用量ベースの料金体系
- Auto Scaling設定でコスト削減
- Reserved Instancesでコスト削減

## デプロイメント手順

### 初回セットアップ
1. Netlifyアカウント作成・リポジトリ連携
2. バックエンドインフラストラクチャ構築
3. 環境変数設定
4. DNS設定
5. 監視設定

### 継続的デプロイ
1. **開発**: feature branchで開発
2. **テスト**: プルリクエスト作成・レビュー
3. **ステージング**: developブランチマージでステージング環境デプロイ
4. **本番**: mainブランチマージで本番環境デプロイ

## トラブルシューティング

### 一般的な問題と対処法
1. **CORS Error**: バックエンドのallowed_origins設定確認
2. **環境変数未設定**: Netlify/クラウドコンソールで設定確認
3. **ビルドエラー**: Node.js/npmバージョン確認
4. **API接続エラー**: ネットワーク設定・セキュリティグループ確認

## 今後の改善計画

1. **Edge Computing**: Netlify Edge Functionsの活用
2. **CDN最適化**: API responseのキャッシュ戦略
3. **マイクロサービス化**: バックエンドの機能分割
4. **A/Bテスト**: Netlifyのsplit testing機能活用