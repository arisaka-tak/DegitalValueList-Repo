#!/usr/bin/env python
"""
pkとproduct_numberの関係を詳しく調査
"""
import os
import sys
import django

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product

def check_pk_sequence():
    """pkとproduct_numberの関係を調査"""
    print("=== pkとproduct_numberの関係 ===")
    
    products = Product.objects.all().order_by('pk')
    
    for product in products:
        print(f"pk={product.pk:2d}, product_number={product.product_number:2d}, name={product.product_name}")
    
    print(f"\n最小pk: {Product.objects.all().aggregate(min_pk=models.Min('pk'))}")
    print(f"最大pk: {Product.objects.all().aggregate(max_pk=models.Max('pk'))}")

if __name__ == "__main__":
    from django.db import models
    check_pk_sequence()