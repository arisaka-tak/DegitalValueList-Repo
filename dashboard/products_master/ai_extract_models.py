from django.db import models
from dashboard.products_master.models import Product, ProductApproval
import os

def ai_extract_pdf_upload_path(instance, filename):
    """トランザクションIDを付けたユニークなファイル名を生成"""
    name, ext = os.path.splitext(filename)
    return f'ai_price_extract/{instance.transaction_id}_{filename}'

class AIExtractTransaction(models.Model):
    """AI価格抽出トランザクション履歴"""
    transaction_id = models.CharField('トランザクションID', max_length=50, unique=True)
    executor = models.CharField('実行者', max_length=100)
    effective_year_month = models.CharField('適用年月', max_length=7)
    revision_reason = models.TextField('改定理由', blank=True, null=True)
    remarks = models.CharField('備考', max_length=200, blank=True, null=True, help_text='処理名やメモ')
    uploaded_pdf = models.FileField('アップロードPDF', upload_to=ai_extract_pdf_upload_path, blank=True, null=True)
    total_products = models.IntegerField('対象商品数', default=0)
    success_count = models.IntegerField('成功件数', default=0)
    skip_count = models.IntegerField('スキップ件数', default=0)
    status = models.CharField('ステータス', max_length=20, default='完了')
    is_active = models.BooleanField('有効', default=True)
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    created_at = models.DateTimeField('実行日時', auto_now_add=True)
    
    class Meta:
        verbose_name = 'AI価格抽出トランザクション'
        ordering = ['-created_at']
    
    def soft_delete(self):
        """論理削除を実行し、3カ月経過した古いデータを物理削除"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()
        
        # 3カ月経過した論理削除済みデータを物理削除
        three_months_ago = timezone.now() - timedelta(days=90)
        old_transactions = AIExtractTransaction.objects.filter(
            is_active=False,
            deleted_at__lt=three_months_ago
        )
        deleted_count = old_transactions.count()
        if deleted_count > 0:
            old_transactions.delete()
            print(f'物理削除: {deleted_count}件のAI抽出トランザクションを削除しました')
    
    def __str__(self):
        return f"{self.transaction_id} - {self.executor}"

class AIExtractTransactionDetail(models.Model):
    """AI価格抽出トランザクション明細"""
    transaction = models.ForeignKey(AIExtractTransaction, on_delete=models.CASCADE, related_name='details')
    sequence = models.IntegerField('連番')
    extracted_product_name = models.CharField('AI抽出商品名', max_length=200, blank=True, null=True)
    extracted_model_number = models.CharField('AI抽出型式', max_length=100, blank=True, null=True)
    extracted_manufacturer = models.CharField('AI抽出メーカー', max_length=100, blank=True, null=True)
    extracted_specification = models.CharField('AI抽出規格', max_length=100, blank=True, null=True)
    extracted_price = models.CharField('AI抽出価格', max_length=50, blank=True, null=True)
    extracted_revision_reason = models.CharField('AI抽出改定理由', max_length=200, blank=True, null=True)
    matched_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    match_score = models.IntegerField('一致率', null=True, blank=True)
    selected_candidate_text = models.CharField('選択した候補表示文字列', max_length=300, blank=True, null=True)
    status = models.CharField('処理結果', max_length=20)
    error_message = models.TextField('エラーメッセージ', blank=True, null=True)
    created_approval = models.ForeignKey(ProductApproval, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = 'AI価格抽出トランザクション明細'
        ordering = ['sequence']
    
    def __str__(self):
        return f"{self.transaction.transaction_id} - {self.sequence}"