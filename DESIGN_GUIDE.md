# デジタル価格表システム デザインガイドライン

## カラーパレット

- **プライマリ**: `#0d6efd` (Bootstrap Blue)
- **セカンダリ**: `#6c757d` (Bootstrap Gray)
- **成功**: `#198754` (Bootstrap Green)
- **情報**: `#0dcaf0` (Bootstrap Cyan)
- **警告**: `#ffc107` (Bootstrap Yellow)
- **危険**: `#dc3545` (Bootstrap Red)

## 共通コンポーネント

### 1. ページ構成
```html
{% extends 'base.html' %}
{% block breadcrumb %}
    {% include 'components/breadcrumb.html' %}
{% endblock %}
{% block content %}
    {% include 'components/page_header.html' %}
    <!-- メインコンテンツ -->
{% endblock %}
```

### 2. カード
- 影付き: `box-shadow: 0 2px 10px rgba(0,0,0,0.1)`
- 角丸: `border-radius: 10px`
- ホバー効果: `.card-hover` クラス使用

### 3. ボタン
- 角丸: `border-radius: 8px`
- パディング: `10px 20px`
- フォントウェイト: `500`

### 4. テーブル
- 白背景、影付き
- ヘッダー: プライマリカラー背景
- ホバー効果: 薄いプライマリカラー背景

### 5. フォーム
- 角丸: `border-radius: 8px`
- パディング: `12px 15px`
- ラベル: フォントウェイト `600`

## レスポンシブ対応

- モバイル: `max-width: 768px`
- タブレット: `768px - 992px`
- デスクトップ: `992px+`

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
    
    <div class="container">
        <div class="card">
            <div class="card-body">
                <!-- コンテンツ -->
            </div>
        </div>
    </div>
{% endblock %}
```