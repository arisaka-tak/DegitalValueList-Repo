# 運用保守ガイド - コード理解の手引き

このドキュメントは、システムの運用保守や修正を行う際に、どのコードを読むべきかを示すガイドです。

## 📚 最初に読むべきドキュメント

### 1. 必読ドキュメント（優先度：高）
```
README.md                              # プロジェクト全体概要
pj_doc/SYSTEM_ARCHITECTURE.md          # システムアーキテクチャ
pj_doc/DEVELOPMENT_GUIDELINES.md       # 開発思想・実装パターン
pj_doc/TECHNICAL_CONVENTIONS.md        # コーディング規約
```

### 2. 機能別ドキュメント（優先度：中）
```
pj_doc/USER_MANUAL.md                  # ユーザーマニュアル
pj_doc/SCREEN_BUTTONS_FUNCTIONS.md     # 画面・ボタン機能一覧
pj_doc/MASTER_DATA_GUIDELINES.md       # マスタデータ管理
pj_doc/DEPLOYMENT_GUIDE.md             # デプロイ手順
```

---

## 🗂️ コード構成の全体像

```
ZCS_DegitalValueList/
├── digital_pricelist_system/    # プロジェクト設定（Django設定）
├── dashboard/products_master/   # メインアプリ（商品マスタ管理）
├── templates/                   # HTMLテンプレート
├── static/                      # CSS/JavaScript
└── system_admin/                # システム管理機能
```

---

## 🎯 修正内容別：読むべきコード

### ケース1: 商品一覧の表示・検索を修正したい

#### 読む順番
1. **ビュー（ロジック）**
   ```
   dashboard/products_master/product_list/product_list_views.py
   ```
   - `product_list()`: 一覧表示のメイン処理
   - `product_search()`: 検索処理
   - 検索条件、ページネーション、並び順の制御

2. **テンプレート（表示）**
   ```
   templates/products_master/product_list.html
   ```
   - 一覧表示のHTML構造
   - 検索フォーム
   - ページネーション

3. **モデル（データ構造）**
   ```
   dashboard/products_master/models.py
   ```
   - `Product`: 商品マスタのデータ構造
   - `PriceHistory`: 価格履歴のデータ構造

4. **URL設定**
   ```
   dashboard/products_master/urls.py
   ```
   - URLパターンの確認

---

### ケース2: 商品詳細・編集画面を修正したい

#### 読む順番
1. **ビュー（ロジック）**
   ```
   dashboard/products_master/product_detail/product_detail_views.py
   ```
   - `product_detail()`: 詳細表示
   - `product_edit()`: 編集処理
   - `product_create()`: 新規作成
   - `product_copy()`: コピー機能

2. **テンプレート（表示）**
   ```
   templates/products_master/product_detail.html
   templates/components/price_history_section.html
   ```
   - 詳細画面のHTML構造
   - 価格履歴セクション

3. **Web Components（動的機能）**
   ```
   static/js/components/product-detail-form.js
   static/js/components/price-history-editor.js
   ```
   - 価格履歴の動的追加・削除
   - 県連価格の自動計算
   - 粗利率の自動計算

4. **ユーティリティ**
   ```
   digital_pricelist_system/gross_margin_utils.py
   static/js/gross-margin-utils.js
   ```
   - 粗利率計算ロジック（Python/JavaScript両方）

---

### ケース3: 承認ワークフローを修正したい

#### 読む順番
1. **ビュー（ロジック）**
   ```
   dashboard/products_master/product_detail/product_detail_views.py
   ```
   - `submit_for_approval()`: 申請処理
   - `approval_list()`: 承認一覧
   - `approval_detail()`: 承認詳細
   - `approve_product()`: 承認処理
   - `reject_product()`: 却下処理

2. **モデル（データ構造）**
   ```
   dashboard/products_master/models.py
   ```
   - `ProductApproval`: 商品承認テーブル
   - `PriceHistoryApproval`: 価格履歴承認テーブル

3. **テンプレート（表示）**
   ```
   templates/products_master/approval_list.html
   templates/products_master/approval_detail.html
   ```
   - 承認一覧画面
   - 承認詳細・差分表示

4. **サービス（共通処理）**
   ```
   dashboard/products_master/product_services.py
   ```
   - `create_approval_from_product()`: 承認データ作成
   - `apply_approval_to_product()`: 承認内容の反映

---

### ケース4: デジタル価格表を修正したい

#### 読む順番
1. **ビュー（ロジック）**
   ```
   dashboard/products_master/integrated_pricelist/integrated_pricelist_views.py
   ```
   - `integrated_pricelist()`: 価格表表示
   - `export_pricelist_excel()`: Excel出力

2. **テンプレート（表示）**
   ```
   templates/products_master/integrated_pricelist.html
   ```
   - 価格表のHTML構造
   - 月選択フォーム

3. **CSS（スタイル）**
   ```
   static/css/price_table.css
   ```
   - 価格表のスタイル定義

---

### ケース5: AI価格抽出機能を修正したい

#### 読む順番
1. **ビュー（ロジック）**
   ```
   dashboard/products_master/ai_price_extract/ai_price_extract_views.py
   dashboard/products_master/ai_price_extract/ai_history_views.py
   ```
   - `ai_extract_input()`: JSON入力画面
   - `ai_extract_process()`: 抽出処理
   - `ai_extract_results()`: 結果表示
   - `ai_extract_history()`: 履歴一覧

2. **サービス（AI処理）**
   ```
   dashboard/products_master/ai_services.py
   ```
   - `process_ai_extraction()`: AI抽出メイン処理
   - `match_products()`: 商品マッチング
   - `calculate_match_score()`: スコア計算

3. **モデル（データ構造）**
   ```
   dashboard/products_master/ai_extract_models.py
   ```
   - `AIExtractTransaction`: AI抽出トランザクション
   - `AIExtractDetail`: AI抽出明細

4. **PDF処理（将来実装）**
   ```
   dashboard/products_master/pdf_processing/
   dashboard/products_master/document_intelligence_service.py
   ```
   - PDF解析処理
   - Azure Document Intelligence連携

---

### ケース6: マスタデータ管理を修正したい

#### 読む順番
1. **ビュー（ロジック）**
   ```
   dashboard/products_master/master_views.py
   ```
   - メーカー・カテゴリ・畜種マスタのCRUD処理

2. **モデル（データ構造）**
   ```
   dashboard/products_master/models.py
   ```
   - `Manufacturer`: メーカーマスタ
   - `Category`: カテゴリマスタ
   - `LivestockType`: 畜種マスタ

3. **テンプレート（表示）**
   ```
   templates/products_master/manufacturer_list.html
   templates/products_master/category_list.html
   templates/products_master/livestock_type_list.html
   ```

---

### ケース7: システム設定を修正したい

#### 読む順番
1. **Django設定**
   ```
   digital_pricelist_system/settings.py
   ```
   - データベース設定
   - アプリケーション設定
   - 静的ファイル設定
   - メディアファイル設定

2. **URL設定**
   ```
   digital_pricelist_system/urls.py
   dashboard/products_master/urls.py
   ```
   - URLルーティング

3. **起動スクリプト**
   ```
   Django_run.py
   ```
   - サーバー起動処理
   - 設定ファイル読み込み

4. **設定ファイル**
   ```
   config.ini (ネットワークドライブ上)
   digital_pricelist_system/config_paths.py
   ```
   - 外部設定ファイルのパス管理

---

## 🔧 よくある修正パターン

### パターン1: 画面に新しい項目を追加したい

1. **モデルにフィールド追加**
   ```python
   # dashboard/products_master/models.py
   class Product(models.Model):
       new_field = models.CharField(max_length=100)  # 追加
   ```

2. **マイグレーション実行**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **フォームに追加**
   ```python
   # dashboard/products_master/forms.py
   class ProductForm(forms.ModelForm):
       class Meta:
           fields = ['product_name', 'new_field']  # 追加
   ```

4. **テンプレートに追加**
   ```html
   <!-- templates/products_master/product_detail.html -->
   <input type="text" name="new_field" value="{{ product.new_field }}">
   ```

---

### パターン2: 検索条件を追加したい

1. **ビューに検索ロジック追加**
   ```python
   # dashboard/products_master/product_list/product_list_views.py
   def product_search(request):
       new_condition = request.GET.get('new_condition', '')
       if new_condition:
           products = products.filter(new_field__icontains=new_condition)
   ```

2. **テンプレートに検索フォーム追加**
   ```html
   <!-- templates/products_master/product_list.html -->
   <input type="text" name="new_condition" placeholder="新しい条件">
   ```

---

### パターン3: 計算ロジックを変更したい

1. **Python側の計算ロジック**
   ```python
   # digital_pricelist_system/gross_margin_utils.py
   def calculate_gross_margin(wholesale_price, kenren_price):
       # 計算ロジックを修正
   ```

2. **JavaScript側の計算ロジック**
   ```javascript
   // static/js/gross-margin-utils.js
   function calculateGrossMargin(wholesalePrice, kenrenPrice) {
       // 計算ロジックを修正
   }
   ```

---

## 🐛 トラブルシューティング

### エラーが発生した場合の調査順序

1. **ログファイル確認**
   ```
   logs/system_YYYYMMDD_HHMMSS.log
   ```

2. **ブラウザのコンソール確認**
   - F12キー → Consoleタブ
   - JavaScriptエラーの確認

3. **データベース確認**
   ```bash
   python manage.py dbshell
   ```

4. **Django管理画面で確認**
   ```
   http://127.0.0.1:8000/admin/
   ```

---

## 📝 コーディング規約

### Python（Django）
- **命名規則**: スネークケース（`product_list`, `calculate_price`）
- **インデント**: スペース4つ
- **docstring**: 関数の先頭にコメント記載

### JavaScript
- **命名規則**: キャメルケース（`productList`, `calculatePrice`）
- **インデント**: スペース2つ
- **コメント**: 処理の意図を明確に

### HTML/CSS
- **インデント**: スペース2つ
- **クラス名**: ケバブケース（`product-list`, `price-history`）

---

## 🚀 開発環境セットアップ

```bash
# 1. 仮想環境作成
python -m venv venv
venv\Scripts\activate

# 2. 依存関係インストール
pip install -r requirements.txt

# 3. データベース初期化
python manage.py makemigrations
python manage.py migrate

# 4. サーバー起動
python Django_run.py
```

---

## 📞 サポート

- **開発ガイドライン**: `pj_doc/DEVELOPMENT_GUIDELINES.md`
- **技術規約**: `pj_doc/TECHNICAL_CONVENTIONS.md`
- **システムアーキテクチャ**: `pj_doc/SYSTEM_ARCHITECTURE.md`

---

## 🔄 更新履歴

- 2026-02-02: 初版作成
