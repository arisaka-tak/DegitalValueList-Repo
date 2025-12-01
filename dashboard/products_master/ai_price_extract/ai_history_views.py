from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from dashboard.products_master.ai_extract_models import AIExtractTransaction, AIExtractTransactionDetail
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

def ai_extract_history(request):
    """AI価格抽出履歴一覧"""
    transactions = AIExtractTransaction.objects.filter(is_active=True).order_by('-created_at')
    
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('ai_extract_history'),
        'transactions': transactions
    }
    return render(request, 'products_master/ai_extract_history.html', context)

def ai_extract_history_detail(request, pk):
    """AI価格抽出履歴詳細（照合結果画面を再現）"""
    transaction = get_object_or_404(AIExtractTransaction, pk=pk)
    details = transaction.details.all().order_by('sequence')
    
    # 照合結果を再構成
    results = {
        'status': 'success',
        'total_products': transaction.total_products,
        'results': []
    }
    
    for detail in details:
        result_data = {
            'index': detail.sequence - 1,
            'status': 'success' if detail.matched_product else 'no_match',
            'extracted_data': {
                'product_name': detail.extracted_product_name,
                'model_number': detail.extracted_model_number,
                'manufacturer': detail.extracted_manufacturer,
                'specification': detail.extracted_specification,
                'new_price': detail.extracted_price,
                'revision_reason': detail.extracted_revision_reason  # 改定理由を追加
            },
            'candidates': []
        }
        
        if detail.matched_product:
            result_data['candidates'] = [{
                'product': {
                    'pk': detail.matched_product.pk,
                    'product_name': detail.matched_product.product_name,
                    'model_number': detail.matched_product.model_number,
                    'specification': detail.matched_product.specification,
                    'manufacturer': detail.matched_product.manufacturer,
                    'product_number': detail.matched_product.product_number,
                },
                'score': detail.match_score or 0,
                'display_info': f"{detail.matched_product.product_name} | {detail.matched_product.model_number or '-'} | {detail.matched_product.specification or '-'}",
                'manufacturer': detail.matched_product.manufacturer or '-',
                'product_number': detail.matched_product.product_number,
            }]
        
        results['results'].append(result_data)
    
    # POSTリクエストの場合は既存の申請処理を使用
    if request.method == 'POST':
        from dashboard.products_master.ai_price_extract.ai_price_extract_views import _process_ai_extract_submission
        # セッションにトランザクションIDを設定
        request.session['ai_extract_transaction_id'] = transaction.transaction_id
        # 再構成した結果で呼び出し
        return _process_ai_extract_submission(request, results, {})
    
    # 再編集可能かどうかを判定
    can_edit = any(detail.status in ['未処理', 'エラー'] for detail in details)
    
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('ai_extract_history_detail'),
        'results': results,
        'transaction': transaction,
        'details': details,
        'is_history_view': True,
        'can_edit': can_edit
    }
    return render(request, 'products_master/ai_extract_results.html', context)

def ai_extract_history_delete(request, pk):
    """AI価格抽出履歴削除"""
    transaction = get_object_or_404(AIExtractTransaction, pk=pk)
    
    if request.method == 'POST':
        transaction_id = transaction.transaction_id
        transaction.soft_delete()  # 論理削除を実行（古いデータの物理削除も自動実行）
        messages.success(request, f'トランザクション「{transaction_id}」を削除しました。')
        return redirect('products_master:ai_extract')
    
    return redirect('products_master:ai_extract')