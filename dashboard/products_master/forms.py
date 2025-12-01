from django import forms
from django.forms import inlineformset_factory
from .models import Product, PriceHistory

class ProductForm(forms.ModelForm):
    """商品マスタフォーム"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # None値を空文字列に変換（既存インスタンスのみ）
        if self.instance and self.instance.pk:
            for field_name, field in self.fields.items():
                if hasattr(self.instance, field_name):
                    value = getattr(self.instance, field_name)
                    if value is None:
                        self.initial[field_name] = ''
    
    def clean_product_code(self):
        product_code = self.cleaned_data.get('product_code') or ''
        product_code = product_code.strip() if product_code else ''
        if product_code and (len(product_code) != 9 or not product_code.isdigit()):
            raise forms.ValidationError('商品コードは9桁の数字で入力してください。')
        return product_code
    
    class Meta:
        model = Product
        fields = [
            'product_code', 'livestock_type', 'category', 'manufacturer',
            'product_name', 'model_number', 'specification', 'shipping_unit',
            'shipping_fee', 'remarks'
        ]
        widgets = {
            'product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9桁の数字または空欄'}),
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

class PDFUploadForm(forms.Form):
    """PDFアップロード用フォーム"""
    pdf_file = forms.FileField(
        label='PDFファイル',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf',
            'id': 'pdf-file-input'
        }),
        help_text='価格表やカタログのPDFファイルをアップロードしてください（最大10MB）'
    )
    transaction_name = forms.CharField(
        label='処理名',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例：2024年12月価格表'
        }),
        help_text='この処理を識別するための名前を入力してください'
    )
    
    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            # ファイルサイズチェック（10MB制限）
            if pdf_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは10MB以下にしてください。')
            
            # ファイル形式チェック
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('PDFファイルのみアップロード可能です。')
        
        return pdf_file