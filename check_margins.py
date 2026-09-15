#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import PriceHistory

print("価格履歴の粗利率を確認:")
for history in PriceHistory.objects.filter(is_active=True).order_by('id'):
    print(f"ID: {history.id}, 商品: {history.product.product_name}, 粗利率: {history.gross_margin_rate}, 仕切: {history.wholesale_price}, 県連: {history.kenren_price}")