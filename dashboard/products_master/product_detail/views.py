from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from dashboard.products_master.models import Product, PriceHistory
from digital_pricelist_system.utils import get_current_user

def product_detail(request, pk):
    """商品詳細画面"""
    product = get_object_or_404(Product, pk=pk)
    price_histories = product.price_histories.filter(is_active=True).order_by('-effective_year_month')
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'price_histories': price_histories,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': f'{product.product_name}', 'url': None}
        ]
    }
    return render(request, 'products_master/product_detail.html', context)

@csrf_exempt
def price_history_update(request, pk):
    """価格履歴更新（HTMX）"""
    if request.method != 'POST':
        return HttpResponse('Invalid request', status=400)
    
    price_history = get_object_or_404(PriceHistory, pk=pk)
    
    if not price_history.is_editable():
        return HttpResponse('Not editable', status=400)
    
    try:
        field = request.POST.get('field')
        value = request.POST.get('value')
        
        if field == 'wholesale_price':
            price_history.wholesale_price = value if value else None
        elif field == 'kenren_price':
            price_history.kenren_price = value if value else None
        elif field == 'revision_reason':
            price_history.revision_reason = value if value else None
        
        price_history.save()
        
        # HTMX用に更新後の行を返す（改定額も含めて更新）
        html = render_to_string('products_master/partials/price_history_row.html', {
            'history': price_history
        })
        return HttpResponse(html)
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

@csrf_exempt
def price_history_delete(request, pk):
    """価格履歴削除"""
    if request.method != 'POST':
        return HttpResponse('Invalid request', status=400)
    
    price_history = get_object_or_404(PriceHistory, pk=pk)
    
    if not price_history.is_deletable():
        return HttpResponse('Not deletable', status=400)
    
    try:
        price_history.soft_delete()
        return HttpResponse('')  # HTMXは空のHTMLで行を削除
    except Exception:
        return HttpResponse('Error', status=500)

def price_history_create(request, product_pk):
    """価格履歴新規作成"""
    product = get_object_or_404(Product, pk=product_pk)
    
    if request.method == 'POST':
        try:
            effective_year_month = request.POST.get('effective_year_month', '').strip()
            wholesale_price = request.POST.get('wholesale_price', '').strip()
            kenren_price = request.POST.get('kenren_price', '').strip()
            revision_reason = request.POST.get('revision_reason', '').strip()
            
            if not effective_year_month:
                return HttpResponse('Missing effective_year_month', status=400)
            
            # 日付形式をバリデーション
            try:
                if '/' not in effective_year_month:
                    return HttpResponse('適用年月はYYYY/MM形式で入力してください', status=400)
                
                year_str, month_str = effective_year_month.split('/')
                year = int(year_str)
                month = int(month_str)
                
                if year < 2000 or year > 2099:
                    return HttpResponse('年は2000～2099の範囲で入力してください', status=400)
                
                if month < 1 or month > 12:
                    return HttpResponse('月は1～12の範囲で入力してください', status=400)
                
                # 正しい形式に整形
                effective_year_month = f"{year:04d}/{month:02d}"
                
            except ValueError:
                return HttpResponse('適用年月はYYYY/MM形式で入力してください', status=400)
            
            if not wholesale_price:
                wholesale_price = '都度見積'
            
            # 年度を自動算出
            period_year = year if month >= 4 else year - 1
            
            # 重複チェック
            if PriceHistory.objects.filter(product=product, effective_year_month=effective_year_month, is_active=True).exists():
                return HttpResponse(f'{effective_year_month}の価格履歴は既に存在します', status=400)
            
            price_history = PriceHistory.objects.create(
                product=product,
                period_year=period_year,
                effective_year_month=effective_year_month,
                wholesale_price=wholesale_price,
                kenren_price=kenren_price if kenren_price else None,
                revision_reason=revision_reason if revision_reason else None,
                gross_margin_rate=1.1,
                revision_amount=0
            )
            return HttpResponse('Created successfully')
            
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}', status=500)
    
    return HttpResponse('Invalid method', status=405)