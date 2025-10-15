#!/usr/bin/env python
"""
商品番号2005のデータ調査スクリプト
"""
import os
import sys
import django
from pathlib import Path

# Djangoプロジェクトのルートディレクトリを設定
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')

# Djangoを初期化
django.setup()

from dashboard.products_master.models import Product, PriceHistory

def investigate_product_2005():
    """商品番号2005のデータを調査"""
    print("=== 商品番号2005のデータ調査 ===")
    
    try:
        # 商品番号2005を取得
        product = Product.objects.get(product_number=2005)
        print(f"商品: {product.product_name}")
        print(f"メーカー: {product.manufacturer}")
        print(f"畜種: {product.livestock_type}")
        print(f"分類: {product.category}")
        print(f"商品コード: {product.product_code}")
        print(f"型式: {product.model_number}")
        print(f"規格: {product.specification}")
        print(f"発送単位: {product.shipping_unit}")
        print(f"送料: {product.shipping_fee}")
        print(f"備考: {product.remarks}")
        print(f"作成日時: {product.created_at}")
        print(f"更新日時: {product.updated_at}")
        print(f"有効フラグ: {product.is_active}")
        
        # 価格履歴を取得
        print(f"\n=== 価格履歴 ===")
        all_histories = PriceHistory.objects.filter(product=product).order_by('effective_year_month')
        active_histories = PriceHistory.objects.filter(product=product, is_active=True).order_by('effective_year_month')
        
        print(f"全履歴件数: {all_histories.count()}")
        print(f"有効履歴件数: {active_histories.count()}")
        
        if all_histories.exists():
            print("\n全履歴:")
            for i, history in enumerate(all_histories):
                print(f"{i+1}. {history.effective_year_month}: 仕切={history.wholesale_price}, 県連={history.kenren_price}, 有効={history.is_active}")
        else:
            print("価格履歴が存在しません")
        
        # 申請テーブルも確認
        from dashboard.products_master.models import ProductApproval
        approvals = ProductApproval.objects.filter(product_number=2005)
        print(f"\n申請テーブル件数: {approvals.count()}")
        
        if approvals.exists():
            print("申請データ:")
            for approval in approvals:
                print(f"- {approval.product_name} (作成: {approval.created_at})")
        
    except Product.DoesNotExist:
        print("商品番号2005が見つかりません")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_product_2005()