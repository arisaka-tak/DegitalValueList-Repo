# 開発ガイドライン

## Web Components + サーバーサイド中心開発思想

このプロジェクトは **サーバーサイド中心 + Web Components** の思想に基づいて開発します。

### 基本原則

1. **サーバーサイド中心**: ビジネスロジックはサーバーサイド（Django）で処理
2. **Web Components**: 再利用可能なUI部品として実装
3. **最小限のJavaScript**: 必要最小限の動的機能のみ
4. **申請・承認ワークフロー**: データ更新は申請・承認で管理

## フロントエンド規約

### Web Components実装

```javascript
// ✅ 良い例: Web Componentsで再利用可能なUI部品
class ProductBasicInfoComponent extends HTMLElement {
    connectedCallback() {
        this.render();
    }
    
    render() {
        const productData = JSON.parse(this.getAttribute('product-data') || '{}');
        // テンプレートレンダリング
    }
}

customElements.define('product-basic-info-component', ProductBasicInfoComponent);
```

```html
<!-- ✅ 良い例: Web Componentsの使用 -->
<product-basic-info-component 
    product-data='{{ product_json }}'
    form-data='{{ form_data_json }}'>
</product-basic-info-component>

<!-- ❌ 悪い例: 複雑なJavaScript処理 -->
<div id="complex-form" onload="initComplexForm()"></div>
```

### JavaScript使用ルール

- **使用OK**: Web Components内のDOM操作、イベントハンドリング
- **使用NG**: 直接のAPI通信、グローバル状態管理

```javascript
// ✅ 良い例: Web Components内のシンプルな処理
renderField(fieldName, productData, formData) {
    const value = productData[fieldName] || '';
    const formValue = formData[fieldName] !== undefined ? formData[fieldName] : value;
    return `<input type="text" value="${this.escapeHtml(formValue)}">`;
}

// ❌ 悪い例: 複雑な状態管理
class GlobalStateManager {
    async saveAllData() {
        // 複雑な処理...
    }
}
```

## バックエンド規約

### 申請・承認ワークフロー

```python
def product_detail(request, pk):
    """商品詳細画面（閲覧モード）"""
    product = get_object_or_404(Product, pk=pk)
    # 表示のみ、編集は申請で実施
    return render(request, 'product_detail.html', context)

def submit_approval(request, pk=None):
    """申請テーブルにデータをコピー"""
    # 1. バリデーション
    # 2. 申請テーブルにコピー
    # 3. 元テーブルのステータスを「申請中」に更新
    pass

def approve_application(request, pk):
    """申請を承認して本テーブルに反映"""
    # 1. 申請テーブルからデータ取得
    # 2. 本テーブルに反映
    # 3. 申請テーブルから削除
    pass
```

### データ送信規約

#### フォームフィールド命名規則

```html
<!-- 新規価格履歴 -->
<input name="new_effective_year_month_0" value="2025/10">
<input name="new_wholesale_price_0" value="1000">
<input name="new_kenren_price_0" value="1100">

<!-- 既存価格履歴更新 -->
<input name="edit_wholesale_price_123" value="1200">  <!-- 123は履歴ID -->
<input name="edit_kenren_price_123" value="1320">

<!-- 削除フラグ -->
<input type="hidden" name="delete_123" value="true">
```

#### 申請テーブル処理

```python
def submit_approval(request, pk=None):
    # 新規履歴を申請テーブルに追加
    for key, value in request.POST.items():
        if key.startswith('new_effective_year_month_') and value.strip():
            index = key.split('_')[-1]
            # PriceHistoryApprovalに保存
    
    # 既存履歴の更新内容を申請テーブルにコピー
    for history in product.price_histories.filter(is_active=True):
        wholesale_price = request.POST.get(f'edit_wholesale_price_{history.pk}', '')
        # 更新内容をPriceHistoryApprovalに保存
    
    # 削除申請処理
    for key, value in request.POST.items():
        if key.startswith('delete_') and value == 'true':
            # is_delete_request=Trueで保存
```

## ファイル構成規約

### テンプレート構成

```
templates/
├── base.html                    # ベーステンプレート
├── components/                  # 共通コンポーネント
│   ├── breadcrumb.html
│   ├── page_header.html
│   └── bottom_action_bar.html
└── products_master/
    ├── product_list.html        # 商品一覧
    ├── product_detail.html      # 商品詳細
    ├── integrated_pricelist.html # デジタル価格表
    └── partials/               # 部分テンプレート
        └── price_history_table.html
```

### Web Components構成

```
static/js/components/
├── product-basic-info-component.js
└── price-history-component.js
```

### ビュー構成

```
products_master/
├── product_list/
│   └── product_list_views.py
├── product_detail/
│   └── product_detail_views.py
└── integrated_pricelist/
    └── integrated_pricelist_views.py
```

## 実装パターン

### 1. Web Componentsパターン

```html
<!-- 商品基本情報コンポーネント -->
<product-basic-info-component 
    product-data='{{ product_json }}'
    form-data='{{ form_data_json }}'
    editable="true"
    is-new="{{ is_new|yesno:'true,false' }}">
</product-basic-info-component>

<!-- 価格履歴コンポーネント -->
<price-history-component 
    histories='{{ price_histories_json }}'>
</price-history-component>
```

### 2. 申請フォームパターン

```html
<!-- 一括申請フォーム -->
<form id="productForm" method="post">
    {% csrf_token %}
    <!-- Web Componentsがフォームフィールドを生成 -->
</form>

<!-- 申請ボタン -->
<button type="submit" 
        form="productForm"
        formaction="{% url 'submit_approval' %}"
        onclick="return submitApplication(this)">
    申請
</button>
```

### 3. 承認フローパターン

```html
<!-- 承認ボタン -->
<button onclick="acceptApplication()" 
        class="btn btn-success">
    承認
</button>

<button onclick="rejectApplication()" 
        class="btn btn-danger">
    却下
</button>
```

## 禁止事項

### ❌ やってはいけないこと

1. **直接データ更新**: 申請・承認を経ずに本テーブルを更新
2. **複雑なJavaScript**: Web Components外での複雑な処理
3. **グローバル状態**: JavaScriptでのグローバル状態管理
4. **余計な修正**: 目的外のコード変更でバグを混入

### ✅ 推奨すること

1. **申請・承認フロー**: 全てのデータ更新はワークフローで管理
2. **Web Components**: 再利用可能なUI部品として実装
3. **サーバーサイド処理**: ビジネスロジックはDjangoで実装
4. **最小限の修正**: 目的に必要な最小限のコード変更

## レビューチェックリスト

新機能実装時は以下をチェック：

- [ ] 申請・承認フローを経ているか？
- [ ] Web Componentsで再利用可能に実装されているか？
- [ ] ビジネスロジックがサーバーサイドにあるか？
- [ ] 命名規則に従っているか？
- [ ] 余計なコード変更がないか？

## 参考資料

- [Web Components MDN](https://developer.mozilla.org/ja/docs/Web/Web_Components)
- [Django 公式ドキュメント](https://docs.djangoproject.com/)
- [Bootstrap 5.1.3](https://getbootstrap.com/docs/5.1/)