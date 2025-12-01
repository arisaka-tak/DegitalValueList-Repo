#!/usr/bin/env python
"""
pk=product_numberになるようにデータを修正するパッチ
"""
import os
import sys
import django
from django.db import transaction

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_pricelist_system.settings')
django.setup()

from dashboard.products_master.models import Product, PriceHistory, ProductApproval, PriceHistoryApproval
from dashboard.products_master.models import ProductGrossMarginRate

def fix_pk_product_number():
    """pk=product_numberになるようにデータを修正"""
    print("=== pk=product_number修正パッチ開始 ===")
    
    # 外部キー制約を一時的に無効化
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = OFF")
    
    with transaction.atomic():
        # 既存商品を取得
        products = Product.objects.all().order_by('product_number')
        
        print("現在のデータ:")
        for product in products:
            print(f"  pk={product.pk}, product_number={product.product_number}, name={product.product_name}")
        
        # 新しいデータを作成
        new_products = []
        for product in products:
            # 新しいproduct_numberでProductを作成
            new_product = Product(
                product_number=product.product_number,  # これがpkになる
                product_code=product.product_code,
                livestock_type=product.livestock_type,
                category=product.category,
                manufacturer=product.manufacturer,
                product_name=product.product_name,
                model_number=product.model_number,
                specification=product.specification,
                shipping_unit=product.shipping_unit,
                shipping_fee=product.shipping_fee,
                remarks=product.remarks,
                status=product.status,
                approver=product.approver,
                created_at=product.created_at,
                updated_at=product.updated_at
            )
            new_products.append((product, new_product))
        
        # 関連データを保存
        all_histories = []
        all_margins = []
        for old_product, new_product in new_products:
            histories = list(old_product.price_histories.all())
            margins = list(ProductGrossMarginRate.objects.filter(product=old_product))
            all_histories.extend([(h, new_product) for h in histories])
            all_margins.extend([(m, new_product) for m in margins])
        
        # 既存データを削除
        print("\n既存データを削除中...")
        ProductGrossMarginRate.objects.all().delete()
        PriceHistory.objects.all().delete()
        Product.objects.all().delete()
        
        # AUTO_INCREMENTをリセット
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='dashboard_products_master_product'")
        
        # 新しいデータを挿入
        print("新しいデータを作成中...")
        for old_product, new_product in new_products:
            # 強制的にpkを指定して保存
            new_product.pk = new_product.product_number
            new_product.save(force_insert=True)
            
            print(f"  作成: pk={new_product.pk}, product_number={new_product.product_number}")
            
        
        # 価格履歴をコピー
        print("\n価格履歴をコピー中...")
        for history, new_product in all_histories:
            PriceHistory.objects.create(
                product=new_product,
                period_year=history.period_year,
                effective_year_month=history.effective_year_month,
                gross_margin_rate=history.gross_margin_rate,
                wholesale_price=history.wholesale_price,
                kenren_price=history.kenren_price,
                retail_price=history.retail_price,
                revision_amount=history.revision_amount,
                revision_reason=history.revision_reason,
                is_active=history.is_active
            )
        
        # 粗利率テーブルをコピー
        print("粗利率テーブルをコピー中...")
        for margin, new_product in all_margins:
            ProductGrossMarginRate.objects.create(
                product=new_product,
                period_year=margin.period_year,
                gross_margin_rate=margin.gross_margin_rate
            )
        
        # 申請データのproduct_numberも修正
        print("\n申請データを修正中...")
        for approval in ProductApproval.objects.filter(product_number__gt=0):
            # product_numberが既存商品を指している場合、そのままでOK
            print(f"  申請データ: pk={approval.pk}, product_number={approval.product_number}")
        
        print("\n=== 修正完了 ===")
        
        # 結果確認
        print("修正後のデータ:")
        for product in Product.objects.all().order_by('pk'):
            print(f"  pk={product.pk}, product_number={product.product_number}, name={product.product_name}")
    
    # 外部キー制約を再有効化
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = ON")

if __name__ == "__main__":
    fix_pk_product_number()