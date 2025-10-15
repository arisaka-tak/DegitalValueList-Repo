# 技術的約束事

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
# 元テーブル
class Product(BaseModel):
    product_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    # 保存時に自動採番

# 承認テーブル
class ProductApproval(BaseModel):
    product_number = models.CharField(max_length=20)  # 元テーブルとの関連付け
    # 同じフィールド構成
    
    def approve(self):
        """承認処理: 元テーブルを削除して承認テーブルから挿入"""
        pass
```

## URL設計規約

### RESTful URL構成

```python
# 基本CRUD
urlpatterns = [
    path('', views.list_view, name='list'),           # GET: 一覧
    path('new/', views.new_view, name='new'),         # GET/POST: 新規作成
    path('<int:pk>/', views.detail_view, name='detail'), # GET/POST: 詳細/更新
    path('<int:pk>/delete/', views.delete_view, name='delete'), # POST: 削除
    
    # HTMX用API
    path('<int:pk>/add-row/', views.add_row, name='add_row'),
    path('row/<int:pk>/update/', views.update_row, name='update_row'),
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