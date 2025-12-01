from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from dashboard.products_master.models import Product
from dashboard.products_master.product_services import regenerate_all_product_keywords
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

def product_list(request):
    """商品一覧画面（有効な商品のみ）"""
    search_query = request.GET.get('search', '')
    
    products = Product.active_objects.all()
    
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(product_code__icontains=search_query)
        )
    
    products = products.order_by('pk')
    
    # ページネーション
    paginator = Paginator(products, 20)  # 20件ずつ表示
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'current_user': get_current_user(),
        'page_obj': page_obj,
        'search_query': search_query,
        'breadcrumbs': get_breadcrumbs('product_list')
    }
    return render(request, 'products_master/product_list.html', context)

def regenerate_keywords_batch(request):
    """キーワード一括再生成実行"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        result = regenerate_all_product_keywords()
        return JsonResponse({
            'success': True,
            'message': f"キーワード再生成完了: {result['processed_count']}/{result['total_count']}件",
            'result': result
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'エラーが発生しました: {str(e)}'
        }, status=500)