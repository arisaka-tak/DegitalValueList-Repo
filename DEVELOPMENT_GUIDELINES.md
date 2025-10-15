# 開発ガイドライン

## HTMX開発思想

このプロジェクトはHTMXの「HTML over the wire」思想に基づいて開発します。

### 基本原則

1. **サーバーサイド中心**: ロジックはサーバーサイド（Django）で処理
2. **最小限のJavaScript**: 必要最小限のJSのみ使用
3. **宣言的HTML**: HTMX属性でインタラクションを定義
4. **シンプルな通信**: 1つのリクエストで必要な処理を完結

## フロントエンド規約

### HTMLテンプレート

```html
<!-- ✅ 良い例: HTMXで宣言的に定義 -->
<button hx-post="/api/save/" 
        hx-include="#form1, #form2" 
        hx-target="#result">
    保存
</button>

<!-- ❌ 悪い例: JavaScriptで複雑な処理 -->
<button onclick="complexSaveFunction()">保存</button>
```

### JavaScript使用ルール

- **使用OK**: DOM操作（表示/非表示、スタイル変更）
- **使用NG**: API通信、複雑なビジネスロジック

```javascript
// ✅ 良い例: シンプルなDOM操作
function toggleVisibility(element) {
    element.style.display = element.style.display === 'none' ? 'block' : 'none';
}

// ❌ 悪い例: 複雑なAPI通信
function saveAllData() {
    Promise.all([fetch('/api1'), fetch('/api2')]).then(...)
}
```

## バックエンド規約

### ビュー設計

```python
def my_view(request):
    if request.method == 'POST':
        # 一括処理: 画面の全データを処理
        return process_all_data(request)
    else:
        # 表示処理
        return render(request, 'template.html', context)

def process_all_data(request):
    """画面の全データを一括処理"""
    # 1. バリデーション
    # 2. データ保存/更新/削除
    # 3. レスポンス返却
    pass
```

### データ送信規約

#### フォームフィールド命名規則

```html
<!-- 新規データ -->
<input name="new_field_0" value="...">
<input name="new_field_1" value="...">

<!-- 既存データ更新 -->
<input name="edit_field_123" value="...">  <!-- 123はレコードID -->

<!-- 削除フラグ -->
<input type="hidden" name="delete_123" value="true">
```

#### サーバーサイド処理

```python
def process_all_data(request):
    # 新規データ処理
    for key, value in request.POST.items():
        if key.startswith('new_'):
            # 新規作成処理
            pass
    
    # 更新データ処理
    for key, value in request.POST.items():
        if key.startswith('edit_'):
            # 更新処理
            pass
    
    # 削除データ処理
    for key, value in request.POST.items():
        if key.startswith('delete_') and value == 'true':
            # 削除処理
            pass
```

## ファイル構成規約

### テンプレート構成

```
templates/
├── base.html                    # ベーステンプレート
├── app_name/
│   ├── list.html               # 一覧画面
│   ├── detail.html             # 詳細画面
│   └── partials/               # HTMX用部分テンプレート
│       ├── table.html          # テーブル全体
│       ├── row.html            # テーブル行
│       └── form_section.html   # フォーム部分
```

### ビュー構成

```
views/
├── __init__.py
├── list_views.py               # 一覧系ビュー
├── detail_views.py             # 詳細系ビュー
└── api_views.py                # HTMX用APIビュー
```

## 実装パターン

### 1. 一覧画面パターン

```html
<!-- 検索フォーム -->
<form hx-get="/search/" hx-target="#results">
    <input name="q" type="search">
    <button type="submit">検索</button>
</form>

<!-- 結果表示エリア -->
<div id="results">
    {% include 'partials/table.html' %}
</div>
```

### 2. 詳細画面パターン

```html
<!-- 一括保存フォーム -->
<form id="mainForm">
    <!-- 基本情報 -->
    <!-- 関連データ -->
</form>

<!-- 保存ボタン -->
<button hx-post="/save/" 
        hx-include="#mainForm" 
        hx-target="body">
    保存
</button>
```

### 3. 動的追加パターン

```html
<!-- 追加ボタン -->
<button hx-get="/add-row/" 
        hx-target="#container">
    行追加
</button>

<!-- コンテナ -->
<div id="container">
    {% include 'partials/table.html' %}
</div>
```

## 禁止事項

### ❌ やってはいけないこと

1. **複雑なJavaScript**: 複数のfetch()を組み合わせた処理
2. **差分更新**: 個別のフィールド更新API
3. **クライアントサイドバリデーション**: サーバーサイドで実施
4. **状態管理**: JavaScriptでの複雑な状態管理

### ✅ 推奨すること

1. **サーバーサイド処理**: 全ロジックをDjangoで実装
2. **一括処理**: 1つのリクエストで完結
3. **宣言的HTML**: HTMX属性での定義
4. **シンプルなJS**: DOM操作のみ

## レビューチェックリスト

新機能実装時は以下をチェック：

- [ ] JavaScriptでAPI通信していないか？
- [ ] 1つのリクエストで処理が完結するか？
- [ ] HTMX属性で宣言的に定義されているか？
- [ ] サーバーサイドで一括処理されているか？
- [ ] 命名規則に従っているか？

## 参考資料

- [HTMX公式ドキュメント](https://htmx.org/)
- [HTML over the wire思想](https://hotwired.dev/)