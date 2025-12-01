# システムアーキテクチャ

## 概要

デジタル価格表システムは、Django + Web Components による「サーバーサイド中心 + 再利用可能UI部品」思想に基づいたWebアプリケーションです。

## アーキテクチャ図

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ブラウザ      │    │   Djangoサーバー │    │   SQLiteDB      │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │Web Components│◄├────┤►│    Views    │◄├────┤►│   Models    │ │
│ │ Bootstrap   │ │    │ │  Templates  │ │    │ │             │ │
│ │ AI Services │ │    │ │ AI Services │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 技術スタック

### フロントエンド
- **Web Components**: 再利用可能なUI部品
- **Bootstrap 5.1.3**: UIフレームワーク
- **最小限のJavaScript**: Web Components + 動的機能

### バックエンド
- **Django 5.2.7**: Webフレームワーク
- **SQLite**: データベース（開発環境）
- **Python 3.11+**: プログラミング言語

## データベース設計

### 主要テーブル

```sql
-- 商品マスタ
CREATE TABLE products_master_product (
    id INTEGER PRIMARY KEY,
    product_number INTEGER UNIQUE,  -- 自動採番
    product_name VARCHAR(200) NOT NULL,
    bigram_keywords TEXT,            -- 2-gram検索キーワード
    status VARCHAR(20) DEFAULT '',   -- 申請ステータス
    is_active BOOLEAN DEFAULT TRUE,  -- 論理削除フラグ
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

-- AI価格抽出トランザクション
CREATE TABLE products_master_aiextracttransaction (
    id INTEGER PRIMARY KEY,
    transaction_name VARCHAR(200),
    created_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE,   -- 論理削除フラグ
    deleted_at DATETIME              -- 論理削除日時
);

-- AI価格抽出明細
CREATE TABLE products_master_aiextractdetail (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER REFERENCES products_master_aiextracttransaction(id),
    extracted_name VARCHAR(500),     -- 抽出された商品名
    extracted_price VARCHAR(100),    -- 抽出された価格
    matched_product_id INTEGER,      -- マッチした商品ID
    match_score DECIMAL(5,2),        -- マッチスコア
    status VARCHAR(20),              -- 処理ステータス
    created_at DATETIME
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
│   ├── product_list_views.py
│   └── product_list_urls.py
├── product_detail/        # 商品詳細・承認機能
│   ├── product_detail_views.py
│   └── product_detail_urls.py
├── product_create/        # 商品作成・編集機能
│   ├── product_create_views.py
│   └── product_create_urls.py
├── integrated_pricelist/  # デジタル価格表機能
│   ├── integrated_pricelist_views.py
│   └── integrated_pricelist_urls.py
├── ai_extract/           # AI価格抽出機能
│   ├── ai_extract_views.py
│   └── ai_extract_urls.py
├── models.py             # データモデル定義
├── ai_extract_models.py  # AI抽出用モデル
├── ai_services.py        # AI関連サービス
├── product_services.py   # 商品関連サービス
├── forms.py              # フォーム定義
└── urls.py               # URL設定
```

### 機能モジュール分割

1. **product_list**: 商品一覧・検索・ページネーション・キーワード再生成
2. **product_detail**: 商品詳細・Web Components編集・申請機能
3. **product_create**: 商品作成・編集・削除申請
4. **integrated_pricelist**: デジタル価格表表示
5. **ai_extract**: AI価格抽出・商品マッチング・論理削除管理

## Web Components設計パターン

### 商品詳細編集コンポーネント

```html
<!-- 価格履歴動的編集 -->
<price-history-editor product-id="{{ product.pk }}">
  <!-- 県連価格自動計算 -->
  <input type="text" data-field="wholesale_price" 
         onchange="this.closest('price-history-editor').calculateKenrenPrice()">
  
  <!-- 行追加・削除 -->
  <button onclick="this.closest('price-history-editor').addRow()">追加</button>
  <button onclick="this.closest('price-history-editor').deleteRow(this)">削除</button>
</price-history-editor>
```

### AI価格抽出パターン

```html
<!-- 現在：JSON入力・処理 -->
<ai-extract-processor>
  <textarea data-field="json_input" placeholder="JSON形式で入力（テスト用）"></textarea>
  <button onclick="this.closest('ai-extract-processor').processExtraction()">処理開始</button>
</ai-extract-processor>

<!-- 将来：PDFアップロード・AI処理 -->
<pdf-upload-processor>
  <input type="file" accept=".pdf" data-field="pdf_file">
  <button onclick="this.closest('pdf-upload-processor').uploadAndProcess()">AI抽出開始</button>
  <div class="processing-status">Azure OpenAI API処理中...</div>
</pdf-upload-processor>

<!-- マッチング結果表示 -->
<matching-result-display>
  <div class="match-item" data-score="85.5">
    85.5% [12345] サンプル商品名
  </div>
</matching-result-display>
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

## AI価格抽出システム

### 現在の実装状況（テスト用）

```
JSON手動入力 → パース → 商品マッチング → 手動調整 → 申請/スキップ → 論理削除
      ↓         ↓         ↓           ↓         ↓
    入力画面   抽出処理  マッチング表示  編集画面  履歴詳細
```

### 将来の実装予定（本格運用）

```
PDFアップロード → Azure OpenAI API → JSON抽出 → 商品マッチング → 手動調整 → 申請/スキップ
       ↓              ↓            ↓         ↓           ↓
   アップロード画面   AI処理      エンティティ抽出  マッチング表示  編集画面
```

#### Azure OpenAI API連携
- **入力**: PDFファイル（価格表・カタログ等）
- **処理**: GPT-4による商品名・価格のエンティティ抽出
- **出力**: JSON形式の構造化データ
- **エラーハンドリング**: API制限・認識エラー対応

### マッチングアルゴリズム

1. **2-gram生成**: 商品名を2文字ずつ分割
2. **基本スコア**: 一致2-gram数 × 80点
3. **余剰減点**: マスタ余剰率 × 20点減点
4. **ボーナス加点**: 完全一致部分 × 15点
5. **閾値判定**: 50%以上で候補表示

### 論理削除システム

- **自動論理削除**: 全明細が「スキップ」「申請済み」状態
- **手動論理削除**: 削除ボタンクリック
- **物理削除**: 3カ月経過後に自動実行

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
- インデックス設定（product_number, effective_year_month）
- 2-gramキーワード事前生成による高速検索

### フロントエンド最適化
- Web Components による再利用可能なUI部品
- 最小限のJavaScript使用
- セッション管理の削減（直接リダイレクト）

### AI処理最適化
- バッチ処理による効率的なマッチング
- スコアリング計算の最適化
- 論理削除による不要データの除外

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