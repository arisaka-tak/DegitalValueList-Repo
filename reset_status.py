#!/usr/bin/env python
"""
商品ステータス強制リセットスクリプト
"""
import os
import sys
import django

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product, ProductApproval

def reset_product_status():
    """商品番号1のステータスをリセット"""
    try:
        # 商品番号1のステータスをクリア
        product = Product.objects.get(product_number=1)
        product.status = ''
        product.approver = ''
        product.save()
        print(f"商品番号1のステータスをリセットしました: {product.product_name}")
        
    except Product.DoesNotExist:
        print("商品番号1が見つかりません")
    
    # 関連する申請データも削除
    try:
        approvals = ProductApproval.objects.filter(product_number=1)
        count = approvals.count()
        approvals.delete()
        print(f"商品番号1の申請データを{count}件削除しました")
        
    except Exception as e:
        print(f"申請データ削除エラー: {e}")

if __name__ == "__main__":
    reset_product_status()