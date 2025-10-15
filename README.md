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
├── dashboard/                  # メインアプリケーション
│   └── products_master/       # 商品マスタ管理
├── templates/                 # HTMLテンプレート
├── static/                    # 静的ファイル
├── DEVELOPMENT_GUIDELINES.md  # 開発ガイドライン
├── TECHNICAL_CONVENTIONS.md   # 技術的約束事
└── Django_run.py             # 開発サーバー起動スクリプト
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
- 商品一覧・検索
- 商品詳細・編集
- 価格履歴管理
- 承認フロー（実装予定）

### 技術スタック
- **Backend**: Django 4.x
- **Frontend**: HTMX + Bootstrap 5
- **Database**: SQLite (開発) / PostgreSQL (本番予定)

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