# 画面別ボタン・関数一覧

## 1. ダッシュボード画面

**ボタン**: なし（カードリンクのみ）

---

## 2. 商品一覧画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| 🤖 AI価格抽出 | - | リンク遷移 |
| 新規登録 | - | リンク遷移 |
| 詳細 | - | リンク遷移 |
| コピー | - | リンク遷移 |
| 削除 | - | リンク遷移 |
| 絞り込み | - | フォーム送信 → product_list_views.py の product_list() 関数 |
| クリア | - | リンク遷移 |

---

## 3. AI価格抽出入力画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| AI抽出開始 | - | フォーム送信（ローディング表示あり） → ai_price_extract_views.py の ai_extract() 関数 |
| + 商品追加 | `addProduct()` | 商品フォーム追加 |
| 削除 | `removeProduct(id)` | 商品フォーム削除 |
| サンプルデータを読み込み | `loadSampleData()` | サンプルデータ読み込み |
| 商品照合を実行 | - | フォーム送信（fetch API） → ai_price_extract_views.py の match_products() 関数 |
| 戻る | - | リンク遷移 |

---

## 4. 商品詳細・編集画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| 新規追加 | `addPriceRow()` | 価格履歴行追加 |
| 申請 | `submitApplication(button)` | 申請処理 |
| 保存 | - | フォーム送信 → product_detail_views.py の product_save() 関数 |
| 戻る | - | リンク遷移 |
| コピー | - | リンク遷移 |

### 内部関数
- `validateForm()` - フォームバリデーション
- `updateGrossMargin(kenrenInput)` - 粗利率更新
- `updateKenrenPriceDisplay(changedInput)` - 県連価格表示更新

---

## 5. 承認ワークフロー画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| 一括承認 | - | フォーム送信 → product_detail_views.py の bulk_approve() 関数 |
| 承認 | - | フォーム送信 → product_detail_views.py の approve_application() 関数 |
| 却下 | - | フォーム送信 → product_detail_views.py の reject_application() 関数 |
| 詳細 | - | リンク遷移 |

---

## 6. デジタル価格表画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| 🤖 AI価格抽出 | - | リンク遷移 |
| 新規作成 | - | リンク遷移 |
| 絞り込み | - | フォーム送信 → integrated_pricelist_views.py の integrated_pricelist() 関数 |
| クリア | - | リンク遷移 |
| 並び順をリセット | `resetSortOrder()` | 並び順リセット |
| 並び順を保存 | `saveSortOrder()` | 並び順保存 |
| Excel出力 | `exportExcel()` | Excel出力 |
| ↑ | `moveUp(this)` | 行を上に移動 |
| ↓ | `moveDown(this)` | 行を下に移動 |
| ⤴ | `moveToPrevPage(this)` | 前ページ末尾へ移動 |
| ⤵ | `moveToNextPage(this)` | 次ページ先頭へ移動 |

### 内部関数
- `handleDragStart(e)` - ドラッグ開始
- `handleDragOver(e)` - ドラッグオーバー
- `handleDrop(e)` - ドロップ
- `handleDragEnd(e)` - ドラッグ終了
- `canMove(sourceRow, targetRow)` - 移動可能性チェック
- `updateRowNumbers()` - 行番号更新
- `updateGroupBorders()` - グループ境界線更新
- `markSortChanged()` - 並び順変更フラグ
- `crossPageMove(productId, direction)` - ページ間移動API呼び出し

---

## 7. マスタ管理画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| 新規登録 | - | リンク遷移 |
| 編集 | - | リンク遷移 |
| 削除 | - | フォーム送信 → master_views.py の master_delete() 関数 |
| 保存 | - | フォーム送信 → master_views.py の master_save() 関数 |
| 戻る | - | リンク遷移 |

---

## 8. 決裁書管理画面

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| アップロード | - | フォーム送信 → product_detail_views.py の document_upload() 関数 |
| 戻る | - | リンク遷移 |

---

## 9. システム管理画面（管理者限定）

| ボタン | 発火する関数 | 備考 |
|--------|-------------|------|
| エクスポート | - | フォーム送信 → system_admin/views.py の data_export() 関数 |
| インポート | - | フォーム送信 → system_admin/views.py の data_import() 関数 |
| キーワード一括再生成 | - | フォーム送信（確認ダイアログあり） → keyword_batch_views.py の regenerate_keywords() 関数 |
| ステータスリセット | - | フォーム送信（確認ダイアログあり） → system_admin/views.py の reset_status() 関数 |
| データクリア | - | フォーム送信（確認ダイアログあり） → system_admin/views.py の clear_data() 関数 |

---

## 10. バージョン管理システム

### VersionChecker.exe
**ボタン**: なし（自動実行）

### Django_run.py
**ボタン**: なし（自動実行）

---

## 共通JavaScript関数

### ドラッグ&ドロップ関連
- `handleDragStart(e)` - ドラッグ開始処理
- `handleDragOver(e)` - ドラッグオーバー処理
- `handleDrop(e)` - ドロップ処理
- `handleDragEnd(e)` - ドラッグ終了処理
- `canMove(sourceRow, targetRow)` - 移動可能性チェック

### テーブル操作関連
- `updateRowNumbers()` - 行番号更新
- `updateGroupBorders()` - グループ境界線更新
- `markSortChanged()` - 並び順変更フラグ設定

### API呼び出し関連
- `crossPageMove(productId, direction)` - ページ間移動API
- `saveSortOrder()` - 並び順保存API
- `resetSortOrder()` - 並び順リセットAPI
- `exportExcel()` - Excel出力

### フォーム関連
- `validateForm()` - フォームバリデーション
- `submitApplication(button)` - 申請処理
- `addProduct(data)` - 商品フォーム追加
- `removeProduct(id)` - 商品フォーム削除
- `loadSampleData()` - サンプルデータ読み込み

### 価格計算関連
- `updateGrossMargin(kenrenInput)` - 粗利率更新
- `updateKenrenPriceDisplay(changedInput)` - 県連価格表示更新
- `addPriceRow()` - 価格履歴行追加

---

## 注意事項

- **リンク遷移**: `href`属性による画面遷移
- **フォーム送信**: `method="post"`によるサーバー送信
- **fetch API**: JavaScriptによる非同期通信
- **確認ダイアログ**: `confirm()`による確認処理
- **ローディング表示**: ボタン無効化・テキスト変更による処理中表示