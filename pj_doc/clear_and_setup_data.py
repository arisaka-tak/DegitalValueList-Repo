#!/usr/bin/env python
"""
データベースをクリアして新しいダミーデータを作成するスクリプト
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product, PriceHistory, ProductApproval, PriceHistoryApproval, ProductGrossMarginRate
from decimal import Decimal

def clear_all_data():
    """全データをクリア"""
    print("=== データクリア開始 ===")
    
    # 申請テーブルをクリア
    PriceHistoryApproval.objects.all().delete()
    ProductApproval.objects.all().delete()
    print("申請テーブルをクリアしました")
    
    # 価格履歴をクリア
    PriceHistory.objects.all().delete()
    print("価格履歴をクリアしました")
    
    # 粗利率テーブルをクリア
    ProductGrossMarginRate.objects.all().delete()
    print("粗利率テーブルをクリアしました")
    
    # 商品マスタをクリア
    Product.objects.all().delete()
    print("商品マスタをクリアしました")
    
    print("=== データクリア完了 ===")

def create_dummy_data():
    """ダミーデータを作成"""
    print("=== ダミーデータ作成開始 ===")
    
    # 商品マスタ作成
    products = [
        {
            'product_code': 'A001',
            'livestock_type': '牛',
            'category': '飼料',
            'manufacturer': 'メーカーA',
            'product_name': '牛用配合飼料',
            'model_number': 'CF-100',
            'specification': '20kg袋',
            'shipping_unit': '1袋',
            'shipping_fee': '別途',
            'remarks': 'テスト商品1'
        },
        {
            'product_code': 'B002',
            'livestock_type': '豚',
            'category': '飼料',
            'manufacturer': 'メーカーB',
            'product_name': '豚用配合飼料',
            'model_number': 'PF-200',
            'specification': '25kg袋',
            'shipping_unit': '1袋',
            'shipping_fee': '込み',
            'remarks': 'テスト商品2'
        }
    ]
    
    created_products = []
    for product_data in products:
        product = Product.objects.create(**product_data)
        created_products.append(product)
        print(f"商品作成: {product.product_name}")
    
    # 粗利率マスタ作成
    margin_rates = [
        # 商品1の粗利率
        {'product': created_products[0], 'period_year': 2024, 'gross_margin_rate': Decimal('1.15'), 'base_kenren_price': 2300, 'base_wholesale_price': 2000, 'calculation_note': '2024年度基準粗利率'},
        {'product': created_products[0], 'period_year': 2025, 'gross_margin_rate': Decimal('1.20'), 'base_kenren_price': 2400, 'base_wholesale_price': 2000, 'calculation_note': '2025年度基準粗利率'},
        
        # 商品2の粗利率
        {'product': created_products[1], 'period_year': 2024, 'gross_margin_rate': Decimal('1.10'), 'base_kenren_price': 2750, 'base_wholesale_price': 2500, 'calculation_note': '2024年度基準粗利率'},
        {'product': created_products[1], 'period_year': 2025, 'gross_margin_rate': Decimal('1.12'), 'base_kenren_price': 2800, 'base_wholesale_price': 2500, 'calculation_note': '2025年度基準粗利率'},
    ]
    
    for margin_data in margin_rates:
        margin_rate = ProductGrossMarginRate.objects.create(**margin_data)
        print(f"粗利率作成: {margin_rate.product.product_name} {margin_rate.period_year}年度 {margin_rate.gross_margin_rate}")
    
    # 価格履歴作成
    price_histories = [
        # 商品1の価格履歴
        {'product': created_products[0], 'period_year': 2024, 'effective_year_month': '2024/04', 'gross_margin_rate': Decimal('1.15'), 'wholesale_price': '2000', 'kenren_price': None},
        {'product': created_products[0], 'period_year': 2024, 'effective_year_month': '2024/08', 'gross_margin_rate': Decimal('1.15'), 'wholesale_price': '2100', 'kenren_price': None},
        {'product': created_products[0], 'period_year': 2025, 'effective_year_month': '2025/04', 'gross_margin_rate': Decimal('1.20'), 'wholesale_price': '2200', 'kenren_price': None},
        
        # 商品2の価格履歴
        {'product': created_products[1], 'period_year': 2024, 'effective_year_month': '2024/04', 'gross_margin_rate': Decimal('1.10'), 'wholesale_price': '2500', 'kenren_price': None},
        {'product': created_products[1], 'period_year': 2025, 'effective_year_month': '2025/04', 'gross_margin_rate': Decimal('1.12'), 'wholesale_price': '2600', 'kenren_price': None},
    ]
    
    for history_data in price_histories:
        history = PriceHistory.objects.create(**history_data)
        print(f"価格履歴作成: {history.product.product_name} {history.effective_year_month}")
    
    print("=== ダミーデータ作成完了 ===")

if __name__ == "__main__":
    clear_all_data()
    create_dummy_data()
    print("=== 全処理完了 ===")