from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from dashboard.products_master.ai_extract_models import AIExtractTransaction


class Command(BaseCommand):
    help = '論理削除から3カ月経過したAI抽出トランザクションを物理削除'

    def handle(self, *args, **options):
        # 3カ月前の日時を計算
        three_months_ago = timezone.now() - timedelta(days=90)
        
        # 論理削除から3カ月経過したトランザクションを取得
        old_transactions = AIExtractTransaction.objects.filter(
            is_active=False,
            deleted_at__lt=three_months_ago
        )
        
        count = old_transactions.count()
        if count > 0:
            # 物理削除実行
            old_transactions.delete()
            self.stdout.write(
                self.style.SUCCESS(f'{count}件のAI抽出トランザクションを物理削除しました')
            )
        else:
            self.stdout.write('削除対象のトランザクションはありません')