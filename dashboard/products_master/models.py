from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import datetime

class ActiveProductManager(models.Manager):
    """有効な商品のみを取得するマネージャー"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class Product(models.Model):
    """商品マスタ"""
    product_number = models.IntegerField('商品番号', unique=True, null=True, blank=True, help_text='システム自動採番の商品番号')
    product_code = models.CharField('商品コード', max_length=50, blank=True, null=True, help_text='ユーザー管理用の商品コード')
    livestock_type = models.CharField('畜種', max_length=50)
    category = models.CharField('分類', max_length=100)
    manufacturer = models.CharField('メーカー', max_length=100)
    product_name = models.CharField('商品名', max_length=200)
    model_number = models.CharField('型式', max_length=100, blank=True, null=True)
    specification = models.CharField('規格', max_length=100, blank=True, null=True)
    shipping_unit = models.CharField('発送単位', max_length=50)
    shipping_fee = models.CharField('送料', max_length=100, blank=True, null=True)
    remarks = models.TextField('備考', blank=True, null=True)
    
    # 論理削除用フィールド
    is_active = models.BooleanField('有効', default=True, help_text='無効にすると論理削除されます')
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    # マネージャー
    objects = models.Manager()  # デフォルトマネージャー（全て）
    active_objects = ActiveProductManager()  # 有効な商品のみ
    
    class Meta:
        verbose_name = '商品マスタ'
        verbose_name_plural = '商品マスタ'
        ordering = ['product_number']
    
    def __str__(self):
        status = "" if self.is_active else "[削除済]"
        return f"{self.product_number}: {self.product_name} {status}"
    
    def soft_delete(self):
        """論理削除を実行"""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """論理削除を復元"""
        self.is_active = True
        self.deleted_at = None
        self.save()
    
    def save(self, *args, **kwargs):
        # 新規作成時に商品番号を自動採番
        if not self.pk and not self.product_number:
            last_product = Product.objects.order_by('-product_number').first()
            self.product_number = (last_product.product_number + 1) if last_product else 1
        super().save(*args, **kwargs)

class PriceHistory(models.Model):
    """価格改定履歴"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品', related_name='price_histories')
    period_year = models.IntegerField('年度', help_text='2025年度 = 2025/04～2026/03')
    effective_year_month = models.CharField('適用年月', max_length=7, help_text='YYYY/MM形式')  # 2025/03
    
    # 粗利率（年度ごと）
    gross_margin_rate = models.DecimalField('粗利率', max_digits=10, decimal_places=6, validators=[MinValueValidator(Decimal('0'))], help_text='前年度最終県連価格÷年度初め仕切価格（年度初めに1度計算、年度中は固定）')
    
    # 仕切価格（仕入価格）
    wholesale_price = models.CharField('仕切価格', max_length=50, help_text='メーカーからの仕入価格（"都度見積"等の文字列含む）')
    
    # 県連価格（販売価格）
    kenren_price = models.CharField('県連価格', max_length=50, blank=True, null=True, help_text='nullなら粗利率×仕切価格で自動計算、値があるならその値を表示（"都度見積"等の文字列含む）')
    
    # 参考小売価格（一般市場価格）
    retail_price = models.CharField('参考小売価格', max_length=50, blank=True, null=True, help_text='一般商流での参考価格（"オープン"等の文字列含む）')
    
    # 改定額（非使用：動的計算に変更）
    revision_amount = models.DecimalField('改定額', max_digits=12, decimal_places=0, default=0, help_text='非使用：get_revision_amount()で動的計算')
    
    # 改定理由
    revision_reason = models.TextField('改定理由', blank=True, null=True)
    
    # 論理削除用フィールド
    is_active = models.BooleanField('有効', default=True, help_text='無効にすると論理削除されます')
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '価格改定履歴'
        verbose_name_plural = '価格改定履歴'
        ordering = ['-effective_year_month', 'product__product_number']
        indexes = [
            models.Index(fields=['period_year', 'product']),
        ]
    
    def __str__(self):
        return f"{self.product.product_name} - {self.effective_year_month}"
    
    def get_revision_amount(self):
        """改定額を動的計算（表示用端数処理済み金額で計算）"""
        try:
            # 現在の県連価格を取得（表示用端数処理済み）
            current_kenren_price = self._get_display_kenren_price()
            if current_kenren_price is None:
                return 0
            
            # 前月の価格履歴を取得
            previous_history = PriceHistory.objects.filter(
                product=self.product,
                effective_year_month__lt=self.effective_year_month,
                is_active=True
            ).order_by('-effective_year_month').first()
            
            if previous_history:
                previous_kenren_price = previous_history._get_display_kenren_price()
                if previous_kenren_price is not None:
                    return int(current_kenren_price - previous_kenren_price)
            
            return 0
                
        except Exception:
            return 0
    
    def _get_display_kenren_price(self):
        """表示用の県連価格数値を取得（端数処理済み）"""
        try:
            # 県連価格が設定されている場合
            if self.kenren_price:
                return float(self.kenren_price.replace(',', ''))
            
            # 県連価格が未設定の場合は自動計算（端数処理済み）
            if self.wholesale_price and self.gross_margin_rate:
                wholesale_numeric = float(self.wholesale_price.replace(',', ''))
                calculated_price = wholesale_numeric * float(self.gross_margin_rate)
                return int(calculated_price)  # 小数点以下切り捨て
            
            return None
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _get_numeric_kenren_price(self):
        """県連価格の数値を取得（自動計算含む）"""
        try:
            # 県連価格が設定されている場合
            if self.kenren_price:
                return float(self.kenren_price.replace(',', ''))
            
            # 県連価格が未設定の場合は自動計算
            if self.wholesale_price and self.gross_margin_rate:
                wholesale_numeric = float(self.wholesale_price.replace(',', ''))
                return wholesale_numeric * float(self.gross_margin_rate)
            
            return None
        except (ValueError, TypeError, AttributeError):
            return None
    
    def is_editable(self):
        """編集可能かどうかを判定"""
        today = datetime.now().strftime('%Y/%m')
        
        # 未来の価格は編集可能
        if self.effective_year_month > today:
            return True
        
        # 過去の価格の場合、今日より前で最新のもののみ編集可能
        latest_past_history = PriceHistory.objects.filter(
            product=self.product,
            effective_year_month__lt=today,
            is_active=True
        ).order_by('-effective_year_month').first()
        
        return latest_past_history and latest_past_history.pk == self.pk
    
    def is_deletable(self):
        """削除可能かどうかを判定（編集条件と同じ）"""
        return self.is_editable()
    
    def get_kenren_price_display(self):
        """県連価格の表示用値を取得"""
        if self.kenren_price:
            return self.kenren_price
        
        # 自動計算
        try:
            if self.wholesale_price and self.gross_margin_rate:
                wholesale_numeric = float(self.wholesale_price.replace(',', ''))
                calculated_price = wholesale_numeric * float(self.gross_margin_rate)
                return f"{calculated_price:,.0f}"
        except (ValueError, TypeError, AttributeError):
            pass
        
        return "都度見積"
    
    def soft_delete(self):
        """論理削除を実行"""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

class ProductApproval(models.Model):
    """商品マスタ承認テーブル"""
    product_number = models.IntegerField('商品番号', help_text='システム自動採番の商品番号')
    product_code = models.CharField('商品コード', max_length=50, blank=True, null=True, help_text='ユーザー管理用の商品コード')
    livestock_type = models.CharField('畜種', max_length=50)
    category = models.CharField('分類', max_length=100)
    manufacturer = models.CharField('メーカー', max_length=100)
    product_name = models.CharField('商品名', max_length=200)
    model_number = models.CharField('型式', max_length=100, blank=True, null=True)
    specification = models.CharField('規格', max_length=100, blank=True, null=True)
    shipping_unit = models.CharField('発送単位', max_length=50)
    shipping_fee = models.CharField('送料', max_length=100, blank=True, null=True)
    remarks = models.TextField('備考', blank=True, null=True)
    
    is_active = models.BooleanField('有効', default=True)
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '商品マスタ承認'
        verbose_name_plural = '商品マスタ承認'
        ordering = ['product_number']
    
    def __str__(self):
        return f"{self.product_number}: {self.product_name}"

class PriceHistoryApproval(models.Model):
    """価格改定履歴承認テーブル"""
    product = models.ForeignKey(ProductApproval, on_delete=models.CASCADE, verbose_name='商品', related_name='price_histories')
    period_year = models.IntegerField('年度', help_text='2025年度 = 2025/04～2026/03')
    effective_year_month = models.CharField('適用年月', max_length=7, help_text='YYYY/MM形式')
    
    gross_margin_rate = models.DecimalField('粗利率', max_digits=10, decimal_places=6, validators=[MinValueValidator(Decimal('0'))])
    wholesale_price = models.CharField('仕切価格', max_length=50)
    kenren_price = models.CharField('県連価格', max_length=50, blank=True, null=True)
    retail_price = models.CharField('参考小売価格', max_length=50, blank=True, null=True)
    revision_amount = models.DecimalField('改定額', max_digits=12, decimal_places=0, default=0)
    revision_reason = models.TextField('改定理由', blank=True, null=True)
    
    is_active = models.BooleanField('有効', default=True)
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '価格改定履歴承認'
        verbose_name_plural = '価格改定履歴承認'
        ordering = ['-effective_year_month', 'product__product_number']
    
    def __str__(self):
        return f"{self.product.product_name} - {self.effective_year_month}"