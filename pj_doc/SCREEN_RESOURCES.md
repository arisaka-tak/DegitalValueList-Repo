# 画面別リソース構成

## システム概要

### アーキテクチャ
- **バックエンド**: Django 5.2.7
- **フロントエンド**: Bootstrap 5.1.3 + Web Components
- **データベース**: SQLite
- **設定管理**: サーバー共有config.ini
- **バージョン管理**: VersionChecker.exe + DigitalValueList.exe

### 配置構成
- **サーバー**: `\\128.167.100.10\資材・大家畜事業部\04資材部\★デジタル価格表作成プログラム\`
- **ローカル**: `C:\ZBS\DVL\`
- **起動方法**: VersionChecker.exe → 自動更新 → DigitalValueList.exe起動

---

## 1. ダッシュボード画面

### バックエンド
- **View**: `dashboard/dashboard_views.py`
  - `dashboard()` - メイン画面表示
  - `sidebar()` - サイドバー表示（管理者権限チェック）

### フロントエンド
- **Template**: `templates/dashboard.html`
- **Base**: `templates/base.html`（サイドナビゲーション含む）
- **CSS**: `static/css/common.css`
- **JavaScript**: なし

### 役割
- システムのトップページ
- 機能別カード表示
- 管理者限定メニューの表示制御（ホスト名BC102131チェック）

---

## 2. 商品一覧画面

### バックエンド
- **View**: `dashboard/products_master/product_list/product_list_views.py`
  - `product_list()` - 商品一覧表示・検索・ページネーション・並び順管理
  - `update_sort_order()` - 並び順更新API
  - `reset_sort_order()` - 並び順リセットAPI
  - `cross_page_move()` - ページ間移動API

### フロントエンド
- **Template**: `templates/products_master/product_list.html`
- **CSS**: テーブルヘッダー固定、ドラッグ&ドロップ対応
- **JavaScript**: 
  - 並び順変更（ドラッグ&ドロップ、上下ボタン）
  - ページ間商品移動
  - グループ境界線表示

### 役割
- 商品の検索・一覧表示・並び順管理
- ページネーション（200件/ページ）
- 畜種・分類・メーカー別グループ表示
- 新規作成・編集・削除へのリンク

---

## 3. AI価格抽出機能

### バックエンド
- **View**: `dashboard/products_master/ai_price_extract/ai_price_extract_views.py`
  - `ai_extract()` - AI価格抽出入力画面
  - `ai_extract_process()` - JSON処理・商品照合・履歴保存
  - `ai_extract_rematch()` - 再照合API
  - `ai_extract_history()` - AI抽出履歴一覧
  - `ai_extract_history_detail()` - 履歴詳細・申請画面
  - `ai_extract_history_delete()` - 履歴論理削除
- **Services**: `dashboard/products_master/ai_services.py`
  - `find_similar_products()` - 商品照合ロジック（2-gram + 加点減点方式）
  - `process_extraction_results()` - 抽出結果処理
- **Models**: `dashboard/products_master/ai_extract_models.py`
  - `AIExtractTransaction` - AI抽出トランザクション（論理削除対応）
  - `AIExtractTransactionDetail` - AI抽出明細
- **PDF処理**: `dashboard/products_master/pdf_processing/extract_di_only.py`
  - Azure Document Intelligence連携

### フロントエンド
- **Template**: 
  - `templates/products_master/ai_extract_input.html` - JSON入力画面
  - `templates/products_master/ai_extract_results.html` - 照合結果・申請画面
  - `templates/products_master/ai_extract_history.html` - 履歴一覧画面
- **CSS**: Bootstrap 5.1.3
- **JavaScript**: 編集・再照合・申請処理

### 役割
- AI抽出JSONデータの入力・処理
- 商品マスタとの自動照合（改良された2-gramアルゴリズム）
- 照合結果の編集・再照合
- 価格履歴申請データの作成
- 抽出履歴の管理・論理削除

---

## 4. 商品詳細・編集画面

### バックエンド
- **View**: `dashboard/products_master/product_detail/product_detail_views.py`
  - `product_detail()` - 商品詳細表示
  - `product_detail_new()` - 新規商品作成
  - `product_copy()` - 商品コピー
  - `submit_approval()` - 申請処理
  - `bulk_approve()` - 一括承認（Djangoメッセージ使用）
  - `approve_application()` - 個別承認
  - `reject_application()` - 申請却下
  - `cancel_application()` - 申請取消

### フロントエンド
- **Template**: `templates/products_master/product_detail.html`
- **Components**: 
  - `templates/components/price_history_section.html`
  - `templates/components/gross_margin_modal.html`
  - `templates/components/manufacturer_modal.html`
- **CSS**: Bootstrap 5.1.3
- **JavaScript**: 
  - 価格履歴動的追加・削除
  - 粗利率自動計算
  - 県連価格計算
  - メーカー管理モーダル

### 役割
- 商品基本情報の表示・編集
- 価格履歴の管理（追加・編集・削除）
- 県連価格の自動計算
- 商品コピー機能
- 申請・承認処理

---

## 5. 承認ワークフロー画面

### バックエンド
- **View**: `dashboard/products_master/product_detail/product_detail_views.py`
  - `approval_list()` - 申請一覧表示
  - `approval_detail()` - 申請詳細表示

### フロントエンド
- **Template**: 
  - `templates/products_master/approval_list.html`
  - `templates/products_master/approval_detail.html`
- **CSS**: 差分表示スタイル
- **JavaScript**: 一括選択・承認処理

### 役割
- 申請中の商品・価格履歴一覧表示
- 申請内容の詳細表示・差分表示
- 一括承認・個別承認・却下機能

---

## 6. デジタル価格表画面

### バックエンド
- **View**: `dashboard/products_master/integrated_pricelist/integrated_pricelist_views.py`
  - `integrated_pricelist()` - 指定月時点での価格表表示
  - `export_excel()` - Excel出力（UTF-8ファイル名対応）
  - `update_sort_order()` - 並び順更新
  - `reset_sort_order()` - 並び順リセット
  - `cross_page_move()` - ページ間移動

### フロントエンド
- **Template**: `templates/products_master/integrated_pricelist.html`
- **CSS**: 
  - ヘッダー固定スクロールテーブル
  - ドラッグ&ドロップ対応
  - グループ境界線表示
- **JavaScript**: 
  - 並び順変更（ドラッグ&ドロップ、ボタン操作）
  - ページ間商品移動
  - Excel出力

### 役割
- 指定月時点での商品価格表示（200件/ページ）
- 最新価格履歴の自動選択
- 並び順管理・Excel出力
- ファイル名形式：`{yyyymm}デジタル価格表_{確定版|未承認版}.xlsx`

---

## 7. マスタ管理画面

### バックエンド
- **View**: `dashboard/products_master/master_views.py`
  - 畜種マスタ（`livestock_type_*`）
  - 分類マスタ（`category_*`）
  - メーカーマスタ（`manufacturer_*`）

### フロントエンド
- **Template**: 
  - `templates/products_master/livestock_type_*.html`
  - `templates/products_master/category_*.html`
  - `templates/products_master/manufacturer_*.html`
- **CSS**: Bootstrap 5.1.3
- **JavaScript**: なし

### 役割
- 各種マスタデータの管理
- CRUD操作
- 表示順管理

---

## 8. 決裁書管理画面

### バックエンド
- **View**: `dashboard/products_master/product_detail/product_detail_views.py`
  - `upload_approval_pdf()` - 決裁書PDFアップロード

### フロントエンド
- **Template**: `templates/products_master/upload_approval_pdf.html`
- **CSS**: Bootstrap 5.1.3
- **JavaScript**: ファイルアップロード処理

### 役割
- 月別決裁書PDFのアップロード・管理
- ファイル形式：YYYY/MM

---

## 9. システム管理画面（管理者限定）

### バックエンド
- **View**: `system_admin/views.py`
  - `export_data()` - データエクスポート
  - `import_data()` - データインポート
  - `status_reset()` - ステータスリセット
  - `regenerate_keywords_batch()` - キーワード一括再生成
  - `clear_data()` - データクリア
- **権限制御**: `digital_pricelist_system/utils.py`
  - `is_admin_user()` - ホスト名BC102131チェック

### フロントエンド
- **Template**: `templates/system_admin/*.html`
- **CSS**: 警告色スタイル
- **JavaScript**: 確認ダイアログ

### 役割
- データの一括管理
- システムメンテナンス
- 管理者限定機能（ホスト名制限）

---

## 10. バージョン管理システム

### バージョンチェッカー
- **ファイル**: `version_checker.py`
- **ビルド**: `pj_doc/build_version_checker.py`
- **機能**: 
  - サーバーバージョンチェック（v{yyyymmddnnn}形式）
  - 自動ダウンロード・更新
  - メインプログラム起動
  - 独立プロセス実行

### メインプログラム
- **ファイル**: `Django_run.py`
- **設定**: サーバー共有`config.ini`読み込み
- **機能**: 
  - Django起動・ブラウザ自動オープン
  - プロセス管理・ポート管理
  - ログ出力

---

## 共通リソース

### 設定管理
- **CONFIG_PATH**: `\\128.167.100.10\...\config.ini`
- **関数**: `digital_pricelist_system/settings.py`
  - `get_database_path()` - DB パス取得
  - `get_media_root()` - メディアパス取得

### 共通コンポーネント
- **Base Template**: `templates/base.html`
- **Components**: `templates/components/*.html`
- **CSS**: `static/css/common.css`, `static/css/price_table.css`
- **Utils**: `digital_pricelist_system/utils.py`
- **Breadcrumbs**: `digital_pricelist_system/breadcrumbs.py`

### データモデル
- **Core Models**: `dashboard/products_master/models.py`
  - `Product`, `PriceHistory`, `ProductApproval`, `PriceHistoryApproval`
  - `LivestockType`, `Category`, `Manufacturer`
  - `ProductGrossMarginRate`, `ApprovalPdf`
- **AI Models**: `dashboard/products_master/ai_extract_models.py`
  - `AIExtractTransaction`, `AIExtractTransactionDetail`

### サービス層
- **Product Services**: `dashboard/products_master/product_services.py`
- **AI Services**: `dashboard/products_master/ai_services.py`
- **Document Intelligence**: `dashboard/products_master/document_intelligence_service.py`

---

## 技術スタック

### バックエンド
- **Django**: 5.2.7
- **Python**: 3.11+
- **Database**: SQLite
- **AI**: Azure Document Intelligence

### フロントエンド
- **Bootstrap**: 5.1.3（CDN）
- **JavaScript**: ES6（Web Components使用なし）
- **CSS**: カスタムスタイル + Bootstrap

### デプロイメント
- **PyInstaller**: onefile/onedir両対応
- **バージョン管理**: 自動更新システム
- **設定管理**: サーバー共有設定ファイル