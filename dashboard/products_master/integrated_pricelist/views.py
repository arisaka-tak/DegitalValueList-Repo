from django.shortcuts import render
from django.core.paginator import Paginator
from dashboard.products_master.models import Product, PriceHistory
from digital_pricelist_system.utils import get_current_user
from datetime import datetime, timedelta

def integrated_pricelist(request):
    """統合価格表画面（有効な商品のみ）"""
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
    
    # 指定年月時点で有効な価格履歴を取得
    if selected_month:
        # 各商品の指定年月以下で最新の価格履歴を取得
        from django.db.models import Max
        
        # 各商品の指定年月以下で最新の適用年月を取得
        latest_months = PriceHistory.objects.filter(
            product__is_active=True,
            is_active=True,
            effective_year_month__lte=selected_month
        ).values('product').annotate(
            latest_month=Max('effective_year_month')
        )
        
        # 最新の適用年月の価格履歴を取得
        price_histories = PriceHistory.objects.select_related('product').filter(
            product__is_active=True,
            is_active=True
        )
        
        # 各商品の最新価格履歴のみを絞り込み
        valid_histories = []
        for latest in latest_months:
            history = price_histories.filter(
                product_id=latest['product'],
                effective_year_month=latest['latest_month']
            ).first()
            if history:
                valid_histories.append(history.id)
        
        price_histories = price_histories.filter(id__in=valid_histories)
    else:
        # 指定がない場合は全ての有効な価格履歴を表示
        price_histories = PriceHistory.objects.select_related('product').filter(
            product__is_active=True,
            is_active=True
        )
    
    # 商品番号順でソート
    price_histories = price_histories.order_by('product__product_number', '-effective_year_month')
    
    # ページネーション
    paginator = Paginator(price_histories, 50)  # 50件ずつ表示
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'current_user': get_current_user(),
        'page_obj': page_obj,
        'available_months': available_months,
        'selected_month': selected_month,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': 'デジタル価格表', 'url': None}
        ]
    }
    return render(request, 'products_master/integrated_pricelist.html', context)