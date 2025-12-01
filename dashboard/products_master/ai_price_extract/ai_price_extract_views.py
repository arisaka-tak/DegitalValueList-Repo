from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from decimal import Decimal
from datetime import datetime
from dashboard.products_master.models import Product, PriceHistoryApproval, ProductApproval
from dashboard.products_master.ai_extract_models import AIExtractTransaction, AIExtractTransactionDetail
from dashboard.products_master.ai_services import process_extraction_results
from dashboard.products_master.forms import PDFUploadForm
from dashboard.products_master.pdf_ai_services import pdf_ai_service, PDFProcessingError, AIExtractionError
from dashboard.products_master.product_detail.product_detail_views import _process_approval
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs


def ai_extract(request):
    """AI価格抽出入力画面"""
    pdf_form = PDFUploadForm()
    
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('ai_extract'),
        'pdf_form': pdf_form
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
        print(f"Debug: Received JSON data: {json_data}")
        
        # 空文字をnullに正規化
        if 'products' in json_data:
            for product in json_data['products']:
                for key, value in product.items():
                    if value == "":
                        product[key] = None
        
        # 照合トランザクションを作成
        import uuid
        transaction_id = f"MATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        match_transaction = AIExtractTransaction.objects.create(
            transaction_id=transaction_id,
            executor=get_current_user(),
            effective_year_month='',  # 照合段階では未定
            revision_reason='',
            total_products=len(json_data.get('products', [])),
            status='照合中'
        )
        
        # 商品照合処理
        results = process_extraction_results(json_data)
        
        # 照合結果を明細テーブルに保存
        for i, result in enumerate(results.get('results', [])):
            extracted_data = result.get('extracted_data', {})
            candidates = result.get('candidates', [])
            
            # 最高スコアの候補を取得
            matched_product = None
            match_score = None
            if candidates:
                best_candidate = candidates[0]
                matched_product_id = best_candidate.get('product', {}).get('pk')
                if matched_product_id:
                    try:
                        matched_product = Product.objects.get(pk=matched_product_id)
                        match_score = best_candidate.get('score', 0)
                    except Product.DoesNotExist:
                        pass
            
            AIExtractTransactionDetail.objects.create(
                transaction=match_transaction,
                sequence=i + 1,
                extracted_product_name=extracted_data.get('product_name'),
                extracted_model_number=extracted_data.get('model_number'),
                extracted_manufacturer=extracted_data.get('manufacturer'),
                extracted_specification=extracted_data.get('specification'),
                extracted_price=str(extracted_data.get('new_price', '')),
                extracted_revision_reason=extracted_data.get('revision_reason'),  # 改定理由を保存
                matched_product=matched_product,
                match_score=match_score,
                status='未処理'
            )
        
        return JsonResponse({'success': True, 'redirect_url': f'/products/ai-extract/history/{match_transaction.pk}/'})
        
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





def _process_ai_extract_submission(request, results, json_data):
    """AI抽出結果からの申請データ作成処理（商品詳細の申請ロジックを使用）"""
    # インポートはファイル上部に移動済み
    
    try:
        # 適用年月を取得
        effective_year_month = request.POST.get('effective_year_month')
        print(f"Debug: effective_year_month = {effective_year_month}")
        if not effective_year_month:
            messages.error(request, '適用年月を指定してください。')
            return redirect(request.path)
        
        # 年月をdatetimeに変換
        effective_date = datetime.strptime(effective_year_month, '%Y-%m').date()
        
        # 一括改定理由を取得
        revision_reason = request.POST.get('revision_reason', 'AI価格抽出による更新')
        
        # 照合時に作成されたトランザクションを取得・更新
        transaction_id = request.session.get('ai_extract_transaction_id')
        if transaction_id:
            transaction = AIExtractTransaction.objects.get(transaction_id=transaction_id)
            transaction.effective_year_month = effective_year_month.replace('-', '/')
            transaction.revision_reason = revision_reason
            transaction.status = '申請中'
            transaction.save()
        else:
            # フォールバック: 新規作成
            import uuid
            transaction_id = f"AI_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            transaction = AIExtractTransaction.objects.create(
                transaction_id=transaction_id,
                executor=get_current_user(),
                effective_year_month=effective_year_month.replace('-', '/'),
                revision_reason=revision_reason,
                total_products=len(results.get('results', [])),
                status='申請中'
            )
        
        created_count = 0
        skipped_count = 0
        
        # 各抽出結果を処理
        print(f"Debug: Processing {len(results.get('results', []))} results")
        for i, result in enumerate(results.get('results', [])):
            product_match = request.POST.get(f'product_match_{i}')
            print(f"Debug: Product {i}: match={product_match}")
            
            # 既存の明細データを取得または作成
            detail, created = AIExtractTransactionDetail.objects.get_or_create(
                transaction=transaction,
                sequence=i + 1,
                defaults={
                    'extracted_product_name': result.get('extracted_data', {}).get('product_name'),
                    'extracted_model_number': result.get('extracted_data', {}).get('model_number'),
                    'extracted_manufacturer': result.get('extracted_data', {}).get('manufacturer'),
                    'extracted_specification': result.get('extracted_data', {}).get('specification'),
                    'status': '未処理'
                }
            )
            
            # フォームデータを優先的に使用（データベースに保存済み）
            product_match = request.POST.get(f'product_match_{i}')
            print(f"Debug: Using form data product_match_{i} = {product_match}")
            
            # 既に確定済み（スキップ・申請済）のデータは処理しない
            if detail.status in ['スキップ', '申請済']:
                continue
            
            # 商品が選択されていない場合はスキップ
            if not product_match:
                detail.status = 'スキップ'
                detail.selected_candidate_text = 'スキップ'
                detail.error_message = '商品が選択されていません'
                detail.save()
                skipped_count += 1
                continue
            
            # 商品を取得
            try:
                product = Product.objects.get(pk=product_match)
            except Product.DoesNotExist:
                detail.status = 'エラー'
                detail.error_message = f'商品ID {product_match} が見つかりません'
                detail.save()
                messages.warning(request, f'商品ID {product_match} が見つかりません。')
                continue
            
            # 重複申請チェック
            if product.status == '申請中':
                detail.status = 'エラー'
                detail.error_message = '既に申請中です'
                detail.save()
                messages.warning(request, f'商品「{product.product_name}」は既に申請中です。')
                continue
            
            # 申請テーブルでの重複チェック
            existing_approval = ProductApproval.objects.filter(
                product_number=product.pk,
                is_active=True
            ).first()
            if existing_approval:
                detail.status = 'エラー'
                detail.error_message = '既に申請テーブルに登録済みです'
                detail.save()
                messages.warning(request, f'商品「{product.product_name}」は既に申請テーブルに登録されています。')
                continue
            
            # フォームから新価格を取得
            new_price_str = request.POST.get(f'new_price_{i}')
            
            if not new_price_str:
                detail.status = 'エラー'
                detail.error_message = '新価格が入力されていません'
                detail.save()
                messages.warning(request, f'商品「{product.product_name}」の新価格が入力されていません。')
                continue
            
            # 価格を数値に変換
            try:
                new_price = Decimal(str(new_price_str).strip())
                if new_price < 0:
                    detail.status = 'エラー'
                    detail.error_message = '新価格は0以上で入力してください'
                    detail.save()
                    messages.warning(request, f'商品「{product.product_name}」の新価格は0以上で入力してください。')
                    continue
            except (ValueError, TypeError):
                detail.status = 'エラー'
                detail.error_message = f'新価格「{new_price_str}」が無効です'
                detail.save()
                messages.warning(request, f'商品「{product.product_name}」の新価格「{new_price_str}」が無効です。')
                continue
            
            # 商品詳細画面と同じ申請処理を使用するため、フォームデータを準備
            # 新しい価格履歴をフォームデータ形式で追加
            year, month = map(int, effective_year_month.split('-'))
            
            # 個別の改定理由を取得
            individual_reason_str = request.POST.get(f'revision_reason_{i}', '').strip()
            final_reason = individual_reason_str if individual_reason_str else revision_reason
            
            # 新しい価格履歴用のフォームデータを作成
            form_data = {
                'product_code': product.product_code,
                'livestock_type': product.livestock_type,
                'category': product.category,
                'manufacturer': product.manufacturer,
                'product_name': product.product_name,
                'model_number': product.model_number,
                'specification': product.specification,
                'shipping_unit': product.shipping_unit,
                'shipping_fee': product.shipping_fee,
                'remarks': product.remarks,
                f'new_effective_year_month_1': f'{year:04d}/{month:02d}',
                f'new_wholesale_price_1': str(new_price),
                f'new_revision_reason_1': final_reason,
            }
            
            # モックリクエストを作成
            from django.http import QueryDict
            mock_post = QueryDict('', mutable=True)
            mock_post.update(form_data)
            
            # モックリクエストオブジェクトを作成
            class MockRequest:
                def __init__(self, post_data):
                    self.POST = post_data
                    self.method = 'POST'
                    self.path = '/ai-extract/'
                    self.META = {}
                    self.user = request.user
            
            mock_request = MockRequest(mock_post)
            
            # 申請前のステータスを記録
            print(f"Debug: 申請前の商品ステータス: '{product.status}'")
            
            # 商品詳細画面の申請処理を呼び出し
            from dashboard.products_master.product_detail.product_detail_views import submit_approval_core
            try:
                print(f"Debug: Calling submit_approval_core with product.pk={product.pk}")
                product_approval = submit_approval_core(mock_request, product.pk)
                
                # 申請成功時の処理
                print(f"Debug: 申請成功 - ProductApproval created: {product_approval.pk}")
                
                # applicantをクリックしたユーザーに更新（AI抽出は補助ツール）
                current_user = get_current_user()
                product_approval.applicant = current_user
                product_approval.save()
                
                # 価格履歴申請のapplicantも更新
                product_approval.price_histories.update(applicant=current_user)
                
            except Exception as submit_error:
                # submit_approval_core内でのエラーをキャッチ
                import traceback
                error_detail = str(submit_error)
                traceback_info = traceback.format_exc()
                
                detail.status = 'エラー'
                detail.error_message = f'申請処理エラー: {error_detail}'
                detail.save()
                
                print(f"Submit approval error for product {product.product_name}: {error_detail}")
                print(f"Traceback: {traceback_info}")
                
                # エラーメッセージをより具体的に表示
                messages.error(request, f'商品「{product.product_name}」の申請に失敗しました。原因: {error_detail}')
                continue
            
            # 既存の明細データを更新
            detail.extracted_price = new_price_str
            detail.matched_product = product
            detail.selected_candidate_text = f"{detail.match_score or 0}% - {product.product_name}"
            detail.status = '申請済'
            if product_approval:
                detail.created_approval = product_approval
            detail.save()
            
            created_count += 1
            print(f"Debug: Created approval for product {product.product_name}")
        
        # トランザクション結果を更新
        transaction.success_count = created_count
        transaction.skip_count = skipped_count
        transaction.save()
        
        # 全明細がスキップ/申請済の場合は論理削除
        all_details = transaction.details.all()
        if all_details.exists() and all(detail.status in ['スキップ', '申請済'] for detail in all_details):
            transaction.soft_delete()
        
        # 結果メッセージ
        if created_count > 0:
            messages.success(request, f'{created_count}件の価格履歴申請を作成しました。(トランザクションID: {transaction_id})')
        if skipped_count > 0:
            messages.info(request, f'{skipped_count}件をスキップしました。')
        

        
        return redirect(request.path)
        
    except Exception as e:
        messages.error(request, f'申請データ作成中にエラーが発生しました: {str(e)}')
        return redirect(request.path)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_rematch(request):
    """AI抽出結果の再照合API"""
    try:
        data = json.loads(request.body)
        index = data.get('index')
        extracted_data = data.get('extracted_data')
        
        if index is None or not extracted_data:
            return JsonResponse({'error': 'パラメータが不正です'}, status=400)
        
        # 商品照合処理を実行
        json_data = {'products': [extracted_data]}
        results = process_extraction_results(json_data)
        
        if results and 'results' in results and len(results['results']) > 0:
            result = results['results'][0]
            
            # 候補に現在の仕切価格情報を追加
            from datetime import datetime
            today = datetime.now().strftime('%Y/%m')
            
            for candidate in result.get('candidates', []):
                product_pk = candidate.get('product', {}).get('pk')
                if product_pk:
                    try:
                        product = Product.objects.get(pk=product_pk)
                        current_price_history = product.price_histories.filter(
                            effective_year_month__lte=today,
                            is_active=True
                        ).order_by('-effective_year_month').first()
                        
                        current_wholesale_price = '-'
                        if current_price_history:
                            current_wholesale_price = current_price_history.wholesale_price or '-'
                        
                        candidate['product']['current_wholesale_price'] = current_wholesale_price
                    except Product.DoesNotExist:
                        candidate['product']['current_wholesale_price'] = '-'
            
            print(f"Debug: API returning result: {result}")
            return JsonResponse({
                'success': True,
                'result': result
            })
        else:
            print(f"Debug: No results found, returning no_match")
            return JsonResponse({
                'success': True,
                'result': {
                    'status': 'no_match',
                    'message': '照合結果が取得できませんでした'
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSONデータが不正です'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'処理エラー: {str(e)}'}, status=500)


def ai_extract_pdf_process(request):
    """PDFアップロード・AI抽出処理"""
    print(f"=== ai_extract_pdf_process called: method={request.method} ===")
    
    if request.method != 'POST':
        messages.error(request, 'POSTメソッドが必要です。')
        return redirect('products_master:ai_extract')
    
    pdf_form = PDFUploadForm(request.POST, request.FILES)
    print(f"Form is_valid: {pdf_form.is_valid()}")
    
    if not pdf_form.is_valid():
        print(f"Form errors: {pdf_form.errors}")
        messages.error(request, f'フォームにエラーがあります: {pdf_form.errors}')
        context = {
            'current_user': get_current_user(),
            'breadcrumbs': get_breadcrumbs('ai_extract'),
            'pdf_form': pdf_form
        }
        return render(request, 'products_master/ai_extract_input.html', context)
    
    try:
        pdf_file = pdf_form.cleaned_data['pdf_file']
        transaction_name = pdf_form.cleaned_data['transaction_name']
        print(f"PDF file: {pdf_file.name}, Transaction: {transaction_name}")
        
        # PDF処理・AI抽出
        print("Starting PDF processing...")
        entities, pdf_text = pdf_ai_service.process_pdf_to_entities(pdf_file)
        print(f"Entities extracted: {len(entities)}")
        
        if not entities:
            print("No entities found")
            messages.warning(request, 'PDFから商品情報を抽出できませんでした。')
            return redirect('products_master:ai_extract')
        
        # AI抽出結果をJSON形式に変換
        json_data = {
            'products': [
                {
                    'product_name': entity['name'],
                    'new_price': entity['price'],
                    'model_number': None,
                    'manufacturer': None,
                    'specification': None
                }
                for entity in entities
            ]
        }
        
        # 照合トランザクションを作成
        import uuid
        transaction_id = f"PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        match_transaction = AIExtractTransaction.objects.create(
            transaction_id=transaction_id,
            executor=get_current_user(),
            effective_year_month='',
            revision_reason='PDFからのAI抽出',
            remarks=transaction_name,
            total_products=len(entities),
            status='照合中'
        )
        
        # 商品照合処理
        results = process_extraction_results(json_data)
        
        # 照合結果を明細テーブルに保存
        for i, result in enumerate(results.get('results', [])):
            extracted_data = result.get('extracted_data', {})
            candidates = result.get('candidates', [])
            
            matched_product = None
            match_score = None
            if candidates:
                best_candidate = candidates[0]
                matched_product_id = best_candidate.get('product', {}).get('pk')
                if matched_product_id:
                    try:
                        matched_product = Product.objects.get(pk=matched_product_id)
                        match_score = best_candidate.get('score', 0)
                    except Product.DoesNotExist:
                        pass
            
            AIExtractTransactionDetail.objects.create(
                transaction=match_transaction,
                sequence=i + 1,
                extracted_product_name=extracted_data.get('product_name'),
                extracted_price=str(extracted_data.get('new_price', '')),
                matched_product=matched_product,
                match_score=match_score,
                status='未処理'
            )
        
        messages.success(request, f'PDFから{len(entities)}件の商品情報を抽出しました。')
        return redirect('products_master:ai_extract_history_detail', pk=match_transaction.pk)
        
    except (PDFProcessingError, AIExtractionError) as e:
        print(f"PDF/AI Error: {str(e)}")
        messages.error(request, str(e))
        return redirect('products_master:ai_extract')
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        messages.error(request, f'予期しないエラーが発生しました: {str(e)}')
        return redirect('products_master:ai_extract')


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_pdf_api(request):
    """PDFアップロードAPI（Ajax用）"""
    try:
        if 'pdf_file' not in request.FILES:
            return JsonResponse({'error': 'PDFファイルがアップロードされていません'}, status=400)
        
        pdf_file = request.FILES['pdf_file']
        transaction_name = request.POST.get('transaction_name', f'PDF抽出_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        # PDF処理・AI抽出
        entities, pdf_text = pdf_ai_service.process_pdf_to_entities(pdf_file)
        
        return JsonResponse({
            'success': True,
            'entities': entities,
            'pdf_text_preview': pdf_text[:500] + '...' if len(pdf_text) > 500 else pdf_text,
            'total_entities': len(entities)
        })
        
    except (PDFProcessingError, AIExtractionError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'予期しないエラー: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_update_detail(request):
    """AI抽出履歴の明細データを更新"""
    try:
        print(f"Debug: Request body: {request.body}")
        data = json.loads(request.body)
        print(f"Debug: Parsed data: {data}")
        transaction_pk = data.get('transaction_pk')
        sequence = data.get('sequence')
        field = data.get('field')
        value = data.get('value')
        
        print(f"Debug: transaction_pk={transaction_pk}, sequence={sequence}, field={field}, value={value}")
        
        # 一括更新か単一更新かを判定
        if 'updates' in data:
            print(f"Debug: Batch update mode")
        elif not all([transaction_pk, sequence, field]):
            print(f"Debug: Missing parameters for single update")
            return JsonResponse({'error': 'パラメータが不正です'}, status=400)
        elif not transaction_pk:
            print(f"Debug: Missing transaction_pk")
            return JsonResponse({'error': 'トランザクションIDが必要です'}, status=400)
        
        # 明細データを取得
        detail = AIExtractTransactionDetail.objects.get(
            transaction__pk=transaction_pk,
            sequence=int(sequence)
        )
        
        # 一括更新の場合
        if 'updates' in data:
            updates = data.get('updates', [])
            for update in updates:
                sequence = update.get('sequence')
                field = update.get('field')
                value = update.get('value')
                
                try:
                    detail = AIExtractTransactionDetail.objects.get(
                        transaction__pk=transaction_pk,
                        sequence=sequence
                    )
                    
                    if field == 'extracted_price':
                        detail.extracted_price = str(value) if value else ''
                    elif field == 'extracted_revision_reason':
                        detail.extracted_revision_reason = str(value) if value else ''
                    elif field == 'matched_product':
                        if value:
                            try:
                                product = Product.objects.get(pk=value)
                                detail.matched_product = product
                                detail.selected_candidate_text = f"{detail.match_score or 0}% - {product.product_name}"
                            except Product.DoesNotExist:
                                detail.matched_product = None
                                detail.selected_candidate_text = 'スキップ'
                        else:
                            detail.matched_product = None
                            detail.selected_candidate_text = 'スキップ'
                    
                    detail.save()
                    
                except AIExtractTransactionDetail.DoesNotExist:
                    continue
        
        # 単一更新の場合（後方互換性のため保持）
        else:
            field = data.get('field')
            value = data.get('value')
            
            if field == 'extracted_price':
                detail.extracted_price = str(value) if value else ''
            elif field == 'extracted_revision_reason':
                detail.extracted_revision_reason = str(value) if value else ''
            elif field == 'extracted_product_name':
                detail.extracted_product_name = str(value) if value else ''
            elif field == 'extracted_model_number':
                detail.extracted_model_number = str(value) if value else ''
            elif field == 'extracted_specification':
                detail.extracted_specification = str(value) if value else ''
            elif field == 'extracted_manufacturer':
                detail.extracted_manufacturer = str(value) if value else ''
            elif field == 'matched_product':
                if value:
                    try:
                        product = Product.objects.get(pk=value)
                        detail.matched_product = product
                        detail.selected_candidate_text = f"{detail.match_score or 0}% - {product.product_name}"
                    except Product.DoesNotExist:
                        detail.matched_product = None
                        detail.selected_candidate_text = 'スキップ'
                else:
                    detail.matched_product = None
                    detail.selected_candidate_text = 'スキップ'
            
            detail.save()
        
        print(f"Debug: Update successful")
        return JsonResponse({'success': True})
        
    except AIExtractTransactionDetail.DoesNotExist as e:
        print(f"Debug: Detail not found: {e}")
        return JsonResponse({'error': '明細データが見つかりません'}, status=404)
    except json.JSONDecodeError as e:
        print(f"Debug: JSON decode error: {e}")
        return JsonResponse({'error': 'JSONデータが不正です'}, status=400)
    except Exception as e:
        print(f"Debug: Unexpected error: {e}")
        import traceback
        print(f"Debug: Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': f'処理エラー: {str(e)}'}, status=500)