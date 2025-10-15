#!/usr/bin/env python
"""
商品番号1001の2026/09データの改定額調査スクリプト
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

def investigate_revision_amount():
    """商品番号1001の2026/09データの改定額を調査"""
    print("=== 商品番号1001の2026/09データ調査 ===")
    
    try:
        # 商品番号1001を取得
        product = Product.objects.get(product_number=1001)
        print(f"商品: {product.product_name}")
        
        # 2026/09のデータを取得
        target_history = PriceHistory.objects.filter(
            product=product,
            effective_year_month='2026/09',
            is_active=True
        ).first()
        
        if not target_history:
            print("2026/09のデータが見つかりません")
            return
        
        print(f"\n=== 2026/09データ ===")
        print(f"適用年月: {target_history.effective_year_month}")
        print(f"仕切価格: {target_history.wholesale_price}")
        print(f"県連価格: {target_history.kenren_price}")
        print(f"粗利率: {target_history.gross_margin_rate}")
        print(f"改定額: {target_history.revision_amount}")
        
        # 県連価格の数値を取得
        current_kenren_price = target_history._get_numeric_kenren_price()
        print(f"県連価格（数値）: {current_kenren_price}")
        
        # 前月のデータを取得
        previous_history = PriceHistory.objects.filter(
            product=product,
            effective_year_month__lt='2026/09',
            is_active=True
        ).order_by('-effective_year_month').first()
        
        if previous_history:
            print(f"\n=== 前月データ ({previous_history.effective_year_month}) ===")
            print(f"仕切価格: {previous_history.wholesale_price}")
            print(f"県連価格: {previous_history.kenren_price}")
            print(f"粗利率: {previous_history.gross_margin_rate}")
            print(f"改定額: {previous_history.revision_amount}")
            
            previous_kenren_price = previous_history._get_numeric_kenren_price()
            print(f"県連価格（数値）: {previous_kenren_price}")
            
            # 改定額の計算を検証
            if current_kenren_price is not None and previous_kenren_price is not None:
                calculated_revision = current_kenren_price - previous_kenren_price
                print(f"\n=== 改定額計算検証 ===")
                print(f"現在の県連価格: {current_kenren_price}")
                print(f"前月の県連価格: {previous_kenren_price}")
                print(f"計算結果: {current_kenren_price} - {previous_kenren_price} = {calculated_revision}")
                print(f"四捨五入後: {int(round(calculated_revision))}")
                print(f"DB保存値: {target_history.revision_amount}")
                print(f"動的計算値: {target_history.get_revision_amount()}")
                
                if int(round(calculated_revision)) == target_history.get_revision_amount():
                    print("OK: 改定額は正しく計算されています")
                else:
                    print("NG: DB値と動的計算値が異なります")
        else:
            print("\n前月のデータが見つかりません")
        
        # 全ての価格履歴を時系列で表示
        print(f"\n=== 商品番号1001の全価格履歴 ===")
        all_histories = PriceHistory.objects.filter(
            product=product,
            is_active=True
        ).order_by('effective_year_month')
        
        for i, history in enumerate(all_histories):
            kenren_numeric = history._get_numeric_kenren_price()
            print(f"{i+1}. {history.effective_year_month}: 仕切={history.wholesale_price}, 県連={history.kenren_price or '自動計算'} ({kenren_numeric}), 改定額={history.revision_amount}")
        
    except Product.DoesNotExist:
        print("商品番号1001が見つかりません")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_revision_amount()