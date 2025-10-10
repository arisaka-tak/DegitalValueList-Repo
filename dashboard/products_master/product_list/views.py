from django.shortcuts import render
from django.core.paginator import Paginator
from dashboard.products_master.models import Product
from digital_pricelist_system.utils import get_current_user

def product_list(request):
    """商品一覧画面（有効な商品のみ）"""
    products = Product.active_objects.all().order_by('product_number')
    
    # ページネーション
    paginator = Paginator(products, 20)  # 20件ずつ表示
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'current_user': get_current_user(),
        'page_obj': page_obj,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': None}
        ]
    }
    return render(request, 'products_master/product_list.html', context)