"""
商品マスタキーワード一括再生成バッチ処理
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from dashboard.products_master.product_services import regenerate_all_product_keywords
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs


def keyword_batch_menu(request):
    """キーワード一括再生成メニュー画面"""
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('keyword_batch_menu')
    }
    return render(request, 'products_master/keyword_batch_menu.html', context)


def keyword_batch_execute(request):
    """キーワード一括再生成実行"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        # バッチ処理実行
        result = regenerate_all_product_keywords()
        
        # 結果メッセージ
        success_message = f"キーワード再生成完了: {result['processed_count']}/{result['total_count']}件 (成功率: {result['success_rate']:.1f}%)"
        messages.success(request, success_message)
        
        return JsonResponse({
            'success': True,
            'message': success_message,
            'result': result
        })
        
    except Exception as e:
        error_message = f'バッチ処理中にエラーが発生しました: {str(e)}'
        messages.error(request, error_message)
        
        return JsonResponse({
            'success': False,
            'error': error_message
        }, status=500)