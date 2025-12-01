from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from dashboard.products_master.ai_extract_models import AIExtractTransaction, AIExtractTransactionDetail
from dashboard.products_master.models import Product
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
    """AI価格抽出履歴詳細（データベースの値のみ使用）"""
    transaction = get_object_or_404(AIExtractTransaction, pk=pk)
    
    # データベースから最新の明細データを取得し、ロックされていないデータを再照合
    def get_fresh_results():
        from dashboard.products_master.ai_services import process_extraction_results
        
        fresh_details = transaction.details.all().order_by('sequence')
        results = {
            'status': 'success',
            'total_products': transaction.total_products,
            'results': []
        }
        
        for detail in fresh_details:
            # ロックされていないデータは再照合
            if detail.status not in ['スキップ', '申請済']:
                extracted_data = {
                    'product_name': detail.extracted_product_name,
                    'model_number': detail.extracted_model_number,
                    'manufacturer': detail.extracted_manufacturer,
                    'specification': detail.extracted_specification
                }
                
                # 再照合実行
                json_data = {'products': [extracted_data]}
                rematch_results = process_extraction_results(json_data)
                
                if rematch_results and 'results' in rematch_results and rematch_results['results']:
                    rematch_result = rematch_results['results'][0]
                    candidates = rematch_result.get('candidates', [])
                    
                    # 最高スコアの候補で更新
                    if candidates:
                        best_candidate = candidates[0]
                        matched_product_id = best_candidate.get('product', {}).get('pk')
                        if matched_product_id:
                            try:
                                matched_product = Product.objects.get(pk=matched_product_id)
                                detail.matched_product = matched_product
                                detail.match_score = best_candidate.get('score', 0)
                                detail.save()
                            except Product.DoesNotExist:
                                pass
            
            result_data = {
                'index': detail.sequence - 1,
                'status': 'success' if detail.matched_product else 'no_match',
                'extracted_data': {
                    'product_name': detail.extracted_product_name or '',
                    'model_number': detail.extracted_model_number or '',
                    'manufacturer': detail.extracted_manufacturer or '',
                    'specification': detail.extracted_specification or '',
                    'new_price': detail.extracted_price or '',
                    'revision_reason': detail.extracted_revision_reason or ''
                },
                'candidates': []
            }
            
            if detail.matched_product:
                # 現在の仕切価格を取得
                from datetime import datetime
                today = datetime.now().strftime('%Y/%m')
                current_price_history = detail.matched_product.price_histories.filter(
                    effective_year_month__lte=today,
                    is_active=True
                ).order_by('-effective_year_month').first()
                
                current_wholesale_price = '-'
                if current_price_history:
                    current_wholesale_price = current_price_history.wholesale_price or '-'
                
                result_data['candidates'] = [{
                    'product': {
                        'pk': detail.matched_product.pk,
                        'product_name': detail.matched_product.product_name,
                        'model_number': detail.matched_product.model_number,
                        'specification': detail.matched_product.specification,
                        'manufacturer': detail.matched_product.manufacturer,
                        'current_wholesale_price': current_wholesale_price,
                    },
                    'score': detail.match_score or 0,
                    'display_info': f"{detail.matched_product.product_name} | {detail.matched_product.model_number or '-'} | {detail.matched_product.specification or '-'}",
                    'manufacturer': detail.matched_product.manufacturer or '-',
                }]
            
            results['results'].append(result_data)
        
        return results, fresh_details
    
    # 最新のデータを取得
    results, details = get_fresh_results()
    
    # POSTリクエストの場合は既存の申請処理を使用
    if request.method == 'POST':
        from dashboard.products_master.ai_price_extract.ai_price_extract_views import _process_ai_extract_submission
        # セッションにトランザクションIDを設定
        request.session['ai_extract_transaction_id'] = transaction.transaction_id
        
        # 申請処理前にフォームデータをデータベースに保存
        _save_form_data_to_database(request, transaction)
        
        # 保存後に最新のデータベース値を取得（フォームデータ反映済み）
        fresh_results, _ = get_fresh_results()
        
        # 最新データで申請処理を呼び出し
        return _process_ai_extract_submission(request, fresh_results, {})
    
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

def _save_form_data_to_database(request, transaction):
    """フォームデータをデータベースに保存"""
    try:
        print(f"Debug: Saving form data for transaction {transaction.pk}")
        # 各明細のフォームデータを取得して保存
        details = transaction.details.all().order_by('sequence')
        
        for detail in details:
            index = detail.sequence - 1
            print(f"Debug: Processing detail {detail.sequence} (index {index})")
            
            # 新価格を更新
            new_price = request.POST.get(f'new_price_{index}')
            print(f"Debug: new_price_{index} = {new_price}")
            if new_price is not None:
                old_price = detail.extracted_price
                detail.extracted_price = str(new_price)
                print(f"Debug: Updated price from '{old_price}' to '{detail.extracted_price}'")
            
            # 改定理由を更新
            revision_reason = request.POST.get(f'revision_reason_{index}')
            print(f"Debug: revision_reason_{index} = {revision_reason}")
            if revision_reason is not None:
                old_reason = detail.extracted_revision_reason
                detail.extracted_revision_reason = str(revision_reason)
                print(f"Debug: Updated reason from '{old_reason}' to '{detail.extracted_revision_reason}'")
            
            # 商品名、型式、規格、メーカーを更新（編集モードの値をフォームから取得）
            extracted_product_name = request.POST.get(f'extracted_product_name_{index}')
            if extracted_product_name is not None:
                old_name = detail.extracted_product_name
                detail.extracted_product_name = str(extracted_product_name)
                print(f"Debug: Updated product_name from '{old_name}' to '{detail.extracted_product_name}'")
            
            extracted_model_number = request.POST.get(f'extracted_model_number_{index}')
            if extracted_model_number is not None:
                old_model = detail.extracted_model_number
                detail.extracted_model_number = str(extracted_model_number)
                print(f"Debug: Updated model_number from '{old_model}' to '{detail.extracted_model_number}'")
            
            extracted_specification = request.POST.get(f'extracted_specification_{index}')
            if extracted_specification is not None:
                old_spec = detail.extracted_specification
                detail.extracted_specification = str(extracted_specification)
                print(f"Debug: Updated specification from '{old_spec}' to '{detail.extracted_specification}'")
            
            extracted_manufacturer = request.POST.get(f'extracted_manufacturer_{index}')
            if extracted_manufacturer is not None:
                old_mfg = detail.extracted_manufacturer
                detail.extracted_manufacturer = str(extracted_manufacturer)
                print(f"Debug: Updated manufacturer from '{old_mfg}' to '{detail.extracted_manufacturer}'")
            
            # 商品選択を更新
            product_match = request.POST.get(f'product_match_{index}')
            print(f"Debug: product_match_{index} = {product_match}")
            if product_match is not None:
                old_product = detail.matched_product
                if product_match:
                    try:
                        product = Product.objects.get(pk=product_match)
                        detail.matched_product = product
                        detail.selected_candidate_text = f"{detail.match_score or 0}% - {product.product_name}"
                        print(f"Debug: Updated product from '{old_product}' to '{product}'")
                    except Product.DoesNotExist:
                        detail.matched_product = None
                        detail.selected_candidate_text = 'スキップ'
                        print(f"Debug: Product {product_match} not found, set to skip")
                else:
                    detail.matched_product = None
                    detail.selected_candidate_text = 'スキップ'
                    print(f"Debug: Set product to skip (empty value)")
            
            detail.save()
            print(f"Debug: Saved detail {detail.sequence} with all fields updated")
            
    except Exception as e:
        print(f"Error saving form data to database: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # エラーが発生しても処理を続行