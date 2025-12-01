#!/usr/bin/env python
"""
product_numberフィールドを削除してpkのみで管理するマイグレーション
"""
import os
import sys
import django

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product, ProductApproval

def remove_product_number_field():
    """product_numberフィールドの削除準備"""
    print("=== product_number削除の準備 ===")
    
    # 現在のデータ確認
    print("現在のProductデータ:")
    for product in Product.objects.all():
        print(f"  pk={product.pk}, product_number={product.product_number}")
    
    print("\n現在のProductApprovalデータ:")
    for approval in ProductApproval.objects.all():
        print(f"  pk={approval.pk}, product_number={approval.product_number}")
    
    print("\n次の手順:")
    print("1. models.pyからproduct_numberフィールドを削除")
    print("2. makemigrations & migrate実行")
    print("3. コード内のproduct_number参照をpkに変更")
    
    print("\n注意: この変更は大きな影響があります。")
    print("バックアップを取ってから実行してください。")

if __name__ == "__main__":
    remove_product_number_field()