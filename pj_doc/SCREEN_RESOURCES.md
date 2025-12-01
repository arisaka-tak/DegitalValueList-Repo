# 画面別リソース構成

## 1. ダッシュボード画面

### バックエンド
- **View**: `dashboard/views.py`
  - `dashboard()` - メイン画面表示

### フロントエンド
- **Template**: `templates/dashboard.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: なし

### 役割
- システムのトップページ
- 各機能へのナビゲーション

---

## 2. 商品一覧画面

### バックエンド
- **View**: `dashboard/products_master/product_list/product_list_views.py`
  - `product_list()` - 商品一覧表示・検索・ページネーション
  - `regenerate_keywords_batch()` - キーワード一括再生成API

### フロントエンド
- **Template**: `templates/products_master/product_list.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: キーワード再生成バッチ処理

### 役割
- 商品の検索・一覧表示
- ページネーション
- 新規作成・編集・削除へのリンク
- 商品キーワード一括再生成機能

---

## 3. AI価格抽出機能

### バックエンド
- **View**: `dashboard/products_master/ai_price_extract/ai_price_extract_views.py`
  - `ai_extract()` - AI価格抽出入力画面
  - `ai_extract_process()` - JSON処理・商品照合・履歴保存
  - `ai_extract_rematch()` - 再照合API
- **View**: `dashboard/products_master/ai_price_extract/ai_history_views.py`
  - `ai_extract_history()` - AI抽出履歴一覧
  - `ai_extract_history_detail()` - 履歴詳細・申請画面
  - `ai_extract_history_delete()` - 履歴論理削除
- **Services**: `dashboard/products_master/ai_services.py`
  - `find_similar_products()` - 商品照合ロジック（2-gram + 加点減点方式）
  - `process_extraction_results()` - 抽出結果処理
- **Models**: `dashboard/products_master/ai_extract_models.py`
  - `AIExtractTransaction` - AI抽出トランザクション（論理削除対応）
  - `AIExtractTransactionDetail` - AI抽出明細

### フロントエンド
- **Template**: 
  - `templates/products_master/ai_extract_input.html` - JSON入力画面
  - `templates/products_master/ai_extract_results.html` - 照合結果・申請画面（履歴詳細と共用）
  - `templates/products_master/ai_extract_history.html` - 履歴一覧画面
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: 編集・再照合・申請処理

### 役割
- AI抽出JSONデータの入力・処理
- 商品マスタとの自動照合（改良された2-gramアルゴリズム）
- 照合結果の編集・再照合
- 価格履歴申請データの作成
- 抽出履歴の管理・論理削除
- 3カ月経過後の自動物理削除

---

## 4. 商品詳細・編集画面

### バックエンド
- **View**: `dashboard/products_master/product_detail/product_detail_views.py`
  - `product_detail()` - 商品詳細表示
  - `product_detail_new()` - 新規商品作成
  - `product_copy()` - 商品コピー
  - `submit_approval()` - 申請処理

### フロントエンド
- **Template**: `templates/products_master/product_detail.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: 
  - `static/js/components/product-basic-info-component.js` - 商品基本情報Webコンポーネント
  - `static/js/components/price-history-component.js` - 価格履歴テーブルWebコンポーネント

### 役割
- 商品基本情報の表示・編集
- 価格履歴の管理（追加・編集・削除）
- インライン編集機能
- 県連価格の自動計算
- 商品コピー機能（全基本情報を継承して新規作成）
- 申請処理

---

## 5. 商品削除機能

### バックエンド
- **View**: `dashboard/products_master/product_delete/product_delete_views.py`
  - `product_delete()` - 商品削除申請

### フロントエンド
- **Template**: `templates/products_master/product_delete.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: なし

### 役割
- 商品の削除申請処理

---

## 6. 申請一覧画面

### バックエンド
- **View**: `dashboard/products_master/product_detail/product_detail_views.py`
  - `approval_list()` - 申請一覧表示
  - `bulk_approve()` - 一括承認

### フロントエンド
- **Template**: `templates/products_master/approval_list.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: なし

### 役割
- 申請中の商品一覧表示
- 申請の検索・フィルタリング
- 一括承認機能

---

## 7. 申請詳細画面

### バックエンド
- **View**: `dashboard/products_master/product_detail/product_detail_views.py`
  - `approval_detail()` - 申請詳細表示
  - `approve_application()` - 申請承認
  - `reject_application()` - 申請却下

### フロントエンド
- **Template**: `templates/products_master/approval_detail.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: 
  - `static/js/components/product-basic-info-component.js` - 商品基本情報Webコンポーネント（読み取り専用モード）
  - `static/js/components/price-history-component.js` - 価格履歴テーブルWebコンポーネント（承認モード）

### 役割
- 申請内容の詳細表示
- 元データとの差分表示
- 申請の承認・却下処理

---

## 8. デジタル価格表画面

### バックエンド
- **View**: `dashboard/products_master/integrated_pricelist/integrated_pricelist_views.py`
  - `integrated_pricelist()` - 指定月時点での価格表表示

### フロントエンド
- **Template**: `templates/products_master/integrated_pricelist.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: なし

### 役割
- 指定月時点での商品価格表示
- 最新価格履歴の自動選択
- ページネーション対応

---

## 共通リソース（依存関係）

### 全画面共通
- **Base Template**: `templates/base.html` - 全画面で継承
- **Common CSS**: `static/css/common.css` - 全画面で使用
- **Bootstrap**: 5.1.3（CDN） - 全画面で使用
- **Breadcrumb**: `templates/components/breadcrumb.html` - 全画面で使用
- **Page Header**: `templates/components/page_header.html` - 全画面で使用
- **Utils**: `digital_pricelist_system/utils.py` - 全ビューで使用
- **Breadcrumbs**: `digital_pricelist_system/breadcrumbs.py` - パンくずリスト生成（全ビューで使用）

### 商品関連画面共通（2,3,4,5,6,7,8番）
- **Models**: `dashboard/products_master/models.py`
  - `Product` - 商品マスタ（全商品関連画面）+ 2-gramキーワード検索対応
  - `PriceHistory` - 価格履歴（4,6,7,8番画面）
  - `ProductApproval` - 商品申請（5,6,7番画面）
  - `PriceHistoryApproval` - 価格履歴申請（6,7番画面）
  - `ProductGrossMarginRate` - 粗利率マスタ（4,6,7番画面）
- **Services**: `dashboard/products_master/product_services.py`
  - `update_product_keywords()` - 商品キーワード更新
  - `regenerate_all_product_keywords()` - 全商品キーワード一括再生成
- **URLs**: `dashboard/products_master/urls.py` - 全商品関連画面

### 特定画面グループ共通
- **ProductForm**: `dashboard/products_master/forms.py`
  - 使用画面：4,5番（商品詳細・削除）
- **Template Filters**: `dashboard/products_master/templatetags/price_filters.py`
  - 使用画面：7番（申請詳細）
- **Webコンポーネント**: `static/js/components/`
  - `product-basic-info-component.js` - 4,7番画面
  - `price-history-component.js` - 4,7番画面


---

## Webコンポーネント詳細

### product-basic-info-component
- **ファイル**: `static/js/components/product-basic-info-component.js`
- **機能**: 商品基本情報の表示・編集
- **モード**: 
  - `edit` - 編集可能モード（コピー時の初期値設定対応）
  - `approval` - 読み取り専用モード（差分表示）

### price-history-component
- **ファイル**: `static/js/components/price-history-component.js`
- **機能**: 価格履歴テーブルの表示・編集
- **モード**:
  - `edit` - 編集可能モード（インライン編集、行追加・削除）
  - `approval` - 読み取り専用モード（差分表示、削除申請表示）

---

## AI商品照合アルゴリズム

### 2-gram + 加点減点方式
```
最終スコア = 基本加点(80) - 余剰減点(20) + 品名ボーナス(15) + 型式ボーナス(15)
```

#### 基本加点
- AI抽出キーワード → マスタキーワードの一致率 × 80点
- AI側を基準とした包含関係を評価

#### 余剰減点
- マスタの余剰キーワード率 × 20点
- 長すぎるマスタデータのスコアを適切に下げる

#### フィールド別ボーナス
- 品名フィールド一致率50%以上: +15点
- 型式フィールド一致率50%以上: +15点

#### 効果
- AI抽出が短い場合でも適切な長さのマスタが選ばれる
- 「牛用」→「牛用飼料」が「牛用配合飼料専用添加物」より高スコア
- フィールド別評価で精密なマッチング

---

## 技術スタック

### バックエンド
- **Django**: 5.2.7
- **Python**: 3.11+
- **Database**: SQLite（開発）

### フロントエンド
- **Bootstrap**: 5.1.3（CDN）
- **Web Components**: ES6 Custom Elements

### 開発ツール
- **IDE**: VS Code推奨
- **Version Control**: Git