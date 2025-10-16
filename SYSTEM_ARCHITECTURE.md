# システムアーキテクチャ

## 概要

デジタル価格表システムは、Django + HTMX による「HTML over the wire」思想に基づいたWebアプリケーションです。

## アーキテクチャ図

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ブラウザ      │    │   Djangoサーバー │    │   SQLiteDB      │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   HTMX      │◄├────┤►│    Views    │◄├────┤►│   Models    │ │
│ │ Bootstrap   │ │    │ │  Templates  │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 技術スタック

### フロントエンド
- **HTMX 1.9.10**: サーバーサイドレンダリング + 部分更新
- **Bootstrap 5.1.3**: UIフレームワーク
- **最小限のJavaScript**: HTMX補完用のみ

### バックエンド
- **Django 4.2.7**: Webフレームワーク
- **SQLite**: データベース（開発環境）
- **Python 3.x**: プログラミング言語

## データベース設計

### 主要テーブル

```sql
-- 商品マスタ
CREATE TABLE products_master_product (
    id INTEGER PRIMARY KEY,
    product_number INTEGER UNIQUE,  -- 自動採番
    product_name VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT '',  -- 申請ステータス
    is_active BOOLEAN DEFAULT TRUE, -- 論理削除フラグ
    created_at DATETIME,
    updated_at DATETIME
);

-- 価格履歴
CREATE TABLE products_master_pricehistory (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products_master_product(id),
    effective_year_month VARCHAR(7),  -- YYYY/MM
    wholesale_price VARCHAR(50),      -- 仕切価格
    kenren_price VARCHAR(50),         -- 県連価格
    gross_margin_rate DECIMAL(10,6),  -- 粗利率
    is_active BOOLEAN DEFAULT TRUE
);

-- 承認テーブル（商品）
CREATE TABLE products_master_productapproval (
    id INTEGER PRIMARY KEY,
    product_number INTEGER,  -- 正の値=既存商品、負の値=新規商品
    -- 商品情報フィールド（Productと同じ構成）
    applicant VARCHAR(100)   -- 申請者
);

-- 承認テーブル（価格履歴）
CREATE TABLE products_master_pricehistoryapproval (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products_master_productapproval(id),
    -- 価格履歴フィールド（PriceHistoryと同じ構成）
    is_delete_request BOOLEAN DEFAULT FALSE  -- 削除申請フラグ
);
```

## アプリケーション構成

### ディレクトリ構造

```
dashboard/products_master/
├── product_list/          # 商品一覧機能
│   └── views.py
├── product_detail/        # 商品詳細・承認機能
│   └── views.py
├── product_create/        # 商品作成・編集機能
│   └── views.py
├── integrated_pricelist/  # デジタル価格表機能
│   └── views.py
├── models.py             # データモデル定義
├── forms.py              # フォーム定義
└── urls.py               # URL設定
```

### 機能モジュール分割

1. **product_list**: 商品一覧・検索・ページネーション
2. **product_detail**: 商品詳細・リアルタイム編集・申請機能
3. **product_create**: 商品作成・編集・削除申請
4. **integrated_pricelist**: デジタル価格表表示

## HTMX設計パターン

### 部分更新パターン

```html
<!-- 県連価格の動的計算 -->
<input hx-get="/calc-kenren-price/{{ history.pk }}/" 
       hx-target="#kenren-price-{{ history.pk }}"
       hx-trigger="input changed delay:500ms">

<!-- 新規行追加 -->
<button hx-get="/products/{{ product.pk }}/add-row/"
        hx-target="#price-history-table tbody"
        hx-swap="afterbegin">
```

### フォーム送信パターン

```html
<!-- 申請送信 -->
<button type="submit" 
        formaction="{% url 'submit_approval' product.pk %}"
        formmethod="post"
        onclick="submitApproval(this)">
```

## 承認ワークフロー

### フロー図

```
商品編集 → 申請 → 承認テーブル → 承認/却下 → マスタ反映/破棄
    ↓         ↓         ↓           ↓
  編集画面   申請画面   承認一覧    承認詳細
```

### 状態管理

1. **申請なし** (`status = ''`): 通常状態
2. **申請中** (`status = '申請中'`): 編集不可
3. **承認済み**: マスタ反映後、申請なし状態に戻る
4. **却下**: 申請なし状態に戻る

## セキュリティ設計

### CSRF保護
- 全フォームでCSRFトークン必須
- HTMX リクエストでもCSRF保護

### 権限制御
- 現在はOSユーザー名ベースの簡易認証
- 将来的にDjango認証システムに移行予定

## パフォーマンス最適化

### データベース最適化
- `select_related()` / `prefetch_related()` でN+1問題回避
- インデックス設定（period_year, product）

### フロントエンド最適化
- HTMX による部分更新でページ全体の再読み込み回避
- 最小限のJavaScript使用

## 運用・保守

### ログ設計
- デバッグ用print文（開発環境）
- 将来的にDjangoログシステムに移行

### バックアップ
- SQLiteファイルの定期バックアップ
- マイグレーションファイルの管理

### 監視
- Django管理画面でのデータ確認
- エラーログの監視