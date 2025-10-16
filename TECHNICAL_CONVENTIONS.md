# 技術的約束事

## アーキテクチャ概要

### アプリケーション構成
- **モノリシック構成**: 単一Djangoアプリケーション
- **機能別モジュール分割**: products_masterアプリ内で機能別にサブモジュール分割
- **HTMX中心設計**: サーバーサイドレンダリング + 部分更新

### パンくずリスト管理
```python
# digital_pricelist_system/breadcrumbs.py
def get_breadcrumbs(page_type, **kwargs):
    """ページタイプに応じたパンくずリストを返す"""
    breadcrumbs_map = {
        'product_list': [{'title': '商品一覧', 'url': None}],
        'product_detail': [
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': kwargs.get('product_name'), 'url': None}
        ]
    }
    return breadcrumbs_map.get(page_type, [])
```

## データベース設計規約

### モデル設計

```python
class BaseModel(models.Model):
    """全モデルの基底クラス"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # 論理削除用
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """論理削除"""
        self.is_active = False
        self.save()
```

### 承認フロー設計

```python
# 商品マスタテーブル
class Product(models.Model):
    product_number = models.IntegerField(unique=True, null=True, blank=True)  # 自動採番
    status = models.CharField(max_length=20, default='', choices=[('', '申請なし'), ('申請中', '申請中')])
    # その他商品情報フィールド

# 商品承認テーブル
class ProductApproval(models.Model):
    product_number = models.IntegerField()  # 既存商品の場合は正の値、新規の場合は負の値
    # Productと同じフィールド構成
    applicant = models.CharField(max_length=100)  # 申請者

# 価格履歴承認テーブル
class PriceHistoryApproval(models.Model):
    product = models.ForeignKey(ProductApproval, related_name='price_histories')
    is_delete_request = models.BooleanField(default=False)  # 削除申請フラグ
    # PriceHistoryと同じフィールド構成

# 承認処理の共通ロジック
def _process_approval(approval):
    """承認処理: 申請内容をマスタテーブルに反映"""
    if approval.product_number > 0:
        # 既存商品の更新
        product = Product.objects.get(product_number=approval.product_number)
        # 申請内容で更新
    else:
        # 新規商品の作成
        product = Product.objects.create(...)
```

## URL設計規約

### 実際のURL構成

```python
# products_master/urls.py
urlpatterns = [
    # 基本機能
    path('', list_views.product_list, name='product_list'),  # 商品一覧
    path('products/', list_views.product_list, name='product_list'),
    path('products/<int:pk>/', detail_views.product_detail, name='product_detail'),
    path('new/', detail_views.product_detail_new, name='product_new'),
    path('products/<int:pk>/delete/', create_views.product_delete, name='product_delete'),
    
    # 申請機能
    path('products/<int:pk>/submit-approval/', detail_views.submit_approval, name='submit_approval'),
    path('new/submit-approval/', detail_views.submit_approval, name='submit_approval_new'),
    
    # 承認機能
    path('approvals/', detail_views.approval_list, name='approval_list'),
    path('approvals/<int:pk>/', detail_views.approval_detail, name='approval_detail'),
    path('approvals/<int:pk>/approve/', detail_views.approve_application, name='approve_application'),
    
    # HTMX API
    path('products/<int:pk>/add-row/', detail_views.add_price_row, name='add_price_row'),
    path('calc-kenren-price/<int:pk>/', detail_views.calc_kenren_price, name='calc_kenren_price'),
    
    # デジタル価格表
    path('integrated-pricelist/', pricelist_views.integrated_pricelist, name='integrated_pricelist'),
]
```

## フォーム設計規約

### 自動採番フィールド

```python
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['product_number']  # 自動採番フィールドは除外
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.product_number:
            instance.product_number = self.generate_product_number()
        if commit:
            instance.save()
        return instance
```

## エラーハンドリング規約

### HTMX用エラーレスポンス

```python
def htmx_error_response(message, status=400):
    """HTMX用エラーレスポンス"""
    return HttpResponse(
        f'<div class="alert alert-danger">{message}</div>',
        status=status
    )

def htmx_success_response(message=""):
    """HTMX用成功レスポンス"""
    if message:
        return HttpResponse(f'<div class="alert alert-success">{message}</div>')
    return HttpResponse('<script>location.reload();</script>')
```

## テンプレート規約

### 共通コンポーネント

```html
<!-- components/breadcrumb.html -->
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        {% for crumb in breadcrumbs %}
            <li class="breadcrumb-item">
                {% if crumb.url %}<a href="{{ crumb.url }}">{% endif %}
                {{ crumb.title }}
                {% if crumb.url %}</a>{% endif %}
            </li>
        {% endfor %}
    </ol>
</nav>

<!-- components/page_header.html -->
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1>{{ page_title }}</h1>
        {% if page_subtitle %}<p class="text-muted">{{ page_subtitle }}</p>{% endif %}
    </div>
</div>
```

### HTMX属性の標準化

```html
<!-- 一覧更新 -->
<button hx-get="/search/" 
        hx-target="#results" 
        hx-indicator="#loading">
    検索
</button>

<!-- フォーム送信 -->
<button hx-post="/save/" 
        hx-include="#form1, #form2" 
        hx-target="body">
    保存
</button>

<!-- 部分更新 -->
<button hx-get="/add-row/" 
        hx-target="#container" 
        hx-swap="innerHTML">
    追加
</button>
```

## セキュリティ規約

### CSRF保護

```html
<!-- 全てのフォームにCSRFトークン -->
<form>
    {% csrf_token %}
    <!-- フォーム内容 -->
</form>

<!-- HTMX用 -->
<div hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <!-- HTMX要素 -->
</div>
```

### 権限チェック

```python
@login_required
def protected_view(request):
    # ログイン必須ビュー
    pass

def check_edit_permission(user, obj):
    """編集権限チェック"""
    # 権限ロジック
    return True
```

## パフォーマンス規約

### クエリ最適化

```python
# N+1問題の回避
products = Product.objects.select_related('category').prefetch_related('price_histories')

# ページネーション
from django.core.paginator import Paginator
paginator = Paginator(products, 25)
```

### キャッシュ戦略

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15分キャッシュ
def static_data_view(request):
    pass
```

## テスト規約

### テストファイル構成

```
tests/
├── __init__.py
├── test_models.py          # モデルテスト
├── test_views.py           # ビューテスト
├── test_forms.py           # フォームテスト
└── test_htmx.py           # HTMXテスト
```

### HTMXテスト例

```python
def test_htmx_add_row(self):
    response = self.client.get('/add-row/', HTTP_HX_REQUEST='true')
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'data-id="new"')
```

## デプロイ規約

### 環境設定

```python
# settings/base.py - 共通設定
# settings/development.py - 開発環境
# settings/production.py - 本番環境

# 環境変数での設定切り替え
DJANGO_SETTINGS_MODULE = os.environ.get('DJANGO_SETTINGS_MODULE', 'settings.development')
```

### 静的ファイル

```python
# 本番環境での静的ファイル配信
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
```