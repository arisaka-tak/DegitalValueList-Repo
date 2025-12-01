# 画面ナビゲーションツリーとリソース一覧

## 画面構成ツリー

```
🏠 ダッシュボード (/)
├── 📦 商品マスタ管理 (/products/products/)
│   ├── 🔍 AI価格読取 (/products/ai-extract/)
│   │   ├── 📤 AI価格抽出処理 (/products/ai-extract/process/)
│   │   └── 📋 AI抽出結果 (/products/ai-extract/results/)
│   ├── ➕ 新規商品作成 (/products/new/)
│   ├── 📝 商品詳細・編集 (/products/products/{id}/)
│   ├── 📋 商品作成 (/products/products/create/)
│   ├── ✏️ 商品編集 (/products/products/{id}/edit/)
│   ├── 📄 商品コピー (/products/products/{id}/copy/)
│   └── 🗑️ 商品削除 (/products/products/{id}/delete/)
├── 📝 承認ワークフロー (/products/approvals/)
│   ├── 📋 申請詳細 (/products/approvals/{id}/)
│   ├── ✅ 申請承認 (/products/approvals/{id}/approve/)
│   ├── ❌ 申請却下 (/products/approvals/{id}/reject/)
│   └── 📦 一括承認 (/products/approvals/bulk-approve/)
└── 📊 デジタル価格表 (/products/integrated-pricelist/)
```

---

## 各画面のリソース詳細

### 1. 🏠 ダッシュボード
**URL**: `/`
**View**: `dashboard.views.dashboard`
**Template**: `templates/dashboard.html`
**CSS**: `static/css/common.css`
**JavaScript**: なし

**機能**: システムのメインメニュー、各機能へのナビゲーション

---

### 2. 📦 商品マスタ管理（商品一覧）
**URL**: `/products/products/`
**View**: `dashboard.products_master.product_list.views.product_list`
**Template**: `templates/products_master/product_list.html`
**CSS**: `static/css/common.css`
**JavaScript**: なし

**機能**: 商品の検索・一覧表示、ページネーション、各種操作へのリンク

---

### 3. 🔍 AI価格読取
**URL**: `/products/ai-extract/`
**View**: `dashboard.products_master.product_list.views.ai_extract`
**Template**: `templates/products_master/ai_extract_input.html`
**CSS**: `static/css/common.css`
**JavaScript**: ファイルアップロード処理

**機能**: 価格表画像のアップロード、AI処理の開始

#### 3-1. 📤 AI価格抽出処理
**URL**: `/products/ai-extract/process/`
**View**: `dashboard.products_master.product_list.views.ai_extract_process`
**機能**: アップロードされた画像のAI処理

#### 3-2. 📋 AI抽出結果
**URL**: `/products/ai-extract/results/`
**View**: `dashboard.products_master.product_list.views.ai_extract_results`
**Template**: `templates/products_master/ai_extract_results.html`
**CSS**: `static/css/common.css`
**JavaScript**: 結果編集・確認処理

**機能**: AI抽出結果の表示・編集・商品マスタへの一括登録

---

### 4. ➕ 新規商品作成
**URL**: `/products/new/`
**View**: `dashboard.products_master.product_detail.views.product_detail_new`
**Template**: `templates/products_master/product_detail.html`
**CSS**: `static/css/common.css`, `static/css/price_table.css`
**JavaScript**: 
- `static/js/components/product-basic-info-component.js`
- `static/js/components/price-history-component.js`

**機能**: 新規商品の基本情報入力、価格履歴管理、申請処理

---

### 5. 📝 商品詳細・編集
**URL**: `/products/products/{id}/`
**View**: `dashboard.products_master.product_detail.views.product_detail`
**Template**: `templates/products_master/product_detail.html`
**CSS**: `static/css/common.css`, `static/css/price_table.css`
**JavaScript**: 
- `static/js/components/product-basic-info-component.js`
- `static/js/components/price-history-component.js`

**機能**: 商品基本情報の表示・編集、価格履歴の管理、インライン編集、県連価格自動計算、申請処理

**注記**: Webコンポーネント化により、partialsテンプレートは使用されていません

---

### 6. 📋 商品作成
**URL**: `/products/products/create/`
**View**: `dashboard.products_master.product_create.views.product_create`
**機能**: 商品作成処理

---

### 7. ✏️ 商品編集
**URL**: `/products/products/{id}/edit/`
**View**: `dashboard.products_master.product_create.views.product_edit`
**機能**: 商品編集処理

---

### 8. 📄 商品コピー
**URL**: `/products/products/{id}/copy/`
**View**: `dashboard.products_master.product_create.views.product_copy`
**機能**: 商品情報をコピーして新規作成モードで詳細画面へ遷移

---

### 9. 🗑️ 商品削除
**URL**: `/products/products/{id}/delete/`
**View**: `dashboard.products_master.product_create.views.product_delete`
**Template**: `templates/products_master/product_delete.html`
**CSS**: `static/css/common.css`
**JavaScript**: なし

**機能**: 商品削除申請処理

---

### 10. 📝 承認ワークフロー（申請一覧）
**URL**: `/products/approvals/`
**View**: `dashboard.products_master.product_detail.views.approval_list`
**Template**: `templates/products_master/approval_list.html`
**CSS**: `static/css/common.css`
**JavaScript**: なし

**機能**: 申請中の商品一覧表示、検索・フィルタリング、承認・却下・一括承認機能

---

### 11. 📋 申請詳細
**URL**: `/products/approvals/{id}/`
**View**: `dashboard.products_master.product_detail.views.approval_detail`
**Template**: `templates/products_master/approval_detail.html`
**CSS**: `static/css/common.css`, `static/css/price_table.css`
**JavaScript**: 
- `static/js/components/product-basic-info-component.js` (読み取り専用モード)
- `static/js/components/price-history-component.js` (承認モード)

**機能**: 申請内容の詳細表示、元データとの差分表示、承認・却下処理

**注記**: Webコンポーネント化により、partialsテンプレートは使用されていません

---

### 12. ✅ 申請承認
**URL**: `/products/approvals/{id}/approve/`
**View**: `dashboard.products_master.product_detail.views.approve_application`
**機能**: 個別申請の承認処理

---

### 13. ❌ 申請却下
**URL**: `/products/approvals/{id}/reject/`
**View**: `dashboard.products_master.product_detail.views.reject_application`
**機能**: 個別申請の却下処理

---

### 14. 📦 一括承認
**URL**: `/products/approvals/bulk-approve/`
**View**: `dashboard.products_master.product_detail.views.bulk_approve`
**機能**: 全申請の一括承認処理

---

### 15. 📊 デジタル価格表
**URL**: `/products/integrated-pricelist/`
**View**: `dashboard.products_master.integrated_pricelist.views.integrated_pricelist`
**Template**: `templates/products_master/integrated_pricelist.html`
**CSS**: `static/css/common.css`, `static/css/price_table.css`
**JavaScript**: なし

**機能**: 指定月時点での商品価格表示、最新価格履歴の自動選択、ページネーション

---

## 共通リソース

### 全画面共通
- **Base Template**: `templates/base.html`
- **Common CSS**: `static/css/common.css`
- **Bootstrap**: 5.1.3（CDN）
- **Breadcrumb**: `templates/components/breadcrumb.html`
- **Page Header**: `templates/components/page_header.html`
- **Bottom Action Bar**: `templates/components/bottom_action_bar.html`

### バックエンド共通
- **Models**: `dashboard/products_master/models.py`
- **Forms**: `dashboard/products_master/forms.py`
- **Utils**: `digital_pricelist_system/utils.py`
- **Breadcrumbs**: `digital_pricelist_system/breadcrumbs.py`
- **AI Services**: `dashboard/products_master/ai_services.py`
- **Template Tags**: `dashboard/products_master/templatetags/price_filters.py`

### Webコンポーネント
- **product-basic-info-component**: 商品基本情報の表示・編集（編集モード・承認モード対応）
- **price-history-component**: 価格履歴テーブルの表示・編集（編集モード・承認モード対応）

---

## 技術スタック

### バックエンド
- **Django**: 5.2.7
- **Python**: 3.x
- **Database**: SQLite（開発）

### フロントエンド
- **Bootstrap**: 5.1.3（CDN）
- **Web Components**: ES6 Custom Elements
- **HTMX**: なし（標準的なHTMLフォーム使用）

### 開発ツール
- **IDE**: VS Code推奨
- **Version Control**: Git