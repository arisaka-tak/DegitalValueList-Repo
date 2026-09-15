from django.core.management.base import BaseCommand
from dashboard.products_master.models import Product, PriceHistory, LivestockType, Category, Manufacturer
from decimal import Decimal
from digital_pricelist_system.gross_margin_utils import calculate_gross_margin_rate
import random

class Command(BaseCommand):
    help = '商品マスタとテストデータを作成'

    def handle(self, *args, **options):
        # 既存データを削除
        self.stdout.write('既存データを削除中...')
        PriceHistory.objects.all().delete()
        Product.objects.all().delete()
        
        # マスタデータを取得
        livestock_types = list(LivestockType.objects.filter(is_active=True))
        categories = list(Category.objects.filter(is_active=True))
        manufacturers = list(Manufacturer.objects.filter(is_active=True)[:20])  # 20社に限定
        
        if not livestock_types or not categories or not manufacturers:
            self.stdout.write(self.style.ERROR('マスタデータが不足しています'))
            return
        
        # テスト商品データ
        test_products = [
            {'name': '牛用配合飼料A', 'code': '100000001'},
            {'name': '豚用配合飼料B', 'code': '100000002'},
            {'name': '鶏用配合飼料C', 'code': '100000003'},
            {'name': '子牛用ミルク', 'code': '100000004'},
            {'name': '肥育牛用飼料', 'code': '100000005'},
            {'name': '乳牛用飼料', 'code': '100000006'},
            {'name': '豚用スターター', 'code': '100000007'},
            {'name': '豚用フィニッシャー', 'code': '100000008'},
            {'name': '採卵鶏用飼料', 'code': '100000009'},
            {'name': 'ブロイラー用飼料', 'code': '100000010'},
            {'name': '牛用サプリメント', 'code': '100000011'},
            {'name': '豚用サプリメント', 'code': '100000012'},
            {'name': '鶏用サプリメント', 'code': '100000013'},
            {'name': '牛用ビタミン剤', 'code': '100000014'},
            {'name': '豚用ビタミン剤', 'code': '100000015'},
            {'name': '鶏用ビタミン剤', 'code': '100000016'},
            {'name': '牛用ミネラル', 'code': '100000017'},
            {'name': '豚用ミネラル', 'code': '100000018'},
            {'name': '鶏用ミネラル', 'code': '100000019'},
            {'name': '牛用抗生物質', 'code': '100000020'},
            {'name': '豚用抗生物質', 'code': '100000021'},
            {'name': '鶏用抗生物質', 'code': '100000022'},
            {'name': '牛用ワクチン', 'code': '100000023'},
            {'name': '豚用ワクチン', 'code': '100000024'},
            {'name': '鶏用ワクチン', 'code': '100000025'},
            {'name': '牛用消毒薬', 'code': '100000026'},
            {'name': '豚用消毒薬', 'code': '100000027'},
            {'name': '鶏用消毒薬', 'code': '100000028'},
            {'name': '牛舎用清掃剤', 'code': '100000029'},
            {'name': '豚舎用清掃剤', 'code': '100000030'},
            {'name': '鶏舎用清掃剤', 'code': '100000031'},
            {'name': '牛用飼料添加物', 'code': '100000032'},
            {'name': '豚用飼料添加物', 'code': '100000033'},
            {'name': '鶏用飼料添加物', 'code': '100000034'},
            {'name': '牛用プロバイオティクス', 'code': '100000035'},
            {'name': '豚用プロバイオティクス', 'code': '100000036'},
            {'name': '鶏用プロバイオティクス', 'code': '100000037'},
            {'name': '牛用酵素剤', 'code': '100000038'},
            {'name': '豚用酵素剤', 'code': '100000039'},
            {'name': '鶏用酵素剤', 'code': '100000040'},
            {'name': '牛用有機酸', 'code': '100000041'},
            {'name': '豚用有機酸', 'code': '100000042'},
            {'name': '鶏用有機酸', 'code': '100000043'},
            {'name': '牛用アミノ酸', 'code': '100000044'},
            {'name': '豚用アミノ酸', 'code': '100000045'},
            {'name': '鶏用アミノ酸', 'code': '100000046'},
            {'name': '牛用脂肪酸', 'code': '100000047'},
            {'name': '豚用脂肪酸', 'code': '100000048'},
            {'name': '鶏用脂肪酸', 'code': '100000049'},
            {'name': '畜産用機器メンテナンス', 'code': '100000050'},
        ]
        
        self.stdout.write('テストデータを作成中...')
        
        for i, product_data in enumerate(test_products, 1):
            # 商品作成
            product = Product.objects.create(
                product_code=product_data['code'],
                livestock_type=random.choice(livestock_types),
                category=random.choice(categories),
                manufacturer=random.choice(manufacturers),
                product_name=product_data['name'],
                model_number=f'MODEL-{i:03d}',
                specification=f'{random.randint(10, 50)}kg袋',
                shipping_unit='1袋',
                shipping_fee='別途',
                remarks=f'テスト商品{i}の備考',
                sort_num=i
            )
            
            # 価格履歴作成（2-3件）
            base_price = random.randint(5000, 50000)
            history_count = random.randint(2, 3)
            
            for j in range(history_count):
                year_month = f'2025/{j+1:02d}'
                period_year = 2024 if j+1 < 4 else 2025
                
                wholesale_price = base_price + (j * random.randint(-1000, 2000))
                
                if j == 0:  # 1件目は必ず仕切価格と県連価格を設定
                    kenren_price = int(wholesale_price * random.uniform(1.05, 1.25))  # 5-25%の粗利
                    # 共通関数で粗利率を算出
                    gross_margin_rate = calculate_gross_margin_rate(wholesale_price, kenren_price)
                    if gross_margin_rate is None:
                        gross_margin_rate = Decimal('0.90')  # デフォルト値
                    kenren_price_str = str(kenren_price)
                else:
                    # 2件目以降は自動計算
                    gross_margin_rate = Decimal('0.90')
                    kenren_price_str = None
                
                PriceHistory.objects.create(
                    product=product,
                    period_year=period_year,
                    effective_year_month=year_month,
                    gross_margin_rate=gross_margin_rate,
                    wholesale_price=str(wholesale_price),
                    kenren_price=kenren_price_str,
                    retail_price=str(int(wholesale_price * 1.3)) if random.choice([True, False]) else None,
                    revision_amount=0,
                    revision_reason='テストデータ' if j > 0 else None
                )
        
        self.stdout.write(self.style.SUCCESS(f'テストデータ作成完了: {len(test_products)}件の商品'))