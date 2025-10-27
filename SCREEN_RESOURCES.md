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

### フロントエンド
- **Template**: `templates/products_master/product_list.html`
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: なし（標準的なHTMLフォーム）

### 役割
- 商品の検索・一覧表示
- ページネーション
- 新規作成・編集・削除へのリンク

---

## 3. AI価格読取画面

### バックエンド
- **View**: `dashboard/products_master/ai_price_extract/ai_price_extract_views.py`
  - `ai_extract()` - AI価格抽出画面表示
  - `ai_extract_process()` - 画像アップロード・AI処理
  - `ai_extract_results()` - 抽出結果表示・商品登録

### フロントエンド
- **Template**: 
  - `templates/products_master/ai_extract.html` - アップロード画面
  - `templates/products_master/ai_extract_results.html` - 結果画面
- **CSS**: Bootstrap 5.1.3（CDN）
- **JavaScript**: ファイルアップロード処理

### 役割
- 価格表画像のアップロード
- AI による価格情報の自動抽出
- 抽出結果の確認・編集
- 商品マスタへの一括登録

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
  - `Product` - 商品マスタ（全商品関連画面）
  - `PriceHistory` - 価格履歴（4,6,7,8番画面）
  - `ProductApproval` - 商品申請（5,6,7番画面）
  - `PriceHistoryApproval` - 価格履歴申請（6,7番画面）
  - `ProductGrossMarginRate` - 粗利率マスタ（4,6,7番画面）
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

## 技術スタック

### バックエンド
- **Django**: 4.2.7
- **Python**: 3.x
- **Database**: SQLite（開発）

### フロントエンド
- **Bootstrap**: 5.1.3（CDN）
- **Web Components**: ES6 Custom Elements

### 開発ツール
- **IDE**: VS Code推奨
- **Version Control**: Git