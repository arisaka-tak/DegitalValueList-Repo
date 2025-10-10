from django import forms
from django.forms import inlineformset_factory
from .models import Product, PriceHistory

class ProductForm(forms.ModelForm):
    """商品マスタフォーム"""
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # 新規作成時のみ商品番号を自動採番（編集時は変更しない）
        if not instance.pk and not instance.product_number:
            last_product = Product.objects.order_by('-product_number').first()
            instance.product_number = (last_product.product_number + 1) if last_product else 1
        
        if commit:
            instance.save()
        return instance
    
    class Meta:
        model = Product
        fields = [
            'product_code', 'livestock_type', 'category', 'manufacturer',
            'product_name', 'model_number', 'specification', 'shipping_unit',
            'shipping_fee', 'remarks'
        ]
        widgets = {
            'product_code': forms.TextInput(attrs={'class': 'form-control'}),
            'livestock_type': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control'}),
            'specification': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_fee': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PriceHistoryForm(forms.ModelForm):
    """価格改定履歴フォーム"""
    
    class Meta:
        model = PriceHistory
        fields = [
            'period_year', 'effective_year_month',
            'gross_margin_rate', 'wholesale_price', 'kenren_price',
            'retail_price', 'revision_amount', 'revision_reason'
        ]
        widgets = {
            'period_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2030}),
            'effective_year_month': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY/MM'}),
            'gross_margin_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'wholesale_price': forms.TextInput(attrs={'class': 'form-control'}),
            'kenren_price': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '空欄で自動計算'}),
            'retail_price': forms.TextInput(attrs={'class': 'form-control'}),
            'revision_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'revision_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

# インラインフォームセット（商品に紐づく価格履歴を複数編集）
PriceHistoryFormSet = inlineformset_factory(
    Product, 
    PriceHistory,
    form=PriceHistoryForm,
    extra=1,  # 新規追加用の空フォームを1つ表示
    can_delete=True,  # 削除可能
    can_order=False
)