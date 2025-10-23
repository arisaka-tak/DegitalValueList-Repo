from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
import json
from dashboard.products_master.models import Product
from dashboard.products_master.ai_services import process_extraction_results
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

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
        'breadcrumbs': get_breadcrumbs('product_list')
    }
    return render(request, 'products_master/product_list.html', context)


def ai_extract(request):
    """AI価格抽出入力画面"""
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('ai_extract')
    }
    return render(request, 'products_master/ai_extract_input.html', context)


def ai_extract_process(request):
    """AI価格抽出処理"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        # JSONデータを取得
        json_text = request.POST.get('json_data', '')
        if not json_text:
            return JsonResponse({'error': 'JSONデータが入力されていません'}, status=400)
        
        # JSON解析
        json_data = json.loads(json_text)
        
        # 空文字をnullに正規化
        if 'products' in json_data:
            for product in json_data['products']:
                for key, value in product.items():
                    if value == "":
                        product[key] = None
        
        # 商品照合処理
        results = process_extraction_results(json_data)
        
        # 結果画面に渡すためセッションに保存
        print("Debug: Saving to session...")
        print(f"Results type: {type(results)}")
        if 'results' in results:
            for i, result in enumerate(results['results']):
                if 'candidates' in result:
                    for j, candidate in enumerate(result['candidates']):
                        print(f"Candidate {i}-{j} product type: {type(candidate.get('product'))}")
        
        request.session['ai_extract_results'] = results
        request.session['ai_extract_json'] = json_data
        
        return JsonResponse({'success': True, 'redirect_url': '/products/ai-extract/results/'})
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'JSON解析エラー: {str(e)}'}, status=400)
    except ImportError as e:
        return JsonResponse({'error': f'ライブラリエラー: {str(e)}'}, status=500)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return JsonResponse({
            'error': f'処理エラー: {str(e)}',
            'detail': error_detail
        }, status=500)


def ai_extract_results(request):
    """照合結果表示画面"""
    results = request.session.get('ai_extract_results')
    json_data = request.session.get('ai_extract_json')
    
    if not results or not json_data:
        messages.error(request, '照合結果が見つかりません。再度実行してください。')
        return redirect('products_master:ai_extract')
    
    if request.method == 'POST':
        return _process_ai_extract_submission(request, results, json_data)
    
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('ai_extract_results'),
        'results': results,
        'json_data': json_data
    }
    return render(request, 'products_master/ai_extract_results.html', context)


def _process_ai_extract_submission(request, results, json_data):
    """AI抽出結果からの申請データ作成処理"""
    from dashboard.products_master.models import PriceHistoryApproval
    from decimal import Decimal
    from datetime import datetime
    
    try:
        # 適用年月を取得
        effective_year_month = request.POST.get('effective_year_month')
        if not effective_year_month:
            messages.error(request, '適用年月を指定してください。')
            return redirect('products_master:ai_extract_results')
        
        # 年月をdatetimeに変換
        effective_date = datetime.strptime(effective_year_month, '%Y-%m').date()
        
        # 一括改定理由を取得
        revision_reason = request.POST.get('revision_reason', 'AI価格抽出による更新')
        
        created_count = 0
        skipped_count = 0
        
        # 各抽出結果を処理
        for i, result in enumerate(results.get('results', [])):
            product_match = request.POST.get(f'product_match_{i}')
            
            # 商品が選択されていない場合はスキップ
            if not product_match:
                skipped_count += 1
                continue
            
            # 商品を取得
            try:
                product = Product.objects.get(pk=product_match)
            except Product.DoesNotExist:
                messages.warning(request, f'商品ID {product_match} が見つかりません。')
                continue
            
            # フォームから新価格を取得
            new_price_str = request.POST.get(f'new_price_{i}')
            
            if not new_price_str:
                messages.warning(request, f'商品「{product.product_name}」の新価格が入力されていません。')
                continue
            
            # 価格を数値に変換
            try:
                new_price = Decimal(str(new_price_str).strip())
                if new_price < 0:
                    messages.warning(request, f'商品「{product.product_name}」の新価格は0以上で入力してください。')
                    continue
            except (ValueError, TypeError):
                messages.warning(request, f'商品「{product.product_name}」の新価格「{new_price_str}」が無効です。')
                continue
            
            # 価格履歴申請を作成
            PriceHistoryApproval.objects.create(
                product=product,
                kenren_price=str(new_price),
                revision_reason=revision_reason,
                action_type='create',
                is_delete_request=False
            )
            
            created_count += 1
        
        # 結果メッセージ
        if created_count > 0:
            messages.success(request, f'{created_count}件の価格履歴申請を作成しました。')
        if skipped_count > 0:
            messages.info(request, f'{skipped_count}件をスキップしました。')
        
        # セッションをクリア
        if 'ai_extract_results' in request.session:
            del request.session['ai_extract_results']
        if 'ai_extract_json' in request.session:
            del request.session['ai_extract_json']
        
        return redirect('products_master:product_list')
        
    except Exception as e:
        messages.error(request, f'申請データ作成中にエラーが発生しました: {str(e)}')
        return redirect('products_master:ai_extract_results')