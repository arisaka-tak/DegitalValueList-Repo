# テスト時の承認フロースキップ手順

## 目的
リリース前の動作確認で、承認フローを一時的にスキップして自分で商品登録をテストする

## ⚠️ 重要な注意事項
- **この変更は一時的なテストのみに使用**
- **本番リリース前に必ず元に戻すこと**
- **バージョンチェッカーを使わず、直接EXEを起動してテスト**

---

## 手順

### 1. コードの一時的な変更

**ファイル:** `dashboard/products_master/product_detail/product_detail_views.py`

**変更箇所:** `approve_application` 関数（約1445行目付近）

#### 変更前:
```python
def approve_application(request, pk):
    """申請を承認"""
    if request.method != 'POST':
        messages.error(request, '無効なリクエストです')
        return redirect('products_master:approval_list')
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 自己承認チェック
        current_user = get_current_user()
        if approval.applicant == current_user:
            messages.error(request, '自分が申請したデータは承認できません')
            return redirect('products_master:approval_detail', pk=pk)
        
        _process_approval(approval)
        print(f"Debug: Approval {pk} processing completed successfully")
        messages.success(request, '承認完了')
        return redirect('products_master:approval_list')
```

#### 変更後（自己承認チェックをコメントアウト）:
```python
def approve_application(request, pk):
    """申請を承認"""
    if request.method != 'POST':
        messages.error(request, '無効なリクエストです')
        return redirect('products_master:approval_list')
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 自己承認チェック
        # ★★★ テスト用に一時的にコメントアウト ★★★
        # current_user = get_current_user()
        # if approval.applicant == current_user:
        #     messages.error(request, '自分が申請したデータは承認できません')
        #     return redirect('products_master:approval_detail', pk=pk)
        
        _process_approval(approval)
        print(f"Debug: Approval {pk} processing completed successfully")
        messages.success(request, '承認完了')
        return redirect('products_master:approval_list')
```

### 2. 一括承認の変更（オプション）

一括承認も使う場合は、`bulk_approve` 関数（約1789行目付近）も同様に変更:

#### 変更箇所:
```python
# 自己承認チェック
# ★★★ テスト用に一時的にコメントアウト ★★★
# if approval.applicant == current_user:
#     error_count += 1
#     error_msg = f"ID {approval_id}: 自分が申請したデータは承認できません"
#     error_messages.append(error_msg)
#     print(f"Error: {error_msg}")
#     continue
```

---

## テスト手順

### 1. EXEをビルド
```powershell
pyinstaller DigitalValueList.spec
```

### 2. 直接起動してテスト
```powershell
# バージョンチェッカーを使わず、直接起動
dist\DigitalValueList.exe
```

### 3. テスト商品を登録
1. 商品を新規作成
2. 申請ボタンをクリック
3. 承認一覧から自分で承認
4. 商品が正常に登録されることを確認

---

## テスト完了後の復元

### ⚠️ 必ず実施すること

**1. コメントアウトを元に戻す**

`product_detail_views.py` の変更を元に戻す:

```python
# 自己承認チェック
current_user = get_current_user()
if approval.applicant == current_user:
    messages.error(request, '自分が申請したデータは承認できません')
    return redirect('products_master:approval_detail', pk=pk)
```

**2. 再ビルド**

```powershell
pyinstaller DigitalValueList.spec
```

**3. 確認**

- [ ] コメントアウトを全て削除した
- [ ] 再ビルドが完了した
- [ ] テストデータを削除した（必要に応じて）

---

## チェックリスト

### テスト前
- [ ] コードを一時的に変更
- [ ] EXEをビルド
- [ ] 直接起動でテスト

### テスト後
- [ ] コードを元に戻す
- [ ] 再ビルド
- [ ] 本番リリース用のEXEを確認

---

## 別の方法: テスト用ユーザーを使う

承認フローをスキップせず、2つのユーザーでテストする方法:

1. **ユーザーA**: 商品を申請
2. **ユーザーB**: 承認

※ この方法の場合、コード変更は不要

---

**作成日:** 2025/01/XX  
**注意:** このドキュメントはテスト用の一時的な手順です。本番環境では使用しないでください。
