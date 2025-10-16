# デジタル価格表システム

Django + HTMX で構築された商品価格管理システム

## 開発思想

このプロジェクトは **HTMX の「HTML over the wire」思想** に基づいて開発されています。

- サーバーサイド中心のアーキテクチャ
- 最小限のJavaScript
- 宣言的なHTML属性でのインタラクション定義

## 開発ガイドライン

新機能開発前に必読：

- [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md) - HTMX開発思想と実装パターン
- [TECHNICAL_CONVENTIONS.md](./TECHNICAL_CONVENTIONS.md) - 技術的約束事とコーディング規約

## プロジェクト構成

```
ZCS_DegitalValueList/
├── dashboard/
│   └── products_master/       # 商品マスタ管理アプリ
│       ├── product_list/      # 商品一覧機能
│       ├── product_detail/    # 商品詳細・承認機能
│       ├── product_create/    # 商品作成・編集機能
│       └── integrated_pricelist/ # デジタル価格表機能
├── templates/                 # HTMLテンプレート
│   ├── components/           # 共通コンポーネント
│   └── products_master/      # 商品マスタ用テンプレート
├── static/                   # 静的ファイル（CSS/JS）
├── digital_pricelist_system/ # プロジェクト設定
│   ├── breadcrumbs.py       # パンくずリスト管理
│   └── utils.py             # 共通ユーティリティ
├── DEVELOPMENT_GUIDELINES.md # 開発ガイドライン
├── TECHNICAL_CONVENTIONS.md  # 技術的約束事
└── Django_run.py            # 開発サーバー起動スクリプト
```

## 開発環境セットアップ

### 1. 仮想環境作成・有効化

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 2. 依存関係インストール

```bash
pip install django
pip install django-bootstrap5
```

### 3. データベース初期化

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. 開発サーバー起動

```bash
python Django_run.py
```

または

```bash
python manage.py runserver
```

## 主要機能

### 商品マスタ管理
- 商品一覧・検索・ページネーション
- 商品詳細・リアルタイム編集（HTMX）
- 価格履歴管理・動的追加・削除
- 粗利率自動算出・県連価格計算
- 商品コピー機能

### 承認ワークフロー
- 新規作成・更新・削除申請
- 価格履歴の追加・更新・削除申請
- 申請内容の差分表示
- 一括承認・個別承認・却下機能

### デジタル価格表
- 指定月時点での価格表表示
- 最新価格履歴の自動選択
- ページネーション対応

### 技術スタック
- **Backend**: Django 4.2.7
- **Frontend**: HTMX 1.9.10 + Bootstrap 5.1.3
- **Database**: SQLite (開発) / PostgreSQL (本番予定)
- **UI/UX**: サイドナビゲーション + レスポンシブデザイン

## 開発ルール

### ✅ 推奨
- サーバーサイドでのロジック処理
- HTMX属性での宣言的定義
- 1つのリクエストでの一括処理

### ❌ 禁止
- 複雑なJavaScript処理
- クライアントサイドでのAPI通信
- 個別フィールドの差分更新

## コミット規約

```
feat: 新機能追加
fix: バグ修正
docs: ドキュメント更新
style: コードスタイル修正
refactor: リファクタリング
test: テスト追加・修正
```

## ブランチ戦略

```
main: 本番環境
develop: 開発環境
feature/xxx: 機能開発
hotfix/xxx: 緊急修正
```