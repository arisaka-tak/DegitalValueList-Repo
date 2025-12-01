#!/usr/bin/env python
"""
商品データ確認スクリプト
"""
import os
import sys
import django

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product

def check_products():
    """商品データを確認"""
    print("=== 商品データ確認 ===")
    
    # 全商品を表示
    products = Product.objects.all()[:10]  # 最初の10件
    print(f"商品総数: {Product.objects.count()}")
    
    for product in products:
        print(f"pk={product.pk}, product_number={product.product_number}, name={product.product_name}")
    
    # 商品番号1を検索
    print("\n=== 商品番号1の検索 ===")
    try:
        product_by_number = Product.objects.get(product_number=1)
        print(f"商品番号1で検索: pk={product_by_number.pk}, name={product_by_number.product_name}")
    except Product.DoesNotExist:
        print("商品番号1は存在しません")
    
    # pk=1を検索
    print("\n=== pk=1の検索 ===")
    try:
        product_by_pk = Product.objects.get(pk=1)
        print(f"pk=1で検索: product_number={product_by_pk.product_number}, name={product_by_pk.product_name}")
    except Product.DoesNotExist:
        print("pk=1は存在しません")

if __name__ == "__main__":
    check_products()