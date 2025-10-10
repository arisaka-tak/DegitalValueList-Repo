from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from dashboard.products_master.models import Product
import os
import socket
import getpass

class ChangeRequest(models.Model):
    """変更申請"""
    
    REQUEST_TYPE_CHOICES = [
        ('CREATE', '新規作成'),
        ('UPDATE', '更新'),
        ('DELETE', '削除'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '申請中'),
        ('APPROVED', '承認済み'),
        ('REJECTED', '却下'),
        ('CANCELLED', '取り消し'),
    ]
    
    # 申請情報
    request_type = models.CharField('申請種別', max_length=10, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField('ステータス', max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # 申請者・承認者（username@hostname形式）
    requester = models.CharField('申請者', max_length=100, help_text='username@hostname形式')
    approver = models.CharField('承認者', max_length=100, null=True, blank=True, help_text='username@hostname形式')
    
    # 対象商品（更新・削除の場合）
    target_product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='対象商品', null=True, blank=True)
    
    # 申請内容（JSON形式で変更前後のデータを保存）
    request_data = models.JSONField('申請データ', help_text='変更内容をJSON形式で保存')
    
    # AI抽出関連
    source_pdf = models.FileField('元PDFファイル', upload_to='pdfs/', null=True, blank=True)
    ai_extracted = models.BooleanField('AI抽出', default=False)
    
    # 日時
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    
    # コメント
    request_comment = models.TextField('申請コメント', blank=True, null=True)
    approval_comment = models.TextField('承認コメント', blank=True, null=True)
    
    class Meta:
        verbose_name = '変更申請'
        verbose_name_plural = '変更申請'
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.get_request_type_display()} - {self.requester} - {self.requested_at.strftime('%Y/%m/%d')}"
    
    @classmethod
    def get_current_user(cls):
        """現在のOSユーザとホスト名を取得"""
        try:
            username = getpass.getuser()
            hostname = socket.gethostname()
            return f"{username}@{hostname}"
        except Exception:
            return "unknown@unknown"

class ApprovalHistory(models.Model):
    """承認履歴"""
    
    ACTION_CHOICES = [
        ('APPROVE', '承認'),
        ('REJECT', '却下'),
        ('REQUEST_CHANGE', '修正依頼'),
    ]
    
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, verbose_name='変更申請', related_name='approval_histories')
    approver = models.CharField('承認者', max_length=100, help_text='username@hostname形式')
    action = models.CharField('アクション', max_length=20, choices=ACTION_CHOICES)
    comment = models.TextField('コメント', blank=True, null=True)
    processed_at = models.DateTimeField('処理日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '承認履歴'
        verbose_name_plural = '承認履歴'
        ordering = ['-processed_at']
    
    def __str__(self):
        return f"{self.change_request} - {self.get_action_display()}"