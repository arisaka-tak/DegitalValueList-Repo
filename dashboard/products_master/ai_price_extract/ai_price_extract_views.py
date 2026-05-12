from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import subprocess
import sys
import tempfile
import os
import uuid
import traceback
from decimal import Decimal
from datetime import datetime
from dashboard.products_master.pdf_processing.extract_di_only import main as extract_di_main
from dashboard.products_master.pdf_processing.process_ai_simple import main as process_ai_main
from dashboard.products_master.models import Product, PriceHistoryApproval, ProductApproval
from dashboard.products_master.ai_extract_models import AIExtractTransaction, AIExtractTransactionDetail
from dashboard.products_master.ai_services import process_extraction_results
from dashboard.products_master.forms import PDFUploadForm
# from dashboard.products_master.pdf_ai_services import pdf_ai_service, PDFProcessingError, AIExtractionError
from dashboard.products_master.product_detail.product_detail_views import _process_approval
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs


def ai_extract(request):
    """AI価格抽出入力画面"""
    pdf_form = PDFUploadForm()
    
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': _get_dynamic_breadcrumbs_for_ai_extract(request),
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

        
        # 空文字をnullに正規化
        if 'products' in json_data:
            for product in json_data['products']:
                for key, value in product.items():
                    if value == "":
                        product[key] = None
        
        # 照合トランザクションを作成
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
                extracted_retail_price=str(extracted_data.get('retail_price', '')) if extracted_data.get('retail_price') else None,
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
        error_detail = traceback.format_exc()
        return JsonResponse({
            'error': f'処理エラー: {str(e)}',
            'detail': error_detail
        }, status=500)





def _process_ai_extract_submission(request, results, json_data):
    """AI抽出結果からの申請データ作成処理（商品詳細の申請ロジックを使用）"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"=== AI価格抽出申請処理開始 ===")
        logger.info(f"処理対象件数: {len(results.get('results', []))}件")
        
        # 適用年月を取得
        effective_year_month = request.POST.get('effective_year_month')
        logger.info(f"適用年月: {effective_year_month}")
        if not effective_year_month:
            messages.error(request, '適用年月を指定してください。')
            logger.error("適用年月が未入力")
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
            retail_price_str = request.POST.get(f'retail_price_{i}')
            
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
            
            # 個別の改定理由を取得（空の場合は一括設定を使用）
            individual_reason_str = request.POST.get(f'revision_reason_{i}', '').strip()
            final_reason = individual_reason_str if individual_reason_str else revision_reason
            
            # 前月の送料を取得
            previous_shipping_fee = None
            previous_month = f'{year:04d}/{month-1:02d}' if month > 1 else f'{year-1:04d}/12'
            previous_history = product.price_histories.filter(
                effective_year_month=previous_month,
                is_active=True
            ).first()
            if previous_history and previous_history.shipping_fee:
                previous_shipping_fee = previous_history.shipping_fee
            
            # 新しい価格履歴用のフォームデータを作成
            form_data = {
                'product_code': product.product_code,
                'livestock_type': product.livestock_type.id if product.livestock_type else '',
                'category': product.category.id if product.category else '',
                'manufacturer': product.manufacturer.id if product.manufacturer else '',
                'product_name': product.product_name,
                'model_number': product.model_number,
                'specification': product.specification,
                'shipping_unit': product.shipping_unit,
                'remarks': product.remarks,
                f'new_effective_year_month_1': f'{year:04d}/{month:02d}',
                f'new_wholesale_price_1': str(new_price),
                f'new_revision_reason_1': final_reason,
            }
            
            # 標準小売価格が入力されている場合は追加（文字列もそのまま渡す）
            if retail_price_str and retail_price_str.strip():
                form_data[f'new_retail_price_1'] = retail_price_str.strip()
            
            # 前月の送料を設定
            if previous_shipping_fee:
                form_data[f'new_shipping_fee_1'] = str(previous_shipping_fee)
            
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
            detail.extracted_retail_price = retail_price_str if retail_price_str else None
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
            logger.info(f"申請成功: {created_count}件")
        if skipped_count > 0:
            messages.info(request, f'{skipped_count}件をスキップしました。')
            logger.info(f"スキップ: {skipped_count}件")
        
        logger.info(f"=== AI価格抽出申請処理完了 ===")
        return redirect(request.path)
        
    except Exception as e:
        error_msg = f'申請データ作成中にエラーが発生しました: {str(e)}'
        logger.error(error_msg)
        logger.error(f"トレースバック: {traceback.format_exc()}")
        messages.error(request, error_msg)
        return redirect(request.path)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_rematch(request):
    """AI抽出結果の再照合API（結果をDBに保存）"""
    try:
        data = json.loads(request.body)
        transaction_pk = data.get('transaction_pk')
        sequence = data.get('sequence')
        extracted_data = data.get('extracted_data')
        
        if not transaction_pk or not sequence or not extracted_data:
            return JsonResponse({'error': 'パラメータが不正です'}, status=400)
        
        # 空文字やNoneをnullに正規化
        for key, value in extracted_data.items():
            if value == "" or value is None:
                extracted_data[key] = None
        
        # 商品照合処理を実行
        json_data = {'products': [extracted_data]}
        results = process_extraction_results(json_data)
        
        if results and 'results' in results and len(results['results']) > 0:
            result = results['results'][0]
            candidates = result.get('candidates', [])
            
            # データベースの照合結果を更新
            try:
                detail = AIExtractTransactionDetail.objects.get(
                    transaction__pk=transaction_pk,
                    sequence=int(sequence)
                )
                
                # 新しい照合結果で更新
                if candidates:
                    best_candidate = candidates[0]
                    matched_product_id = best_candidate.get('product', {}).get('pk')
                    if matched_product_id:
                        try:
                            matched_product = Product.objects.get(pk=matched_product_id)
                            detail.matched_product = matched_product
                            detail.match_score = best_candidate.get('score', 0)
                            detail.selected_candidate_text = f"{detail.match_score}% - {matched_product.product_name}"
                        except Product.DoesNotExist:
                            detail.matched_product = None
                            detail.match_score = None
                            detail.selected_candidate_text = None
                    else:
                        detail.matched_product = None
                        detail.match_score = None
                        detail.selected_candidate_text = None
                else:
                    # 候補がない場合はクリア
                    detail.matched_product = None
                    detail.match_score = None
                    detail.selected_candidate_text = None
                
                detail.save()
                
            except AIExtractTransactionDetail.DoesNotExist:
                return JsonResponse({'error': '照合結果が見つかりません'}, status=404)
            
            # 候補に現在の仕切価格情報を追加
            today = datetime.now().strftime('%Y/%m')
            
            for candidate in candidates:
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
                        # Manufacturerオブジェクトを文字列に変換
                        if 'manufacturer' in candidate['product'] and candidate['product']['manufacturer']:
                            candidate['product']['manufacturer'] = str(candidate['product']['manufacturer'])
                    except Product.DoesNotExist:
                        candidate['product']['current_wholesale_price'] = '-'
            
            return JsonResponse({
                'success': True,
                'result': result
            })
        else:
            # 照合結果がない場合もDBを更新
            try:
                detail = AIExtractTransactionDetail.objects.get(
                    transaction__pk=transaction_pk,
                    sequence=int(sequence)
                )
                detail.matched_product = None
                detail.match_score = None
                detail.selected_candidate_text = None
                detail.save()
            except AIExtractTransactionDetail.DoesNotExist:
                pass
            
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


def setup_proxy_from_config():
    """プロキシ設定をconfig.iniから読み込み環境変数に設定"""
    import configparser
    from digital_pricelist_system.config_paths import CONFIG_PATH
    
    config = configparser.ConfigParser()
    
    print(f"[WEB画面] config.iniパス: {CONFIG_PATH}")
    print(f"[WEB画面] config.ini存在: {CONFIG_PATH.exists()}")
    
    if CONFIG_PATH.exists():
        try:
            config.read(CONFIG_PATH, encoding='utf-8')
            http_proxy = config.get('PROXY', 'http_proxy', fallback='')
            https_proxy = config.get('PROXY', 'https_proxy', fallback='')
            proxy_auth = config.get('PROXY', 'proxy_auth', fallback='')
            
            print(f"[WEB画面] プロキシ設定読み込み: http_proxy={bool(http_proxy)}, https_proxy={bool(https_proxy)}, auth={bool(proxy_auth)}")
            
            if http_proxy:
                # プロトコルを除去して正しい形式に変換
                clean_proxy = http_proxy.replace('http://', '').replace('https://', '')
                if proxy_auth:
                    proxy_url = f"http://{proxy_auth}@{clean_proxy}"
                    os.environ['HTTP_PROXY'] = proxy_url
                else:
                    proxy_url = f"http://{clean_proxy}"
                    os.environ['HTTP_PROXY'] = proxy_url
                
                print(f"[WEB画面] プロキシ設定: {clean_proxy}")
            
            if https_proxy and 'HTTP_PROXY' in os.environ:
                # HTTPプロキシが設定されている場合のみHTTPSも設定
                clean_proxy = https_proxy.replace('http://', '').replace('https://', '')
                if proxy_auth:
                    os.environ['HTTPS_PROXY'] = f"http://{proxy_auth}@{clean_proxy}"
                else:
                    os.environ['HTTPS_PROXY'] = f"http://{clean_proxy}"
            
        except Exception as e:
            print(f"[WEB画面] プロキシ設定エラー: {e}")
    else:
        print(f"[WEB画面] config.iniが見つかりません")

def ai_extract_pdf_process(request):
    """PDFアップロード・AI抽出処理"""
    print(f"=== ai_extract_pdf_process called: method={request.method} ===")
    
    # プロキシ設定を環境変数に設定
    setup_proxy_from_config()
    
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
        if not transaction_name:
            transaction_name = f'PDF抽出_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        print(f"PDF file: {pdf_file.name}, Transaction: {transaction_name}")
        
        # Document Intelligence + AI抽出処理
        print("Starting Document Intelligence + AI processing...")
        print(f"プロキシ設定: HTTP={os.environ.get('HTTP_PROXY', 'なし')}, HTTPS={os.environ.get('HTTPS_PROXY', 'なし')}")
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            for chunk in pdf_file.chunks():
                temp_file.write(chunk)
            temp_pdf_path = temp_file.name
        
        try:
            print("PDF処理を開始します...")
            
            # 直接インポートでPDF処理（統一）
            try:
                # 一時ファイルパスを明示的に指定
                temp_dir = tempfile.gettempdir()
                di_result_path = os.path.join(temp_dir, f"di_result_{os.getpid()}.pkl")
                ai_result_path = os.path.join(temp_dir, f"ai_results_{os.getpid()}.json")
                
                # Document Intelligence処理
                print(f"DI処理実行: {temp_pdf_path} -> {di_result_path}")
                extract_di_main(temp_pdf_path, di_result_path)
                
                # AI解析処理
                print(f"AI処理実行: {di_result_path} -> {ai_result_path}")
                ai_results = process_ai_main(di_result_path, ai_result_path)
                
                # 一時ファイルを清理
                try:
                    if os.path.exists(di_result_path):
                        os.unlink(di_result_path)
                    if os.path.exists(ai_result_path):
                        os.unlink(ai_result_path)
                except Exception:
                    pass
                
            except ImportError as e:
                print(f"インポートエラー: {e}")
                raise Exception(f"PDF処理モジュールのインポートに失敗: {e}")
            except Exception as e:
                print(f"PDF処理エラー: {e}")
                # 一時ファイルを清理
                try:
                    if 'di_result_path' in locals() and os.path.exists(di_result_path):
                        os.unlink(di_result_path)
                    if 'ai_result_path' in locals() and os.path.exists(ai_result_path):
                        os.unlink(ai_result_path)
                except Exception:
                    pass
                
                # ネットワークエラーの場合は具体的なメッセージを表示
                error_msg = str(e)
                if 'getaddrinfo failed' in error_msg or 'Failed to resolve' in error_msg:
                    messages.error(request, 'ネットワークエラー: Azure Document Intelligenceサービスのドメイン名解決に失敗しました。企業ネットワークでAzureサービスがブロックされている可能性があります。ネットワーク管理者にお問い合わせください。')
                    return redirect('products_master:ai_extract')
                else:
                    raise Exception(f"PDF処理に失敗: {e}")
            
            if ai_results is None:
                # AI処理が失敗した場合の空のトランザクションを作成
                transaction_id = f"FAILED_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
                
                failed_transaction = AIExtractTransaction.objects.create(
                    transaction_id=transaction_id,
                    executor=get_current_user(),
                    effective_year_month='',
                    revision_reason='PDF処理失敗',
                    remarks=f"{transaction_name} - PDF処理が失敗しました",
                    total_products=0,
                    status='処理失敗'
                )
                
                messages.error(request, 'PDF処理が失敗しました。Azure Document Intelligenceサービスに接続できません。企業ネットワークの制限により、Azureサービスへのアクセスがブロックされている可能性があります。')
                return redirect('products_master:ai_extract_history_detail', pk=failed_transaction.pk)
            
            entities = ai_results.get('products', [])
            print(f"AI entities extracted: {len(entities)}")
            
            if not entities:
                print("No entities found")
                
                # エンティティが抽出できなかった場合の空のトランザクションを作成
                transaction_id = f"EMPTY_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
                
                document_metadata = ai_results.get('document_metadata', {})
                sender = document_metadata.get('sender', '')
                
                empty_transaction = AIExtractTransaction.objects.create(
                    transaction_id=transaction_id,
                    executor=get_current_user(),
                    effective_year_month='',
                    revision_reason='PDFからの抽出失敗',
                    remarks=f"{transaction_name} (送信元: {sender}) - 商品情報が抽出できませんでした",
                    total_products=0,
                    status='抽出失敗'
                )
                
                messages.warning(request, f'PDFから商品情報を抽出できませんでした。トランザクションID: {transaction_id}')
                return redirect('products_master:ai_extract_history_detail', pk=empty_transaction.pk)
            
            # AI抽出結果をJSON形式に変換
            document_metadata = ai_results.get('document_metadata', {})
            manufacturer_name = document_metadata.get('sender', '')
            
            json_data = {
                'document_metadata': document_metadata,
                'products': [
                    {
                        'product_name': entity.get('name'),
                        'new_price': entity.get('price'),
                        'retail_price': entity.get('retail_price'),
                        'model_number': entity.get('model'),
                        'manufacturer': manufacturer_name if manufacturer_name else None,
                        'specification': entity.get('spec')
                    }
                    for entity in entities
                ]
            }
            
        finally:
            # PDF一時ファイルを削除
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        
        # 照合トランザクションを作成
        transaction_id = f"PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 文書メタデータを取得
        document_metadata = json_data.get('document_metadata', {})
        sender = document_metadata.get('sender', '')
        reason = document_metadata.get('reason', 'PDFからのAI抽出')
        
        match_transaction = AIExtractTransaction.objects.create(
            transaction_id=transaction_id,
            executor=get_current_user(),
            effective_year_month='',
            revision_reason=reason,
            remarks=f"{transaction_name} (送信元: {sender})",
            uploaded_pdf=pdf_file,
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
                extracted_model_number=extracted_data.get('model_number'),
                extracted_manufacturer=extracted_data.get('manufacturer'),
                extracted_specification=extracted_data.get('specification'),
                extracted_price=str(extracted_data.get('new_price', '')),
                extracted_retail_price=str(extracted_data.get('retail_price', '')) if extracted_data.get('retail_price') else None,
                extracted_revision_reason='',  # 明細はデフォルト空欄
                matched_product=matched_product,
                match_score=match_score,
                status='未処理'
            )
        
        messages.success(request, f'PDFから{len(entities)}件の商品情報を抽出しました。')
        return redirect('products_master:ai_extract_history_detail', pk=match_transaction.pk)
        
    # except (PDFProcessingError, AIExtractionError) as e:
    #     print(f"PDF/AI Error: {str(e)}")
    #     messages.error(request, str(e))
    #     return redirect('products_master:ai_extract')
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
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
        
        # PDF処理・AI抽出（現在は使用されていない）
        # entities, pdf_text = pdf_ai_service.process_pdf_to_entities(pdf_file)
        entities, pdf_text = [], ""
        
        return JsonResponse({
            'success': True,
            'entities': entities,
            'pdf_text_preview': pdf_text[:500] + '...' if len(pdf_text) > 500 else pdf_text,
            'total_entities': len(entities)
        })
        
    # except (PDFProcessingError, AIExtractionError) as e:
    #     return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'予期しないエラー: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_get_detail(request):
    """明細データを取得"""
    try:
        data = json.loads(request.body)
        transaction_pk = data.get('transaction_pk')
        sequence = data.get('sequence')
        
        if not transaction_pk or not sequence:
            return JsonResponse({'error': 'パラメータが不正です'}, status=400)
        
        detail = AIExtractTransactionDetail.objects.get(
            transaction__pk=transaction_pk,
            sequence=int(sequence)
        )
        
        return JsonResponse({
            'extracted_product_name': detail.extracted_product_name or '',
            'extracted_model_number': detail.extracted_model_number or '',
            'extracted_specification': detail.extracted_specification or '',
            'extracted_manufacturer': detail.extracted_manufacturer or '',
            'extracted_price': detail.extracted_price or '',
            'extracted_revision_reason': detail.extracted_revision_reason or ''
        })
        
    except AIExtractTransactionDetail.DoesNotExist:
        return JsonResponse({'error': '明細データが見つかりません'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'処理エラー: {str(e)}'}, status=500)

def _get_dynamic_breadcrumbs_for_ai_extract(request):
    """AI価格抽出画面の動的パンくずリスト"""
    referer = request.META.get('HTTP_REFERER', '')
    
    if 'integrated-pricelist' in referer:
        # デジタル価格表から来た場合
        return get_breadcrumbs('ai_extract', 
                              from_page_title='デジタル価格表', 
                              from_page_url='/products/integrated-pricelist/')
    else:
        # 商品一覧から来た場合（デフォルト）
        return get_breadcrumbs('ai_extract')

@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_search_products(request):
    """商品検索API（モーダル用）"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        category_id = data.get('category_id')
        livestock_type_id = data.get('livestock_type_id')
        manufacturer_id = data.get('manufacturer_id')
        
        # 基本クエリ
        from django.db.models import Q
        products_query = Product.objects.select_related('manufacturer', 'category', 'livestock_type')
        
        # 絞り込み条件を適用
        if category_id:
            products_query = products_query.filter(category_id=category_id)
        if livestock_type_id:
            products_query = products_query.filter(livestock_type_id=livestock_type_id)
        if manufacturer_id:
            products_query = products_query.filter(manufacturer_id=manufacturer_id)
        
        # キーワード検索（空の場合は絞り込みのみ）
        if query:
            products_query = products_query.filter(
                Q(product_name__icontains=query) |
                Q(model_number__icontains=query) |
                Q(specification__icontains=query)
            )
        
        products = products_query[:50]  # 上位50件
        
        # 現在の仕切価格を取得
        from datetime import datetime
        today = datetime.now().strftime('%Y/%m')
        
        result = []
        for product in products:
            current_price_history = product.price_histories.filter(
                effective_year_month__lte=today,
                is_active=True
            ).order_by('-effective_year_month').first()
            
            current_wholesale_price = '-'
            if current_price_history:
                current_wholesale_price = current_price_history.wholesale_price or '-'
            
            result.append({
                'pk': product.pk,
                'product_name': product.product_name,
                'model_number': product.model_number or '-',
                'specification': product.specification or '-',
                'manufacturer': str(product.manufacturer) if product.manufacturer else '-',
                'current_wholesale_price': current_wholesale_price,
                'display_info': f"{product.product_name} | {product.model_number or '-'} | {product.specification or '-'}"
            })
        
        return JsonResponse({'products': result})
        
    except Exception as e:
        return JsonResponse({'error': f'検索エラー: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def ai_extract_get_masters(request):
    """マスタデータ取得API（絞り込み用）"""
    try:
        from dashboard.products_master.models import Category, LivestockType, Manufacturer
        
        categories = [{'id': c.id, 'name': c.name} for c in Category.objects.all().order_by('name')]
        livestock_types = [{'id': l.id, 'name': l.name} for l in LivestockType.objects.all().order_by('name')]
        manufacturers = [{'id': m.id, 'name': m.name} for m in Manufacturer.objects.all().order_by('name')]
        
        return JsonResponse({
            'categories': categories,
            'livestock_types': livestock_types,
            'manufacturers': manufacturers
        })
        
    except Exception as e:
        return JsonResponse({'error': f'マスタデータ取得エラー: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_update_detail(request):
    """AI抽出履歴の明細データを更新"""
    try:
        data = json.loads(request.body)
        transaction_pk = data.get('transaction_pk')
        sequence = data.get('sequence')
        field = data.get('field')
        value = data.get('value')
        
        # 一括更新か単一更新かを判定
        if 'updates' not in data and not all([transaction_pk, sequence, field]):
            return JsonResponse({'error': 'パラメータが不正です'}, status=400)
        elif not transaction_pk:
            return JsonResponse({'error': 'トランザクションIDが必要です'}, status=400)
        
        # 明細データを取得
        detail = AIExtractTransactionDetail.objects.get(
            transaction__pk=transaction_pk,
            sequence=int(sequence)
        )
        
        # 一括更新の場合
        if 'updates' in data:
            updates = data.get('updates', [])
            print(f"BATCH_UPDATE: Processing {len(updates)} updates for transaction {transaction_pk}, sequence {sequence}")
            
            # 対象の明細データを取得
            detail = AIExtractTransactionDetail.objects.get(
                transaction__pk=transaction_pk,
                sequence=int(sequence)
            )
            
            # 全ての更新を一つのオブジェクトに適用
            for update in updates:
                field = update.get('field')
                value = update.get('value')
                
                print(f"BATCH_UPDATE: {field} = '{value}'")
                
                if field == 'extracted_price':
                    detail.extracted_price = str(value) if value else ''
                elif field == 'extracted_retail_price':
                    detail.extracted_retail_price = str(value) if value else None
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
            
            # 一度だけ保存
            detail.save()
            print(f"BATCH_UPDATE: Transaction {transaction_pk}, Sequence {sequence} saved successfully")
            
            # データベースから再読み込みして保存確認
            detail.refresh_from_db()
            print(f"BATCH_VERIFY: extracted_product_name = '{detail.extracted_product_name}'")
            print(f"BATCH_VERIFY: extracted_price = '{detail.extracted_price}'")
            print(f"BATCH_VERIFY: extracted_revision_reason = '{detail.extracted_revision_reason}'")
        
        # 単一更新の場合（後方互換性のため保持）
        else:
            field = data.get('field')
            value = data.get('value')
            
            if field == 'extracted_price':
                old_value = detail.extracted_price
                detail.extracted_price = str(value) if value else ''
                print(f"SAVE: {field} '{old_value}' → '{detail.extracted_price}'")
            elif field == 'extracted_revision_reason':
                old_value = detail.extracted_revision_reason
                detail.extracted_revision_reason = str(value) if value else ''
                print(f"SAVE: {field} '{old_value}' → '{detail.extracted_revision_reason}'")
            elif field == 'extracted_product_name':
                old_value = detail.extracted_product_name
                detail.extracted_product_name = str(value) if value else ''
                print(f"SAVE: {field} '{old_value}' → '{detail.extracted_product_name}' (value='{value}')")
            elif field == 'extracted_model_number':
                old_value = detail.extracted_model_number
                detail.extracted_model_number = str(value) if value else ''
                print(f"SAVE: {field} '{old_value}' → '{detail.extracted_model_number}'")
            elif field == 'extracted_specification':
                old_value = detail.extracted_specification
                detail.extracted_specification = str(value) if value else ''
                print(f"SAVE: {field} '{old_value}' → '{detail.extracted_specification}'")
            elif field == 'extracted_manufacturer':
                old_value = detail.extracted_manufacturer
                detail.extracted_manufacturer = str(value) if value else ''
                print(f"SAVE: {field} '{old_value}' → '{detail.extracted_manufacturer}'")
            elif field == 'matched_product':
                old_value = detail.matched_product
                if value:
                    try:
                        product = Product.objects.get(pk=value)
                        detail.matched_product = product
                        detail.selected_candidate_text = f"{detail.match_score or 0}% - {product.product_name}"
                        print(f"SAVE: {field} '{old_value}' → '{product.product_name} (ID:{product.pk})'")
                    except Product.DoesNotExist:
                        detail.matched_product = None
                        detail.selected_candidate_text = 'スキップ'
                        print(f"SAVE: {field} '{old_value}' → 'None (Product not found)'")
                else:
                    detail.matched_product = None
                    detail.selected_candidate_text = 'スキップ'
                    print(f"SAVE: {field} '{old_value}' → 'None (Skip)'")
            
            detail.save()
            print(f"SAVE: Transaction {transaction_pk}, Sequence {sequence} saved successfully")
            
            # データベースから再読み込みして保存確認
            detail.refresh_from_db()
            print(f"DB_VERIFY: extracted_product_name = '{detail.extracted_product_name}'")
            print(f"DB_VERIFY: extracted_price = '{detail.extracted_price}'")
            print(f"DB_VERIFY: extracted_revision_reason = '{detail.extracted_revision_reason}'")
            print(f"DB_VERIFY: field='{field}', original_value='{value}'")
        
        return JsonResponse({'success': True})
        
    except AIExtractTransactionDetail.DoesNotExist:
        return JsonResponse({'error': '明細データが見つかりません'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSONデータが不正です'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'処理エラー: {str(e)}'}, status=500)