#!/usr/bin/env python
"""
データベースの内容を確認するスクリプト
"""
import os
import sys
import django

# Djangoプロジェクトのルートディレクトリを設定
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Django設定を読み込み
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product, PriceHistory

def check_data():
    print("=== データベース内容確認 ===")
    
    # 商品マスタの確認
    print(f"\n【商品マスタ】")
    products = Product.objects.all()
    print(f"全商品数: {products.count()}")
    
    active_products = Product.active_objects.all()
    print(f"有効商品数: {active_products.count()}")
    
    if products.exists():
        print("\n最新の商品5件:")
        for product in products.order_by('-pk')[:5]:
            print(f"  ID:{product.pk} - {product.product_name} (有効:{product.is_active})")
    
    # 価格履歴の確認
    print(f"\n【価格履歴】")
    price_histories = PriceHistory.objects.all()
    print(f"全価格履歴数: {price_histories.count()}")
    
    active_histories = PriceHistory.objects.filter(is_active=True)
    print(f"有効価格履歴数: {active_histories.count()}")
    
    if price_histories.exists():
        print("\n最新の価格履歴5件:")
        for history in price_histories.order_by('-pk')[:5]:
            print(f"  ID:{history.pk} - 商品ID:{history.product.pk} {history.product.product_name} - {history.effective_year_month} (有効:{history.is_active})")
    
    # データベースファイルの確認
    db_path = os.path.join(project_root, 'db.sqlite3')
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path)
        print(f"\nデータベースファイル: {db_path}")
        print(f"ファイルサイズ: {file_size:,} bytes")
    else:
        print(f"\nデータベースファイルが見つかりません: {db_path}")

if __name__ == "__main__":
    check_data()