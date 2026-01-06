# デジタル価格表システム デザインガイドライン

## カラーパレット

```css
:root {
    --primary-color: #0d6efd;    /* Bootstrap Blue */
    --secondary-color: #6c757d;  /* Bootstrap Gray */
    --success-color: #198754;    /* Bootstrap Green */
    --info-color: #0dcaf0;       /* Bootstrap Cyan */
    --warning-color: #ffc107;    /* Bootstrap Yellow */
    --danger-color: #dc3545;     /* Bootstrap Red */
    --light-color: #f8f9fa;      /* 背景色 */
    --dark-color: #212529;       /* テキスト色 */
}
```

## レイアウト構成

### ベースレイアウト
- **ナビゲーションバー**: 上部固定、プライマリカラー
- **サイドナビ**: 左側250px固定幅、メニュー階層構造
- **メインコンテンツ**: 可変幅、水平スクロール対応

### サイドナビゲーション
```html
<nav style="width: 250px; background-color: #f8f9fa;">
    <div class="p-3">
        <h6 class="text-muted mb-3">メニュー</h6>
        <ul class="nav flex-column">
            <!-- メインメニュー -->
            <li class="nav-item mb-2">
                <a class="nav-link d-flex align-items-center">
                    <span class="me-2">📦</span> 商品マスタ管理
                </a>
            </li>
            <!-- サブメニュー -->
            <li class="nav-item mb-2">
                <h6 class="text-muted mb-2 mt-3">システム管理</h6>
                <ul class="nav flex-column ms-3">
                    <li class="nav-item mb-1">
                        <a class="nav-link">🐄 畜種マスタ</a>
                    </li>
                </ul>
            </li>
        </ul>
    </div>
</nav>
```

## 共通コンポーネント

### 1. カードコンポーネント
```css
.card {
    border: none;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    border-radius: 10px;
}

.card-hover {
    transition: all 0.2s ease;
}

.card-hover:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
```

### 2. ボタンコンポーネント
```css
.btn {
    border-radius: 8px;
    font-weight: 500;
    padding: 10px 20px;
}
```

### 3. テーブルコンポーネント
```css
.table {
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.table thead th {
    background-color: var(--primary-color);
    color: white;
    border: none;
    font-weight: 600;
}

.table tbody tr:hover {
    background-color: rgba(13, 110, 253, 0.1);
}
```

### 4. フォームコンポーネント
```css
.form-control {
    border-radius: 8px;
    border: 1px solid #dee2e6;
    padding: 12px 15px;
}

.form-control:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}

.form-label {
    font-weight: 600;
    color: var(--dark-color);
    margin-bottom: 8px;
}
```

### 5. メッセージコンポーネント
```html
<!-- Djangoメッセージフレームワーク連携 -->
{% if messages %}
    <div class="container mt-3">
        {% for message in messages %}
            <div class="alert alert-{% if message.tags == 'error' %}danger{% elif message.tags == 'warning' %}warning{% elif message.tags == 'success' %}success{% else %}info{% endif %} alert-dismissible fade show">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        {% endfor %}
    </div>
{% endif %}
```

## レスポンシブ対応

```css
/* モバイル対応 */
@media (max-width: 768px) {
    .page-title {
        font-size: 1.5rem;
    }
    
    .sidebar {
        width: 100% !important;
        height: auto;
        position: relative;
    }
    
    .d-flex {
        flex-direction: column;
    }
}
```

- **モバイル**: `max-width: 768px` - サイドナビが上部に移動
- **タブレット**: `768px - 992px` - サイドナビ維持
- **デスクトップ**: `992px+` - フルレイアウト

## 特殊コンポーネント

### 価格テーブル
```css
/* ヘッダー固定スクロールテーブル */
.price-table-wrapper {
    max-height: 85vh;
    overflow: auto;
    position: relative;
}

.price-table-wrapper #priceTable thead tr th {
    position: sticky !important;
    top: 0 !important;
    z-index: 102 !important;
    background-color: #4472C4 !important;
    color: #fff !important;
}
```

### 管理者限定メニュー
```html
{% if is_admin %}
<li class="nav-item mb-2">
    <h6 class="text-muted mb-2 mt-3">データ管理(ホスト:BC101131~のみ)</h6>
    <ul class="nav flex-column ms-3">
        <li class="nav-item mb-1">
            <a class="nav-link text-warning">♨️ ステータスリセット</a>
        </li>
        <li class="nav-item mb-1">
            <a class="nav-link text-danger">🗑️ データクリア</a>
        </li>
    </ul>
</li>
{% endif %}
```

## 使用例

### ページテンプレート
```html
{% extends 'base.html' %}

{% block title %}商品一覧 - デジタル価格表システム{% endblock %}

{% block breadcrumb %}
    {% include 'components/breadcrumb.html' with breadcrumbs=breadcrumbs %}
{% endblock %}

{% block content %}
    {% include 'components/page_header.html' with page_title="商品一覧" page_subtitle="商品マスタの管理" %}
    
    <div class="container" style="max-width: none; margin: 0; padding: 1rem;">
        <div class="card">
            <div class="card-body">
                <!-- コンテンツ -->
            </div>
        </div>
    </div>
{% endblock %}
```

### フォームレイアウト
```html
<form method="post">
    {% csrf_token %}
    <div class="row g-3">
        <div class="col-md-6">
            <label class="form-label">商品名</label>
            <input type="text" class="form-control" name="product_name">
        </div>
        <div class="col-md-6">
            <label class="form-label">メーカー</label>
            <select class="form-control" name="manufacturer">
                <option value="">選択してください</option>
            </select>
        </div>
    </div>
    <div class="mt-3">
        <button type="submit" class="btn btn-primary">保存</button>
        <a href="#" class="btn btn-secondary">キャンセル</a>
    </div>
</form>
```