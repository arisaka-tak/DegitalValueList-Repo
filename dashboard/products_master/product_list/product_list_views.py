from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from dashboard.products_master.models import Product
from dashboard.products_master.product_services import regenerate_all_product_keywords
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

def product_list(request):
    """商品一覧画面"""
    search_query = request.GET.get('search', '')
    show_deleted = request.GET.get('show_deleted', 'false') == 'true'
    
    if show_deleted:
        products = Product.objects.filter(is_active=False)
    else:
        products = Product.active_objects.all()
    
    if search_query:
        from dashboard.products_master.ai_services import normalize_text
        
        # 検索クエリを正規化（全角・半角統一）
        normalized_query = normalize_text(search_query)
        
        products = products.filter(
            Q(product_name__icontains=normalized_query) |
            Q(manufacturer__name__icontains=normalized_query) |
            Q(product_code__icontains=normalized_query)
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
        'show_deleted': show_deleted,
        'breadcrumbs': get_breadcrumbs('product_list')
    }
    return render(request, 'products_master/product_list.html', context)

def toggle_product_status(request, pk):
    """商品の削除・復元申請作成"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    product = get_object_or_404(Product, pk=pk)
    
    # 申請中チェック
    if product.status:
        return JsonResponse({'error': 'この商品は既に申請中です'}, status=400)
    
    from dashboard.products_master.models import ProductApproval
    from digital_pricelist_system.utils import get_current_user
    
    # 申請テーブルにコピー
    approval = ProductApproval.objects.create(
        product_number=product.pk,
        product_code=product.product_code,
        livestock_type=product.livestock_type.id if product.livestock_type else None,
        category=product.category.id if product.category else None,
        manufacturer=product.manufacturer.id if product.manufacturer else None,
        product_name=product.product_name,
        model_number=product.model_number,
        specification=product.specification,
        shipping_unit=product.shipping_unit,
        shipping_fee=product.shipping_fee,
        remarks=product.remarks,
        status='削除申請' if product.is_active else '復元申請',
        applicant=get_current_user()
    )
    
    # 価格履歴も申請テーブルにコピー
    from dashboard.products_master.models import PriceHistoryApproval
    for history in product.price_histories.filter(is_active=True):
        PriceHistoryApproval.objects.create(
            product=approval,
            period_year=history.period_year,
            effective_year_month=history.effective_year_month,
            gross_margin_rate=history.gross_margin_rate,
            wholesale_price=history.wholesale_price,
            kenren_price=history.kenren_price,
            retail_price=history.retail_price,
            revision_amount=history.revision_amount,
            revision_reason=history.revision_reason,
            memo=history.memo,
            applicant=get_current_user()
        )
    
    # 商品マスタのステータスを申請中に変更
    product.status = '申請中'
    product.save()
    
    action = '削除' if product.is_active else '復元'
    message = f'商品「{product.product_name}」の{action}申請を作成しました'
    
    return JsonResponse({
        'success': True,
        'message': message
    })

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