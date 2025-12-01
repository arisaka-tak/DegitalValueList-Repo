#!/usr/bin/env python
"""
テーブルを空にしてpk=product_numberになるようにリセット
"""
import os
import sys
import django

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product, PriceHistory, ProductApproval, PriceHistoryApproval
from dashboard.products_master.models import ProductGrossMarginRate

def reset_tables():
    """テーブルをリセット"""
    print("=== テーブルリセット開始 ===")
    
    # 外部キー制約を一時的に無効化
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = OFF")
    
    # 全データ削除
    print("全データを削除中...")
    ProductGrossMarginRate.objects.all().delete()
    PriceHistoryApproval.objects.all().delete()
    ProductApproval.objects.all().delete()
    PriceHistory.objects.all().delete()
    Product.objects.all().delete()
    
    # AUTO_INCREMENTをリセット
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='dashboard_products_master_product'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='dashboard_products_master_pricehistory'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='dashboard_products_master_productapproval'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='dashboard_products_master_pricehistoryapproval'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='dashboard_products_master_productgrossmarginrate'")
    
    # 外部キー制約を再有効化
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = ON")
    
    print("=== リセット完了 ===")
    print("これで新規作成時にpk=product_numberになります")

if __name__ == "__main__":
    reset_tables()