from django.shortcuts import render
from django.core.paginator import Paginator
from dashboard.products_master.models import Product, PriceHistory
from digital_pricelist_system.utils import get_current_user

def integrated_pricelist(request):
    """統合価格表画面（有効な商品のみ）"""
    # 年度フィルター
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    
    # 年度一覧を取得（有効な商品のみ）
    available_years = PriceHistory.objects.filter(product__is_active=True).values_list('period_year', flat=True).distinct().order_by('-period_year')
    
    # 月一覧を取得（有効な商品のみ）
    available_months = PriceHistory.objects.filter(product__is_active=True).values_list('effective_year_month', flat=True).distinct().order_by('-effective_year_month')
    
    # フィルター適用（有効な商品のみ）
    price_histories = PriceHistory.objects.select_related('product').filter(product__is_active=True)
    
    if selected_year:
        price_histories = price_histories.filter(period_year=selected_year)
    if selected_month:
        price_histories = price_histories.filter(effective_year_month=selected_month)
    
    # 商品番号順でソート
    price_histories = price_histories.order_by('product__product_number', '-effective_year_month')
    
    # ページネーション
    paginator = Paginator(price_histories, 50)  # 50件ずつ表示
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'current_user': get_current_user(),
        'page_obj': page_obj,
        'available_years': available_years,
        'available_months': available_months,
        'selected_year': int(selected_year) if selected_year else None,
        'selected_month': selected_month,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '統合価格表', 'url': None}
        ]
    }
    return render(request, 'products_master/integrated_pricelist.html', context)