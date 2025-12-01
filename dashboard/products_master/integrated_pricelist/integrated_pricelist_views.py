from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse
from dashboard.products_master.models import Product, PriceHistory
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs
from datetime import datetime, timedelta

def _initialize_sort_numbers(force_reset=False):
    """畜種・分類・メーカーごとにsort_numを初期化"""
    from django.db.models import Q
    
    if force_reset:
        # 強制リセット時は全商品を対象
        products_to_update = Product.objects.filter(
            is_active=True
        ).order_by('livestock_type', 'category', 'manufacturer', 'product_name')
    else:
        # 通常時はsort_numが0の商品のみ
        products_to_update = Product.objects.filter(
            Q(sort_num=0) | Q(sort_num__isnull=True),
            is_active=True
        ).order_by('livestock_type', 'category', 'manufacturer', 'product_name')
    
    if not products_to_update.exists():
        return
    
    # グループ別に連番を振る
    current_group = None
    sort_counter = 1
    
    for product in products_to_update:
        group_key = (product.livestock_type, product.category, product.manufacturer)
        
        if current_group != group_key:
            current_group = group_key
            sort_counter = 1
        
        product.sort_num = sort_counter
        product.save(update_fields=['sort_num'])
        sort_counter += 1

def integrated_pricelist(request):
    """統合価格表画面（全商品表示、価格なしはグレー）"""
    # デフォルトはシステム稼働日の翌月
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    default_month = next_month.strftime('%Y/%m')
    
    # 適用年月フィルター
    selected_month = request.GET.get('month', default_month)
    
    # HTML5 month入力からYYYY/MM形式に変換
    if selected_month and '-' in selected_month:
        selected_month = selected_month.replace('-', '/')
    
    # 適用年月一覧を取得（有効な商品のみ）
    available_months = PriceHistory.objects.filter(
        product__is_active=True, 
        is_active=True
    ).values_list('effective_year_month', flat=True).distinct().order_by('-effective_year_month')
    
    # sort_numが未設定の商品に初期値を設定
    _initialize_sort_numbers()
    
    # 全ての有効な商品を取得
    all_products = Product.objects.filter(is_active=True).order_by(
        'livestock_type', 'category', 'manufacturer', 'sort_num', 'product_name'
    )
    
    # 各商品に対して価格履歴を取得またはNoneを設定
    product_data = []
    previous_group = None
    
    for product in all_products:
        price_history = None
        
        if selected_month:
            # 指定年月以下で最新の価格履歴を取得
            price_history = PriceHistory.objects.filter(
                product=product,
                is_active=True,
                effective_year_month__lte=selected_month
            ).order_by('-effective_year_month').first()
        else:
            # 最新の価格履歴を取得
            price_history = PriceHistory.objects.filter(
                product=product,
                is_active=True
            ).order_by('-effective_year_month').first()
        
        # グループの境界を判定
        current_group = (product.livestock_type, product.category, product.manufacturer)
        is_group_start = previous_group != current_group
        previous_group = current_group
        
        # 商品と価格履歴のペアを作成
        product_data.append({
            'product': product,
            'price_history': price_history,
            'has_price': price_history is not None,
            'is_group_start': is_group_start
        })
    
    # ページネーション
    paginator = Paginator(product_data, 200)  # 200件ずつ表示
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'current_user': get_current_user(),
        'page_obj': page_obj,
        'available_months': available_months,
        'selected_month': selected_month,
        'breadcrumbs': get_breadcrumbs('integrated_pricelist')
    }
    return render(request, 'products_master/integrated_pricelist.html', context)

def update_sort_order(request):
    """ソート順序更新API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドが必要です'})
    
    try:
        import json
        from django.http import JsonResponse
        from django.db import transaction
        
        data = json.loads(request.body)
        updates = data.get('updates', [])
        
        if not updates:
            return JsonResponse({'success': False, 'message': '更新データがありません'})
        
        # 一括更新
        with transaction.atomic():
            for update in updates:
                product_id = update.get('product_id')
                sort_num = update.get('sort_num')
                
                if product_id and sort_num is not None:
                    Product.objects.filter(pk=product_id).update(sort_num=sort_num)
        
        return JsonResponse({'success': True, 'message': 'ソート順序を更新しました'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'})

def reset_sort_order(request):
    """ソート順序リセットAPI"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドが必要です'})
    
    try:
        from django.db import transaction
        
        # 全商品のsort_numを0にリセット
        with transaction.atomic():
            Product.objects.filter(is_active=True).update(sort_num=0)
        
        return JsonResponse({'success': True, 'message': 'ソート順序をリセットしました'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'})