#!/usr/bin/env python
import os
import sys
import django
import sqlite3

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import LivestockType, Category
from django.db import connection

# 直接SQLで既存データを取得
with connection.cursor() as cursor:
    cursor.execute("SELECT DISTINCT livestock_type FROM products_master_product WHERE livestock_type IS NOT NULL AND livestock_type != ''")
    livestock_types = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT category FROM products_master_product WHERE category IS NOT NULL AND category != ''")
    categories = [row[0] for row in cursor.fetchall()]

print(f"既存畜種: {livestock_types}")
print(f"既存分類: {categories}")

# 畜種マスタを作成
for i, livestock_type in enumerate(sorted(livestock_types)):
    LivestockType.objects.get_or_create(
        name=livestock_type,
        defaults={'sort_order': i + 1}
    )
    print(f"畜種マスタ作成: {livestock_type}")

# 分類マスタを作成
for i, category in enumerate(sorted(categories)):
    Category.objects.get_or_create(
        name=category,
        defaults={'sort_order': i + 1}
    )
    print(f"分類マスタ作成: {category}")

print("マスタデータ作成完了")