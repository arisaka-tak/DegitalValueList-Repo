#!/usr/bin/env python
"""
県連価格自動計算の根拠調査スクリプト
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

from dashboard.products_master.models import ProductApproval, PriceHistoryApproval

def investigate_kenren_calculation():
    """県連価格の自動計算根拠を調査"""
    print("=== 県連価格自動計算の根拠調査 ===")
    
    try:
        # 最新の申請データを取得
        latest_approval = ProductApproval.objects.filter(product_number=2005).first()
        
        if not latest_approval:
            print("商品番号2005の申請データが見つかりません")
            return
        
        print(f"申請商品: {latest_approval.product_name}")
        print(f"申請日時: {latest_approval.created_at}")
        
        # 申請の価格履歴を取得
        approval_histories = PriceHistoryApproval.objects.filter(
            product=latest_approval,
            is_active=True
        ).order_by('effective_year_month')
        
        print(f"\n=== 申請価格履歴 ===")
        for history in approval_histories:
            print(f"適用年月: {history.effective_year_month}")
            print(f"仕切価格: {history.wholesale_price}")
            print(f"県連価格: {history.kenren_price}")
            print(f"粗利率: {history.gross_margin_rate}")
            
            # 自動計算を実行
            if not history.kenren_price and history.wholesale_price:
                try:
                    if history.wholesale_price != '都度見積':
                        wholesale_num = float(str(history.wholesale_price).replace(',', ''))
                        margin_rate = float(history.gross_margin_rate)
                        calculated = wholesale_num * margin_rate
                        
                        print(f"\n=== 自動計算 ===")
                        print(f"仕切価格: {wholesale_num}")
                        print(f"粗利率: {margin_rate}")
                        print(f"計算式: {wholesale_num} × {margin_rate} = {calculated}")
                        print(f"端数処理後: {int(calculated)}")
                        
                except (ValueError, TypeError) as e:
                    print(f"計算エラー: {e}")
            
            print("-" * 40)
        
        # 新規履歴作成時のデフォルト粗利率を確認
        print(f"\n=== デフォルト設定 ===")
        print("新規履歴作成時の粗利率: 1.1 (固定値)")
        print("計算例: 100 × 1.1 = 110")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_kenren_calculation()