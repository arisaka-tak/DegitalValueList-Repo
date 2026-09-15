import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, QueryDict, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.contrib import messages
from dashboard.products_master.models import Product, PriceHistory, ProductApproval, PriceHistoryApproval, LivestockType, Category, Manufacturer
from django.db.models import Q, Max
from django.db import connection, transaction
from decimal import Decimal
from dashboard.products_master.forms import ProductForm
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs
from digital_pricelist_system.gross_margin_utils import calculate_gross_margin_rate as calc_margin_rate
from digital_pricelist_system.text_utils import normalize_product_name

def is_admin_user(username):
    """管理者ユーザーかどうかを判定"""
    if not username:
        return False
    # ユーザ名@ホスト名 形式からホスト名を取得
    if '@' in username:
        hostname = username.split('@')[-1]  # @以降の部分を取得
        return hostname.startswith('BC102131')
    return False

def product_detail(request, pk):
    """商品詳細画面"""
    print(f"=== product_detail called: method={request.method}, pk={pk} ===")
    
    # POSTリクエストの場合は申請処理
    if request.method == 'POST':
        return submit_approval(request, pk)
    
    product = get_object_or_404(Product, pk=pk)
    price_histories = product.price_histories.filter(is_active=True).order_by('-effective_year_month')
    
    form = ProductForm(instance=product)
    
    # Web Component用のJSONデータを準備
    price_histories_json = json.dumps([
        {
            'id': history.pk,
            'period_year': history.period_year,
            'effective_year_month': history.effective_year_month,
            'wholesale_price': history.wholesale_price,
            'kenren_price': history.kenren_price,  # 元のkenren_priceフィールド
            'kenren_price_display': history.get_kenren_price_display(),
            'retail_price': history.retail_price,
            'shipping_fee': history.shipping_fee,
            'gross_margin_rate': str(history.gross_margin_rate) if history.gross_margin_rate is not None else None,
            'revision_amount': history.get_revision_amount(),
            'revision_reason': history.revision_reason or '',
            'memo': history.memo or '',
            'is_editable': history.is_editable()
        }
        for history in price_histories
    ])
    
    # マスタデータを取得
    livestock_types = list(LivestockType.objects.filter(is_active=True).values('id', 'name'))
    categories = list(Category.objects.filter(is_active=True).values('id', 'name'))
    
    # 商品情報用JSONデータを準備
    product_json = json.dumps({
        'product_number': product.pk if product else None,
        'product_code': product.product_code if product else '',
        'livestock_type': product.livestock_type.id if product and product.livestock_type else '',
        'category': product.category.id if product and product.category else '',
        'manufacturer': product.manufacturer.id if product and product.manufacturer else '',
        'product_name': product.product_name if product else '',
        'model_number': product.model_number if product else '',
        'specification': product.specification if product else '',
        'shipping_unit': product.shipping_unit if product else '',
        'remarks': product.remarks if product else '',
    })
    
    # フォームデータ用JSON（初期値用）
    form_data_json = json.dumps({
        'product_code': form.initial.get('product_code', ''),
        'livestock_type': form.initial.get('livestock_type', ''),
        'category': form.initial.get('category', ''),
        'manufacturer': form.initial.get('manufacturer', ''),
        'product_name': form.initial.get('product_name', ''),
        'model_number': form.initial.get('model_number', ''),
        'specification': form.initial.get('specification', ''),
        'shipping_unit': form.initial.get('shipping_unit', ''),
        'remarks': form.initial.get('remarks', ''),
    })
    
    # マスタデータ用JSON
    livestock_types_json = json.dumps(livestock_types)
    categories_json = json.dumps(categories)
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'form': form,
        'price_histories': price_histories,
        'price_histories_json': price_histories_json,
        'product_json': product_json,
        'form_data_json': form_data_json,
        'livestock_types_json': livestock_types_json,
        'categories_json': categories_json,
        'diff_flags_json': '{}',  # 新規作成時は差分なし
        'is_new': not bool(product),
        'breadcrumbs': get_breadcrumbs('product_detail', product_name=product.product_name if product else '新規作成')
    }
    return render(request, 'products_master/product_detail.html', context)

def product_copy(request, pk):
    """商品コピー（基本情報をコピーして新規作成モードで詳細画面へ）"""
    original_product = get_object_or_404(Product, pk=pk)
    
    # コピーモードで詳細画面にリダイレクト（copy_fromパラメータ付き）
    url = reverse('products_master:product_new') + f'?copy_from={pk}'
    return HttpResponseRedirect(url)

def save_product_and_histories(request, product=None):
    """商品情報と価格履歴を一括保存"""
    print("=== save_product_and_histories START ===")
    try:
        # 削除フラグがある場合は申請処理にリダイレクト
        has_delete_request = any(key.startswith('delete_') and value == 'true' for key, value in request.POST.items())
        if has_delete_request:
            print("削除申請が検出されました。申請処理にリダイレクトします。")
            return submit_approval(request, product.pk if product else None)
        
        # 1. 商品基本情報の保存
        if product:
            # 既存商品の更新
            form = ProductForm(request.POST, instance=product)
            if form.is_valid():
                product = form.save()
            else:
                return HttpResponse('<script>alert("\u30d5\u30a9\u30fc\u30e0\u30a8\u30e9\u30fc");</script>', status=400)
        else:
            # 新規商品の作成
            form = ProductForm(request.POST)
            if form.is_valid():
                product = form.save()
            else:
                return HttpResponse('<script>alert("\u30d5\u30a9\u30fc\u30e0\u30a8\u30e9\u30fc");</script>', status=400)
        
        # デバッグ: 送信されたデータを確認
        print(f"POST keys: {list(request.POST.keys())}")
        
        # 2. 新規価格履歴の保存
        for key, value in request.POST.items():
            if key.startswith('new_effective_year_month_') and value.strip():
                print(f"New history: {key} = {value}")
                index = key.split('_')[-1]
                effective_year_month = value.strip()
                wholesale_price = request.POST.get(f'new_wholesale_price_{index}', '').strip()
                
                if '/' in effective_year_month:
                    year, month = map(int, effective_year_month.split('/'))
                    period_year = year if month >= 4 else year - 1
                    
                    gross_margin_rate = determine_gross_margin_rate(product, period_year, wholesale_price or '\u90fd\u5ea6\u898b\u7a4d', request)
                    PriceHistory.objects.create(
                        product=product,
                        period_year=period_year,
                        effective_year_month=effective_year_month,
                        wholesale_price=wholesale_price or '\u90fd\u5ea6\u898b\u7a4d',
                        gross_margin_rate=gross_margin_rate,
                        revision_amount=0
                    )
        
        # 3. 既存価格履歴の更新
        for key, value in request.POST.items():
            if key.startswith('edit_'):
                print(f"Edit history: {key} = {value}")
                parts = key.split('_')
                if len(parts) >= 3:
                    # edit_wholesale_price_33 -> field='wholesale_price', history_id='33'
                    if len(parts) == 3:
                        field = parts[1]
                        history_id = parts[2]
                    else:
                        # edit_wholesale_price_33 -> field='wholesale_price', history_id='33'
                        field = '_'.join(parts[1:-1])  # 中間の部分を結合
                        history_id = parts[-1]  # 最後の部分がID
                    
                    try:
                        history = PriceHistory.objects.get(pk=history_id, product=product)
                        if hasattr(history, 'is_editable') and history.is_editable():
                            setattr(history, field, value.strip() if value.strip() else None)
                            history.save()
                            print(f"Updated {field} for history {history_id}")
                    except (PriceHistory.DoesNotExist, ValueError) as e:
                        print(f"History {history_id} error: {e}")
        

        print("=== RETURNING SUCCESS ===")
        # 新規作成の場合は詳細画面にリダイレクト
        if request.path.endswith('/new/'):
            response = HttpResponse(f'<script>alert("\u4fdd\u5b58\u5b8c\u4e86");location.href="/products/products/{product.pk}/";</script>')
        else:
            response = HttpResponse('<script>alert("\u4fdd\u5b58\u5b8c\u4e86");location.reload();</script>')
        response['Content-Type'] = 'text/html'
        return response
        
    except Exception as e:
        import traceback
        print(f"=== ERROR OCCURRED ===")
        print(f"ERROR: {traceback.format_exc()}")
        return HttpResponse('<script>alert("\u30a8\u30e9\u30fc\u767a\u751f");</script>', status=500)

def product_detail_new(request):
    """新規商品作成モードの詳細画面"""
    print(f"=== product_detail_new called: method={request.method} ===")
    copy_from_id = request.GET.get('copy_from')
    
    if request.method == 'POST':
        print(f"POST data received: {list(request.POST.keys())}")
        # 申請処理
        return submit_approval(request, None)
    else:
        # コピー元がある場合はその情報で初期化
        if copy_from_id:
            try:
                original_product = Product.objects.get(pk=copy_from_id)
                initial_data = {
                    'product_code': original_product.product_code,
                    'livestock_type': original_product.livestock_type.id if original_product.livestock_type else None,
                    'category': original_product.category.id if original_product.category else None,
                    'manufacturer': original_product.manufacturer.id if original_product.manufacturer else None,
                    'product_name': original_product.product_name,
                    'model_number': original_product.model_number,
                    'specification': original_product.specification,
                    'shipping_unit': original_product.shipping_unit,
                    'remarks': original_product.remarks,
                }
                form = ProductForm(initial=initial_data)
            except Product.DoesNotExist:
                form = ProductForm()
        else:
            form = ProductForm()
    
    # マスタデータを取得
    livestock_types = list(LivestockType.objects.filter(is_active=True).values('id', 'name'))
    categories = list(Category.objects.filter(is_active=True).values('id', 'name'))
    
    # 新規作成用JSONデータを準備
    if copy_from_id:
        try:
            original_product = Product.objects.get(pk=copy_from_id)
            product_json = json.dumps({
                'product_number': None,
                'product_code': original_product.product_code or '',
                'livestock_type': original_product.livestock_type.id if original_product.livestock_type else '',
                'category': original_product.category.id if original_product.category else '',
                'manufacturer': original_product.manufacturer.id if original_product.manufacturer else '',
                'product_name': original_product.product_name or '',
                'model_number': original_product.model_number or '',
                'specification': original_product.specification or '',
                'shipping_unit': original_product.shipping_unit or '',
                'remarks': original_product.remarks or '',
            })
        except Product.DoesNotExist:
            product_json = json.dumps({
                'product_number': None,
                'product_code': '',
                'livestock_type': '',
                'category': '',
                'manufacturer': '',
                'product_name': '',
                'model_number': '',
                'specification': '',
                'shipping_unit': '',
                'remarks': '',
            })
    else:
        product_json = json.dumps({
            'product_number': None,
            'product_code': '',
            'livestock_type': '',
            'category': '',
            'manufacturer': '',
            'product_name': '',
            'model_number': '',
            'specification': '',
            'shipping_unit': '',
            'remarks': '',
        })
    
    # マスタデータ用JSON
    livestock_types_json = json.dumps(livestock_types)
    categories_json = json.dumps(categories)
    
    form_data_json = json.dumps({
        'product_code': form.initial.get('product_code', ''),
        'livestock_type': form.initial.get('livestock_type', ''),
        'category': form.initial.get('category', ''),
        'manufacturer': form.initial.get('manufacturer', ''),
        'product_name': form.initial.get('product_name', ''),
        'model_number': form.initial.get('model_number', ''),
        'specification': form.initial.get('specification', ''),
        'shipping_unit': form.initial.get('shipping_unit', ''),
        'remarks': form.initial.get('remarks', ''),
    })
    
    context = {
        'current_user': get_current_user(),
        'product': None,  # 新規作成モード
        'form': form,
        'price_histories': [],  # 空の価格履歴
        'price_histories_json': '[]',  # 空のJSON配列
        'product_json': product_json,
        'form_data_json': form_data_json,
        'livestock_types_json': livestock_types_json,
        'categories_json': categories_json,
        'diff_flags_json': '{}',
        'is_new': True,  # 新規作成フラグ
        'breadcrumbs': _get_dynamic_breadcrumbs_for_new(request)
    }
    return render(request, 'products_master/product_detail.html', context)

@csrf_exempt
def price_history_update(request, pk):
    """価格履歴更新（HTMX）"""
    if request.method != 'POST':
        return HttpResponse('Invalid request', status=400)
    
    price_history = get_object_or_404(PriceHistory, pk=pk)
    
    if not price_history.is_editable():
        return HttpResponse('Not editable', status=400)
    
    try:
        field = request.POST.get('field')
        value = request.POST.get('value')
        
        if field == 'wholesale_price':
            price_history.wholesale_price = value if value else None
        elif field == 'kenren_price':
            price_history.kenren_price = value if value else None
        elif field == 'revision_reason':
            price_history.revision_reason = value if value else None
        elif field == 'memo':
            price_history.memo = value if value else None
        
        price_history.save()
        
        # HTMX用に更新後の行を返す（改定額も含めて更新）
        html = render_to_string('products_master/partials/price_history_row.html', {
            'history': price_history
        })
        return HttpResponse(html)
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

@csrf_exempt
def price_history_delete(request, pk):
    """価格履歴削除"""
    if request.method != 'POST':
        return HttpResponse('Invalid request', status=400)
    
    price_history = get_object_or_404(PriceHistory, pk=pk)
    
    if not price_history.is_deletable():
        return HttpResponse('Not deletable', status=400)
    
    try:
        price_history.soft_delete()
        return HttpResponse('')  # HTMXは空のHTMLで行を削除
    except Exception:
        return HttpResponse('Error', status=500)

def price_history_create(request, product_pk):
    """価格履歴新規作成"""
    product = get_object_or_404(Product, pk=product_pk)
    
    if request.method == 'POST':
        try:
            effective_year_month = request.POST.get('effective_year_month', '').strip()
            wholesale_price = request.POST.get('wholesale_price', '').strip()
            kenren_price = request.POST.get('kenren_price', '').strip()
            revision_reason = request.POST.get('revision_reason', '').strip()
            memo = request.POST.get('memo', '').strip()
            
            if not effective_year_month:
                return HttpResponse('Missing effective_year_month', status=400)
            
            # 日付バリデーション
            try:
                formatted_date = validate_date_format(effective_year_month)
                check_business_rules(formatted_date, product)
                effective_year_month = formatted_date
            except ValueError as e:
                return HttpResponse(str(e), status=400)
            
            if not wholesale_price:
                wholesale_price = '都度見積'
            
            # 年度を自動算出
            year, month = map(int, effective_year_month.split('/'))
            period_year = year if month >= 4 else year - 1
            
            gross_margin_rate = determine_gross_margin_rate(product, period_year, wholesale_price, request)
            price_history = PriceHistory.objects.create(
                product=product,
                period_year=period_year,
                effective_year_month=effective_year_month,
                wholesale_price=wholesale_price,
                kenren_price=kenren_price if kenren_price else None,
                revision_reason=revision_reason if revision_reason else None,
                memo=memo if memo else None,
                gross_margin_rate=gross_margin_rate,
                revision_amount=0
            )
            return HttpResponse('Created successfully')
            
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}', status=500)
    
    return HttpResponse('Invalid method', status=405)

def add_price_row(request, pk=None):
    """新規行を追加したテーブルを返す（HTMX）"""
    if pk:
        # 既存商品の場合
        product = get_object_or_404(Product, pk=pk)
        price_histories = list(product.price_histories.filter(is_active=True).order_by('-effective_year_month'))
    else:
        # 新規作成モードの場合
        price_histories = []
    
    context = {
        'price_histories': price_histories,
        'show_new_row': True
    }
    return render(request, 'products_master/partials/price_history_table.html', context)

def calc_kenren_price(request, pk):
    """県連価格を計算して返す（HTMX）"""
    history = get_object_or_404(PriceHistory, pk=pk)
    
    # デバッグ: 送信されたデータを確認
    print(f"=== calc_kenren_price called for history {pk} ===")
    print(f"GET params: {dict(request.GET)}")
    
    wholesale_price = request.GET.get(f'edit_wholesale_price_{pk}', '')
    print(f"wholesale_price: '{wholesale_price}'")
    
    # 仮の価格で計算
    try:
        if wholesale_price and wholesale_price != '都度見積':
            price_num = float(wholesale_price.replace(',', ''))
            margin_rate = float(history.gross_margin_rate)  # Decimalをfloatに変換
            calc_price = int(price_num * margin_rate)
            calc_display = f'{calc_price:,}'
            print(f"Calculated: {price_num} * {margin_rate} = {calc_display}")
        else:
            calc_display = '要見積'
            print(f"No valid price, showing: {calc_display}")
    except (ValueError, TypeError) as e:
        calc_display = '要見積'
        print(f"Error calculating: {e}")
    
    # 県連価格セルのみを返す
    context = {
        'history': history,
        'calc_display': calc_display
    }
    return render(request, 'products_master/partials/kenren_price_cell.html', context)

def preview_save(request, pk=None):
    """保存前の確認画面を表示（HTMX）"""
    if pk:
        product = get_object_or_404(Product, pk=pk)
    else:
        product = None
    
    # 商品情報を仮更新（保存はしない）
    if product:
        form = ProductForm(request.POST, instance=product)
    else:
        form = ProductForm(request.POST)
    
    if not form.is_valid():
        return HttpResponse('<script>alert("商品情報にエラーがあります");</script>')
    
    preview_product = form.save(commit=False)  # 保存せずにオブジェクトだけ作成
    
    # 価格履歴の予想更新内容を作成
    preview_histories = []
    
    if product:  # 既存商品の場合
        for history in product.price_histories.filter(is_active=True):
            # 各履歴の更新内容をチェック
            wholesale_price = request.POST.get(f'edit_wholesale_price_{history.pk}', '').strip()
            kenren_price = request.POST.get(f'edit_kenren_price_{history.pk}', '').strip()
            revision_reason = request.POST.get(f'edit_revision_reason_{history.pk}', '').strip()
            delete_flag = request.POST.get(f'delete_{history.pk}', 'false')
            
            if delete_flag == 'true':
                continue  # 削除予定の履歴はスキップ
            
            # 予想更新後の値を計算
            preview_history = {
                'pk': history.pk,
                'period_year': history.period_year,
                'effective_year_month': history.effective_year_month,
                'wholesale_price': wholesale_price if wholesale_price else history.wholesale_price,
                'kenren_price': kenren_price if kenren_price else None,
                'revision_reason': revision_reason if f'edit_revision_reason_{history.pk}' in request.POST else history.revision_reason,
                'gross_margin_rate': history.gross_margin_rate,
                'is_changed': bool(wholesale_price or kenren_price or revision_reason)
            }
            
            # 県連価格の自動計算
            if not preview_history['kenren_price'] and preview_history['wholesale_price']:
                try:
                    if preview_history['wholesale_price'] != '都度見積':
                        price_num = float(str(preview_history['wholesale_price']).replace(',', ''))
                        margin_rate = float(history.gross_margin_rate)
                        preview_history['calc_kenren_price'] = int(price_num * margin_rate)
                except (ValueError, TypeError):
                    preview_history['calc_kenren_price'] = None
            
            preview_histories.append(preview_history)
    
    # 新規履歴の処理
    for key, value in request.POST.items():
        if key.startswith('new_effective_year_month_') and value.strip():
            index = key.split('_')[-1]
            effective_year_month = value.strip()
            wholesale_price = request.POST.get(f'new_wholesale_price_{index}', '').strip()
            kenren_price = request.POST.get(f'new_kenren_price_{index}', '').strip()
            revision_reason = request.POST.get(f'new_revision_reason_{index}', '').strip()
            
            if '/' in effective_year_month:
                year, month = map(int, effective_year_month.split('/'))
                period_year = year if month >= 4 else year - 1
                
                new_history = {
                    'pk': f'new_{index}',
                    'period_year': period_year,
                    'effective_year_month': effective_year_month,
                    'wholesale_price': wholesale_price or '都度見積',
                    'kenren_price': kenren_price if kenren_price else None,
                    'revision_reason': revision_reason,
                    'gross_margin_rate': 1.1,
                    'is_new': True
                }
                
                # 県連価格の自動計算
                if not new_history['kenren_price'] and new_history['wholesale_price'] != '都度見積':
                    try:
                        price_num = float(str(new_history['wholesale_price']).replace(',', ''))
                        new_history['calc_kenren_price'] = int(price_num * 1.1)
                    except (ValueError, TypeError):
                        new_history['calc_kenren_price'] = None
                
                preview_histories.append(new_history)
    
    # 時系列順にソートしてから改定額を計算
    preview_histories.sort(key=lambda x: x['effective_year_month'])
    
    for i, history in enumerate(preview_histories):
        if i == 0:
            history['calc_revision_amount'] = 0  # 最初の履歴は0
        else:
            try:
                # 現在の県連価格
                current_price = history.get('kenren_price') or history.get('calc_kenren_price')
                # 前の履歴の県連価格
                prev_price = preview_histories[i-1].get('kenren_price') or preview_histories[i-1].get('calc_kenren_price')
                
                if current_price and prev_price:
                    current_num = int(float(str(current_price).replace(',', '')))
                    prev_num = int(float(str(prev_price).replace(',', '')))
                    history['calc_revision_amount'] = current_num - prev_num
                else:
                    history['calc_revision_amount'] = 0
            except (ValueError, TypeError):
                history['calc_revision_amount'] = 0
    
    # 表示用に逆順（新しい順）に戻す
    preview_histories.sort(key=lambda x: x['effective_year_month'], reverse=True)
    
    context = {
        'product': preview_product,
        'preview_histories': preview_histories,
        'is_new': not bool(pk)
    }
    
    return render(request, 'products_master/partials/save_preview_modal.html', context)

def submit_approval_core(request, pk=None, is_reapplication=False):
    """申請処理のコア機能（結果とエラーメッセージを返す）"""
    print(f"=== submit_approval_core called: pk={pk}, method={request.method}, is_reapplication={is_reapplication} ===")
    print(f"Request path: {request.path}")
    print(f"POST data keys: {list(request.POST.keys())}")
    
    if pk:
        try:
            product = Product.objects.get(pk=pk)
            if product.status:
                raise ValueError("この商品は既に申請中です")
        except Product.DoesNotExist:
            product = None
    else:
        product = None
    
    # 共通バリデーションを使用
    print("=== バリデーション開始 ===")
    try:
        product_data, new_histories = validate_form_data(request, product)
        print(f"Validation successful: {len(new_histories)} new histories")
    except ValueError as e:
        print(f"Validation error: {str(e)}")
        raise ValueError(str(e))
    except Exception as e:
        print(f"Unexpected validation error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"バリデーションエラー: {str(e)}")
    print("=== バリデーション完了 ===")
    
    # 申請テーブルに商品情報をコピー
    if product:
        temp_product_number = product.pk
        Product.objects.filter(pk=product.pk).update(status='申請中', approver='')
    else:
        last_temp = ProductApproval.objects.filter(product_number__lt=0).order_by('product_number').first()
        temp_product_number = (last_temp.product_number - 1) if last_temp else -1
        print(f"New product temp number: {temp_product_number}")
    
    approval_product = ProductApproval.objects.create(
        product_number=temp_product_number,
        product_code=product_data['product_code'],
        livestock_type=product_data['livestock_type'],
        category=product_data['category'],
        manufacturer=product_data['manufacturer'],
        product_name=product_data['product_name'],
        model_number=product_data['model_number'],
        specification=product_data['specification'],
        shipping_unit=product_data['shipping_unit'],
        remarks=product_data['remarks'],
        applicant=get_current_user()
    )
    print(f"Created ProductApproval: pk={approval_product.pk}, product_number={approval_product.product_number}")
    
    # 価格履歴を申請テーブルにコピー
    if product:
        for history in product.price_histories.filter(is_active=True):
            wholesale_price = request.POST.get(f'edit_wholesale_price_{history.pk}', '').strip()
            kenren_price = request.POST.get(f'edit_kenren_price_{history.pk}', '').strip()
            retail_price = request.POST.get(f'edit_retail_price_{history.pk}', '').strip()
            revision_reason = request.POST.get(f'edit_revision_reason_{history.pk}', '').strip()
            memo = request.POST.get(f'edit_memo_{history.pk}', '').strip()
            delete_flag = request.POST.get(f'delete_{history.pk}', 'false')
            
            # 既存履歴を申請テーブルにコピー（元の粗利率を保持）
            PriceHistoryApproval.objects.create(
                product=approval_product,
                period_year=history.period_year,
                effective_year_month=history.effective_year_month,
                gross_margin_rate=history.gross_margin_rate,  # 元の粗利率をそのまま使用
                wholesale_price=wholesale_price if wholesale_price else history.wholesale_price,
                kenren_price=kenren_price if kenren_price else history.kenren_price,
                retail_price=retail_price if retail_price else history.retail_price,
                shipping_fee=request.POST.get(f'edit_shipping_fee_{history.pk}', '').strip() or history.shipping_fee,
                revision_amount=0,
                revision_reason=revision_reason if f'edit_revision_reason_{history.pk}' in request.POST else history.revision_reason,
                memo=memo if f'edit_memo_{history.pk}' in request.POST else history.memo,
                is_delete_request=(delete_flag == 'true'),
                applicant=get_current_user()
            )
    
    # 新規履歴を申請テーブルに追加
    existing_approval_dates = list(PriceHistoryApproval.objects.filter(
        product=approval_product
    ).values_list('effective_year_month', flat=True))
    
    for history in new_histories:
        year, month = map(int, history['effective_year_month'].split('/'))
        period_year = year if month >= 4 else year - 1
        effective_year_month = f"{year:04d}/{month:02d}"
        
        check_business_rules(effective_year_month, product, existing_approval_dates)
        existing_approval_dates.append(effective_year_month)
        
        # 申請時に粗利率を確定（県連価格が手入力されている場合はそこから算出）
        gross_margin_rate = determine_gross_margin_rate(product, period_year, history['wholesale_price'] or '都度見積', request)
        
        PriceHistoryApproval.objects.create(
            product=approval_product,
            period_year=period_year,
            effective_year_month=effective_year_month,
            gross_margin_rate=gross_margin_rate,  # 申請時に確定した粗利率
            wholesale_price=history['wholesale_price'] or '都度見積',
            kenren_price=history['kenren_price'] if history['kenren_price'] else None,
            retail_price=history['retail_price'] if history['retail_price'] else None,
            shipping_fee=history['shipping_fee'] if history['shipping_fee'] else None,
            revision_amount=0,
            revision_reason=history['revision_reason'] if history['revision_reason'] else None,
            memo=history['memo'] if history['memo'] else None,
            applicant=get_current_user()
        )
    
    print(f"=== submit_approval_core completed successfully ===")
    return approval_product

def submit_approval(request, pk=None):
    """申請処理（既存の呼び出し用）"""
    try:
        submit_approval_core(request, pk)
        return HttpResponse('<script>alert("申請完了");location.href="/products/";</script>')
    except ValueError as e:
        # バリデーションエラーの場合はJSONでエラーを返す
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return JsonResponse({'error': 'エラーが発生しました'}, status=500)

def validate_date_format(effective_year_month):
    """日付形式のバリデーションのみ"""
    if '/' not in effective_year_month:
        raise ValueError('適用年月はYYYY/MM形式で入力してください')
    
    parts = effective_year_month.split('/')
    if len(parts) != 2:
        raise ValueError('適用年月はYYYY/MM形式で入力してください')
    
    try:
        year_str, month_str = parts
        year = int(year_str)
        month = int(month_str)
    except (ValueError, IndexError):
        raise ValueError('適用年月はYYYY/MM形式で入力してください')
    
    if year < 2000 or year > 2099:
        raise ValueError('年は2000～2099の範囲で入力してください')
    
    if month < 1 or month > 12:
        raise ValueError('月は1～12の範囲で入力してください')
    
    return f"{year:04d}/{month:02d}"

def check_business_rules(formatted_date, product=None, existing_dates=None):
    """ビジネスルールのチェック（共通化）"""
    if existing_dates is None:
        existing_dates = []
    
    year, month = map(int, formatted_date.split('/'))
    
    # 既存商品の場合のチェック
    if product:
        # 既存の価格履歴との重複チェック
        if PriceHistory.objects.filter(product=product, effective_year_month=formatted_date, is_active=True).exists():
            raise ValueError(f'{formatted_date}の価格履歴は既に存在します。')
        
        # 編集可能範囲のチェック
        from datetime import datetime
        today = datetime.now().strftime('%Y/%m')
        
        # 履歴が0→1になる場合（初回登録）は過去日付も許可
        existing_count = PriceHistory.objects.filter(product=product, is_active=True).count()
        
        if existing_count > 0 and formatted_date < today:
            raise ValueError(f'操作日より前の月（{formatted_date}）は登録できません。')
        
        # 過去の日付の場合、編集可能な最新の履歴より前は登録不可
        if formatted_date < today:
            latest_editable = PriceHistory.objects.filter(
                product=product, effective_year_month__lt=today, is_active=True
            ).order_by('-effective_year_month').first()
            
            if latest_editable and formatted_date <= latest_editable.effective_year_month:
                raise ValueError(f'編集不可な範囲の日付です。{latest_editable.effective_year_month}より後の日付を入力してください。')
    
    # 2年度以上先の登録禁止（共通チェック）
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_period_year = current_year if current_month >= 4 else current_year - 1
    input_period_year = year if month >= 4 else year - 1
    
    if input_period_year > current_period_year + 1:
        raise ValueError(f'{input_period_year}年度は2年度以上先のため登録できません。')
    
    # 重複チェック（共通チェック）
    if formatted_date in existing_dates:
        raise ValueError(f'{formatted_date}が重複しています。')

def _return_form_with_error(request, product, form, error_message):
    """エラー時のフォーム再表示用ヘルパー関数"""
    if product:
        price_histories = product.price_histories.filter(is_active=True).order_by('-effective_year_month')
        price_histories_json = json.dumps([
            {
                'id': history.pk,
                'period_year': history.period_year,
                'effective_year_month': history.effective_year_month,
                'wholesale_price': history.wholesale_price,
                'kenren_price': history.kenren_price,
                'kenren_price_display': history.get_kenren_price_display(),
                'gross_margin_rate': str(history.gross_margin_rate) if history.gross_margin_rate is not None else None,
                'revision_amount': history.get_revision_amount(),
                'revision_reason': history.revision_reason or '',
                'is_editable': history.is_editable()
            }
            for history in price_histories
        ])
        
        # 商品情報JSON
        product_json = json.dumps({
            'product_number': product.pk,
            'product_code': product.product_code or '',
            'livestock_type': product.livestock_type.id if product.livestock_type else '',
            'category': product.category.id if product.category else '',
            'manufacturer': product.manufacturer.id if product.manufacturer else '',
            'product_name': product.product_name or '',
            'model_number': product.model_number or '',
            'specification': product.specification or '',
            'shipping_unit': product.shipping_unit or '',
            'remarks': product.remarks or '',
        })
    else:
        price_histories = []
        price_histories_json = '[]'
        product_json = json.dumps({})
    
    # フォームエラー時の入力値を取得
    form_data_json = json.dumps({
        'product_code': request.POST.get('product_code', ''),
        'livestock_type': request.POST.get('livestock_type', ''),
        'category': request.POST.get('category', ''),
        'manufacturer': request.POST.get('manufacturer', ''),
        'product_name': request.POST.get('product_name', ''),
        'model_number': request.POST.get('model_number', ''),
        'specification': request.POST.get('specification', ''),
        'shipping_unit': request.POST.get('shipping_unit', ''),
        'remarks': request.POST.get('remarks', ''),
    })
    
    # エラーフィールドを特定
    error_fields = []
    if '商品名は必須です' in error_message:
        error_fields.append('product_name')
    if '商品コードは9桁の数字で入力してください' in error_message:
        error_fields.append('product_code')
    if '畜種は必須です' in error_message:
        error_fields.append('livestock_type')
    if '分類は必須です' in error_message:
        error_fields.append('category')
    if 'メーカーは必須です' in error_message:
        error_fields.append('manufacturer')
    
    error_fields_json = json.dumps(error_fields)
    
    preview_histories = []
    for key, value in request.POST.items():
        if key.startswith('new_effective_year_month_') and value.strip():
            index = key.split('_')[-1]
            effective_year_month = value.strip()
            wholesale_price = request.POST.get(f'new_wholesale_price_{index}', '').strip()
            kenren_price = request.POST.get(f'new_kenren_price_{index}', '').strip()
            revision_reason = request.POST.get(f'new_revision_reason_{index}', '').strip()
            
            preview_histories.append({
                'effective_year_month': effective_year_month,
                'wholesale_price': wholesale_price,
                'kenren_price': kenren_price,
                'revision_reason': revision_reason,
                'index': index
            })
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'form': form,
        'price_histories': price_histories,
        'price_histories_json': price_histories_json,
        'product_json': product_json,
        'form_data_json': form_data_json,
        'diff_flags_json': '{}',
        'preview_histories': preview_histories,
        'is_new': not bool(product),
        'error_message': error_message,
        'error_fields_json': error_fields_json,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': '新規作成' if not product else f'{product.product_name or "商品詳細"}', 'url': None}
        ]
    }
    return render(request, 'products_master/product_detail.html', context)

def get_kenren_price_input(request, wholesale_price):
    """リクエストから県連価格入力を取得"""
    if not request:
        return None, None
    
    for key, value in request.POST.items():
        if key.startswith('new_wholesale_price_') and value.strip() == wholesale_price:
            current_index = key.split('_')[-1]
            kenren_value = request.POST.get(f'new_kenren_price_{current_index}', '').strip()
            if kenren_value:
                try:
                    kenren_numeric = float(kenren_value.replace(',', ''))
                    return kenren_value, kenren_numeric
                except (ValueError, AttributeError):
                    return kenren_value, None
            break
    return None, None

def calculate_margin_from_prices(kenren_price, wholesale_price):
    """県連価格と仕切価格から粗利率を計算（共通関数使用）"""
    try:
        wholesale_numeric = float(wholesale_price.replace(',', ''))
        kenren_numeric = float(str(kenren_price).replace(',', ''))
        return calc_margin_rate(wholesale_numeric, kenren_numeric)
    except (ValueError, AttributeError):
        pass
    return None

def get_margin_from_table(product, period_year):
    """粗利率テーブルから取得（0.0の場合は未登録扱い）"""
    from dashboard.products_master.models import ProductGrossMarginRate
    if not product:
        return None
    
    try:
        margin_rate_record = ProductGrossMarginRate.objects.get(
            product=product, period_year=period_year
        )
        # 0.0の場合は未登録扱い
        if margin_rate_record.gross_margin_rate == Decimal('0.0'):
            return None
        return margin_rate_record.gross_margin_rate
    except ProductGrossMarginRate.DoesNotExist:
        return None

def get_margin_from_history(product, period_year, wholesale_price):
    """過去履歴から粗利率を推定（前年度の最終仕切価格÷前年度の最終県連価格）"""
    from dashboard.products_master.models import PriceHistory
    if not product:
        return None
    
    past_history = PriceHistory.objects.filter(
        product=product,
        period_year__lt=period_year,
        is_active=True
    ).order_by('-period_year', '-effective_year_month').first()
    
    if not past_history:
        return None
    
    try:
        # 前年度の最終県連価格を取得
        if not past_history.kenren_price:
            return None
        
        past_kenren_price = float(str(past_history.kenren_price).replace(',', ''))
        
        # 前年度の最終仕切価格を取得
        past_wholesale_price = float(str(past_history.wholesale_price).replace(',', '')) if past_history.wholesale_price != '都度見積' else None
        
        if not past_wholesale_price or past_wholesale_price <= 0 or past_kenren_price <= 0:
            return None
        
        # 新しい計算方式：仕切価格÷県連価格
        calculated_rate = past_wholesale_price / past_kenren_price
        
        # 小数点第2位まで、3位以下を切り捨て
        import math
        truncated_rate = math.floor(calculated_rate * 100) / 100
        
        return Decimal(str(truncated_rate))
    except (ValueError, TypeError, ZeroDivisionError):
        return None

def determine_gross_margin_rate(product, period_year, wholesale_price, request=None):
    """粗利率を決定し、必要に応じて粗利率テーブルを更新"""
    
    # 1. 県連価格が手入力されているかチェック
    kenren_text, kenren_numeric = get_kenren_price_input(request, wholesale_price)
    
    if kenren_text is not None and kenren_numeric is not None:
        # 仕切価格と県連価格が両方入力された場合、粗利率を計算して粗利率テーブルを更新
        try:
            wholesale_numeric = float(wholesale_price.replace(',', ''))
            if wholesale_numeric > 0:
                margin_rate = calculate_margin_from_prices(kenren_numeric, wholesale_price)
                if margin_rate is not None and product:
                    # 粗利率テーブルを更新（最新の粗利率として記録）
                    from dashboard.products_master.models import ProductGrossMarginRate
                    ProductGrossMarginRate.objects.update_or_create(
                        product=product,
                        period_year=period_year,
                        defaults={'gross_margin_rate': margin_rate}
                    )
                return margin_rate
        except (ValueError, AttributeError):
            pass
    
    # 2. 粗利率テーブルから最新の粗利率を取得
    margin_rate = get_margin_from_table(product, period_year)
    if margin_rate is not None and margin_rate != Decimal('0.0'):
        return margin_rate
    
    # 3. 過去年度の粗利率を継続使用
    if product:
        from dashboard.products_master.models import ProductGrossMarginRate
        latest_margin = ProductGrossMarginRate.objects.filter(
            product=product,
            period_year__lt=period_year,
            gross_margin_rate__gt=Decimal('0.0')
        ).order_by('-period_year').first()
        
        if latest_margin:
            return latest_margin.gross_margin_rate
    
    # 4. 初回登録時はデフォルト値
    return Decimal('0.90')

def approval_list(request):
    """申請一覧画面"""
    search_query = request.GET.get('search', '')
    
    approvals = ProductApproval.objects.filter(is_active=True)
    
    if search_query:
        approvals = approvals.filter(
            Q(product_name__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(product_code__icontains=search_query)
        )
    
    approvals = approvals.order_by('-created_at')
    
    # IDを名前に変換
    livestock_types = {str(lt.id): lt.name for lt in LivestockType.objects.filter(is_active=True)}
    categories = {str(c.id): c.name for c in Category.objects.filter(is_active=True)}
    manufacturers = {str(m.id): m.name for m in Manufacturer.objects.filter(is_active=True)}
    
    for approval in approvals:
        approval.livestock_type_name = livestock_types.get(str(approval.livestock_type), approval.livestock_type)
        approval.category_name = categories.get(str(approval.category), approval.category)
        approval.manufacturer_name = manufacturers.get(str(approval.manufacturer), approval.manufacturer)
    
    context = {
        'current_user': get_current_user(),
        'approvals': approvals,
        'search_query': search_query,
        'breadcrumbs': get_breadcrumbs('approval_list')
    }
    return render(request, 'products_master/approval_list.html', context)

def approval_detail(request, pk):
    """申請詳細画面"""
    approval = get_object_or_404(ProductApproval, pk=pk)
    print(f"=== approval_detail: pk={pk}, status='{approval.status}' ===")
    
    # 再申請待ちの場合はPOSTリクエストで更新処理
    if request.method == 'POST' and approval.status == '再申請待ち':
        return _update_reapplication(request, approval)
    
    price_histories = approval.price_histories.filter(is_active=True).order_by('-effective_year_month')
    
    # 元データとの差分を計算
    original_product = None
    if approval.product_number > 0:
        try:
            original_product = Product.objects.get(pk=approval.product_number)
        except Product.DoesNotExist:
            pass
    
    # 商品情報の差分フラグ
    diff_flags = {}
    if original_product:
        diff_flags = {
            'product_code': approval.product_code != original_product.product_code,
            'livestock_type': approval.livestock_type != original_product.livestock_type,
            'category': approval.category != original_product.category,
            'manufacturer': approval.manufacturer != original_product.manufacturer,
            'product_name': approval.product_name != original_product.product_name,
            'model_number': approval.model_number != original_product.model_number,
            'specification': approval.specification != original_product.specification,
            'shipping_unit': approval.shipping_unit != original_product.shipping_unit,
            'remarks': approval.remarks != original_product.remarks,
        }
    
    # 価格履歴の差分フラグ
    for history in price_histories:
        if original_product:
            original_history = PriceHistory.objects.filter(
                product=original_product,
                effective_year_month=history.effective_year_month,
                is_active=True
            ).first()
            
            if original_history:
                history.diff_flags = {
                    'wholesale_price': history.wholesale_price != original_history.wholesale_price,
                    'kenren_price': history.kenren_price != original_history.kenren_price,
                    'retail_price': history.retail_price != original_history.retail_price,
                    'revision_reason': history.revision_reason != original_history.revision_reason,
                }
            else:
                # 新規履歴は全て差分
                history.diff_flags = {
                    'wholesale_price': True,
                    'kenren_price': True,
                    'retail_price': True,
                    'revision_reason': True,
                }
        else:
            # 新規商品は全て差分
            history.diff_flags = {
                'wholesale_price': True,
                'kenren_price': True,
                'retail_price': True,
                'revision_reason': True,
            }
    
    # 再申請待ちの場合は編集可能モード
    is_editable = (approval.status == '再申請待ち')
    print(f"is_editable: {is_editable}")
    
    # 価格履歴の編集可能性をデバッグ出力
    for history in price_histories:
        print(f"History {history.pk}: is_editable={history.is_editable()}")
    
    # マスタデータを取得
    livestock_types = list(LivestockType.objects.filter(is_active=True).values('id', 'name'))
    categories = list(Category.objects.filter(is_active=True).values('id', 'name'))
    manufacturers = list(Manufacturer.objects.filter(is_active=True).values('id', 'name'))
    
    # マスタデータ用JSON
    livestock_types_json = json.dumps(livestock_types)
    categories_json = json.dumps(categories)
    manufacturers_json = json.dumps(manufacturers)
    
    context = {
        'current_user': get_current_user(),
        'approval': approval,
        'price_histories': price_histories,
        'diff_flags': diff_flags,
        'is_new_product': not bool(original_product),
        'is_editable': is_editable,
        'livestock_types_json': livestock_types_json,
        'categories_json': categories_json,
        'manufacturers_json': manufacturers_json,
        'breadcrumbs': get_breadcrumbs('approval_detail', product_name=approval.product_name)
    }
    return render(request, 'products_master/approval_detail.html', context)

def _process_approval(approval):
    """承認処理の共通ロジック"""
    
    try:
        with transaction.atomic():
            if approval.product_number > 0:
                # 既存商品の更新
                product = Product.objects.get(pk=approval.product_number)
                
                # 削除申請の場合は論理削除
                if approval.status == '削除申請':
                    product.soft_delete()
                    product.status = ''  # ステータスをクリア
                    product.save()
                    approval.delete()
                    return
                
                # 復元申請の場合は復元
                if approval.status == '復元申請':
                    product.restore()
                    product.status = ''  # ステータスをクリア
                    product.save()
                    approval.delete()
                    return
        
                # 商品情報を更新
                product.product_code = approval.product_code
                
                # 畜種と分類を外部キーオブジェクトに変換
                if approval.livestock_type:
                    try:
                        livestock_type_value = str(approval.livestock_type).strip("'\"")
                        # IDか名前かを判定
                        if livestock_type_value.isdigit():
                            product.livestock_type = LivestockType.objects.get(id=livestock_type_value)
                        else:
                            product.livestock_type = LivestockType.objects.get(name=livestock_type_value)
                    except (LivestockType.DoesNotExist, ValueError):
                        product.livestock_type = None
                else:
                    product.livestock_type = None
                    
                if approval.category:
                    try:
                        category_value = str(approval.category).strip("'\"")
                        # IDか名前かを判定
                        if category_value.isdigit():
                            product.category = Category.objects.get(id=category_value)
                        else:
                            product.category = Category.objects.get(name=category_value)
                    except (Category.DoesNotExist, ValueError):
                        product.category = None
                else:
                    product.category = None
                    
                if approval.manufacturer:
                    try:
                        manufacturer_value = str(approval.manufacturer).strip("'\"")
                        # IDか名前かを判定
                        if manufacturer_value.isdigit():
                            product.manufacturer = Manufacturer.objects.get(id=manufacturer_value)
                        else:
                            product.manufacturer = Manufacturer.objects.get(name=manufacturer_value)
                    except (Manufacturer.DoesNotExist, ValueError):
                        product.manufacturer = None
                else:
                    product.manufacturer = None
                product.product_name = approval.product_name
                product.model_number = approval.model_number
                product.specification = approval.specification
                product.shipping_unit = approval.shipping_unit
                product.remarks = approval.remarks
                product.status = ''
                product.approver = get_current_user()
                product.save()
                
                # キーワードを再生成
                from dashboard.products_master.product_services import update_product_keywords
                update_product_keywords(product)
                
                # 価格履歴を更新し、新規粗利率をテーブルに登録
                from dashboard.products_master.models import ProductGrossMarginRate
                for approval_history in approval.price_histories.filter(is_active=True):
                    if approval_history.is_delete_request:
                        # 削除申請の場合
                        PriceHistory.objects.filter(
                            product=product,
                            effective_year_month=approval_history.effective_year_month,
                            is_active=True
                        ).update(is_active=False)
                        
                        # 該当年度の有効履歴が空になる場合は粗利テーブルも削除
                        remaining_count = PriceHistory.objects.filter(
                            product=product,
                            period_year=approval_history.period_year,
                            is_active=True
                        ).count()
                        if remaining_count == 0:
                            ProductGrossMarginRate.objects.filter(
                                product=product,
                                period_year=approval_history.period_year
                            ).delete()
                    else:
                        # 今回申請したレコードかどうかを判定（既存履歴との比較）
                        original_history = PriceHistory.objects.filter(
                            product=product,
                            effective_year_month=approval_history.effective_year_month,
                            is_active=True
                        ).first()
                        
                        is_new_or_changed = (
                            not original_history or  # 新規履歴
                            original_history.wholesale_price != approval_history.wholesale_price or  # 仕切価格変更
                            original_history.kenren_price != approval_history.kenren_price  # 県連価格変更
                        )
                        
                        # 更新または新規作成の場合（申請データの粗利率をそのまま使用）
                        history, created = PriceHistory.objects.get_or_create(
                            product=product,
                            effective_year_month=approval_history.effective_year_month,
                            is_active=True,
                            defaults={
                                'period_year': approval_history.period_year,
                                'gross_margin_rate': approval_history.gross_margin_rate,
                                'wholesale_price': approval_history.wholesale_price,
                                'kenren_price': approval_history.kenren_price,
                                'retail_price': approval_history.retail_price,
                                'shipping_fee': approval_history.shipping_fee,
                                'revision_amount': approval_history.revision_amount,
                                'revision_reason': approval_history.revision_reason,
                                'memo': approval_history.memo,
                            }
                        )
                        if not created:
                            # 既存の場合は更新（申請データの粗利率をそのまま使用）
                            history.period_year = approval_history.period_year
                            history.gross_margin_rate = approval_history.gross_margin_rate
                            history.wholesale_price = approval_history.wholesale_price
                            history.kenren_price = approval_history.kenren_price
                            history.retail_price = approval_history.retail_price
                            history.shipping_fee = approval_history.shipping_fee
                            history.revision_amount = approval_history.revision_amount
                            history.revision_reason = approval_history.revision_reason
                            history.memo = approval_history.memo
                            history.save()
                        else:
                            # 新規作成の場合もメモを設定
                            history.memo = approval_history.memo
                            history.save()
                        
                        # 今回申請したレコードで仕切金額と県連金額の両方がある場合のみ粗利率を再計算
                        if (is_new_or_changed and 
                            approval_history.wholesale_price and approval_history.wholesale_price != '都度見積' and 
                            approval_history.kenren_price):
                            try:
                                wholesale_num = float(str(approval_history.wholesale_price).replace(',', ''))
                                kenren_num = float(str(approval_history.kenren_price).replace(',', ''))
                                if wholesale_num > 0 and kenren_num > 0:
                                    # 新しい計算方式：仕切価格÷県連価格
                                    calculated_rate = wholesale_num / kenren_num
                                    # 小数点第2位まで、3位以下を切り捨て
                                    import math
                                    final_rate = Decimal(str(math.floor(calculated_rate * 100) / 100))
                                    
                                    # 既存レコードを削除してから新規作成
                                    ProductGrossMarginRate.objects.filter(
                                        product=product,
                                        period_year=approval_history.period_year
                                    ).delete()
                                    
                                    ProductGrossMarginRate.objects.create(
                                        product=product,
                                        period_year=approval_history.period_year,
                                        gross_margin_rate=final_rate,
                                        calculation_note='承認時計算'
                                    )
                            except (ValueError, TypeError, ZeroDivisionError):
                                pass
            else:
                # 新規商品の作成
                # 畜種と分類を外部キーオブジェクトに変換
                livestock_type_obj = None
                if approval.livestock_type:
                    try:
                        livestock_type_value = str(approval.livestock_type).strip("'\"")
                        # IDか名前かを判定
                        if livestock_type_value.isdigit():
                            livestock_type_obj = LivestockType.objects.get(id=livestock_type_value)
                        else:
                            livestock_type_obj = LivestockType.objects.get(name=livestock_type_value)
                    except (LivestockType.DoesNotExist, ValueError):
                        pass
                
                category_obj = None
                if approval.category:
                    try:
                        category_value = str(approval.category).strip("'\"")
                        # IDか名前かを判定
                        if category_value.isdigit():
                            category_obj = Category.objects.get(id=category_value)
                        else:
                            category_obj = Category.objects.get(name=category_value)
                    except (Category.DoesNotExist, ValueError):
                        pass
                
                manufacturer_obj = None
                if approval.manufacturer:
                    try:
                        manufacturer_value = str(approval.manufacturer).strip("'\"")
                        # IDか名前かを判定
                        if manufacturer_value.isdigit():
                            manufacturer_obj = Manufacturer.objects.get(id=manufacturer_value)
                        else:
                            manufacturer_obj = Manufacturer.objects.get(name=manufacturer_value)
                    except (Manufacturer.DoesNotExist, ValueError):
                        pass
                
                product = Product.objects.create(
                    product_code=approval.product_code,
                    livestock_type=livestock_type_obj,
                    category=category_obj,
                    manufacturer=manufacturer_obj,
                    product_name=approval.product_name,
                    model_number=approval.model_number,
                    specification=approval.specification,
                    shipping_unit=approval.shipping_unit,
                    remarks=approval.remarks,
                    status='',
                    approver=get_current_user()
                )
                
                # キーワードを再生成
                from dashboard.products_master.product_services import update_product_keywords
                update_product_keywords(product)
                
                # 価格履歴を作成し、新規粗利率をテーブルに登録
                from dashboard.products_master.models import ProductGrossMarginRate
                for approval_history in approval.price_histories.filter(is_active=True):
                    if not approval_history.is_delete_request:
                        # 新規商品の価格履歴作成（申請データの粗利率をそのまま使用）
                        PriceHistory.objects.create(
                            product=product,
                            period_year=approval_history.period_year,
                            effective_year_month=approval_history.effective_year_month,
                            gross_margin_rate=approval_history.gross_margin_rate,
                            wholesale_price=approval_history.wholesale_price,
                            kenren_price=approval_history.kenren_price,
                            retail_price=approval_history.retail_price,
                            shipping_fee=approval_history.shipping_fee,
                            revision_amount=approval_history.revision_amount,
                            revision_reason=approval_history.revision_reason,
                            memo=approval_history.memo,
                        )
                        
                        # 申請データに仕切金額と県連金額の両方がある場合は粗利率を再計算してテーブル更新
                        if (approval_history.wholesale_price and approval_history.wholesale_price != '都度見積' and 
                            approval_history.kenren_price):
                            try:
                                wholesale_num = float(str(approval_history.wholesale_price).replace(',', ''))
                                kenren_num = float(str(approval_history.kenren_price).replace(',', ''))
                                if wholesale_num > 0 and kenren_num > 0:
                                    # 新しい計算方式：仕切価格÷県連価格
                                    calculated_rate = wholesale_num / kenren_num
                                    # 小数点第2位まで、3位以下を切り捨て
                                    import math
                                    final_rate = Decimal(str(math.floor(calculated_rate * 100) / 100))
                                    
                                    # 既存レコードを削除してから新規作成
                                    ProductGrossMarginRate.objects.filter(
                                        product=product,
                                        period_year=approval_history.period_year
                                    ).delete()
                                    
                                    ProductGrossMarginRate.objects.create(
                                        product=product,
                                        period_year=approval_history.period_year,
                                        gross_margin_rate=final_rate,
                                        calculation_note='承認時計算'
                                    )
                            except (ValueError, TypeError, ZeroDivisionError):
                                pass
            
            # 承認テーブルから削除
            approval.delete()
            
    except Exception as e:
        raise

def approve_application(request, pk):
    """申請を承認"""
    if request.method != 'POST':
        messages.error(request, '無効なリクエストです')
        return redirect('products_master:approval_list')
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 自己承認チェック
        current_user = get_current_user()
        if approval.applicant == current_user:
            messages.error(request, '自分が申請したデータは承認できません')
            return redirect('products_master:approval_detail', pk=pk)
        
        _process_approval(approval)
        print(f"Debug: Approval {pk} processing completed successfully")
        messages.success(request, '承認完了')
        return redirect('products_master:approval_list')
        
    except Exception as e:
        import traceback
        print(f"ERROR in approve_application: {traceback.format_exc()}")
        messages.error(request, 'エラーが発生しました')
        return redirect('products_master:approval_list')

def reject_application(request, pk):
    """申請を却下（再申請待ちに変更）"""
    if request.method != 'POST':
        messages.error(request, '無効なリクエストです')
        return redirect('products_master:approval_list')
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 申請種別を「再申請待ち」に変更
        approval.status = '再申請待ち'
        approval.save()
        
        # 申請却下時は商品マスタのステータスはそのまま（申請中を維持）
        
        messages.warning(request, '申請を却下しました。再申請待ちに変更されました。')
        return redirect('products_master:approval_list')
    except Exception as e:
        messages.error(request, 'エラーが発生しました')
        return redirect('products_master:approval_list')

def cancel_application(request, pk):
    """申請を取消（完全削除）"""
    if request.method != 'POST':
        messages.error(request, '無効なリクエストです')
        return redirect('products_master:approval_list')
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 既存商品の場合はステータスをクリア
        if approval.product_number > 0:
            try:
                product = Product.objects.get(pk=approval.product_number)
                product.status = ''
                product.save()
            except Product.DoesNotExist:
                pass
        
        approval.delete()
        messages.success(request, '申請取消完了')
        return redirect('products_master:approval_list')
    except Exception as e:
        messages.error(request, 'エラーが発生しました')
        return redirect('products_master:approval_list')



def validate_form_data(request, product=None):
    """共通フォームバリデーション"""
    # 商品情報の取得
    product_name_raw = request.POST.get('product_name', '')
    
    product_data = {
        'product_code': (request.POST.get('product_code', '') or '').strip() if isinstance(request.POST.get('product_code', ''), str) else str(request.POST.get('product_code', '') or ''),
        'livestock_type': str(request.POST.get('livestock_type', '') or ''),
        'category': str(request.POST.get('category', '') or ''),
        'manufacturer': str(request.POST.get('manufacturer', '') or ''),
        'product_name': normalize_product_name((product_name_raw or '').strip() if isinstance(product_name_raw, str) else str(product_name_raw or '')),
        'model_number': (request.POST.get('model_number', '') or '').strip() if isinstance(request.POST.get('model_number', ''), str) else str(request.POST.get('model_number', '') or ''),
        'specification': (request.POST.get('specification', '') or '').strip() if isinstance(request.POST.get('specification', ''), str) else str(request.POST.get('specification', '') or ''),
        'shipping_unit': (request.POST.get('shipping_unit', '') or '').strip() if isinstance(request.POST.get('shipping_unit', ''), str) else str(request.POST.get('shipping_unit', '') or ''),

        'remarks': (request.POST.get('remarks', '') or '').strip() if isinstance(request.POST.get('remarks', ''), str) else str(request.POST.get('remarks', '') or '')
    }
    
    # 新規価格履歴の取得
    new_histories = []
    for key, value in request.POST.items():
        if key.startswith('new_effective_year_month_') and value.strip():
            index = key.split('_')[-1]
            effective_year_month = value.strip()
            wholesale_price = request.POST.get(f'new_wholesale_price_{index}', '').strip()
            kenren_price = request.POST.get(f'new_kenren_price_{index}', '').strip()
            retail_price = request.POST.get(f'new_retail_price_{index}', '').strip()
            shipping_fee = request.POST.get(f'new_shipping_fee_{index}', '').strip()
            revision_reason = request.POST.get(f'new_revision_reason_{index}', '').strip()
            memo = request.POST.get(f'new_memo_{index}', '').strip()
            
            new_histories.append({
                'effective_year_month': effective_year_month,
                'wholesale_price': wholesale_price,
                'kenren_price': kenren_price,
                'retail_price': retail_price,
                'shipping_fee': shipping_fee,
                'revision_reason': revision_reason,
                'memo': memo
            })
    
    # バリデーション実行
    errors = []
    
    # 商品名は必須
    product_name_value = product_data['product_name'].strip() if product_data['product_name'] else ''
    if not product_name_value:
        errors.append('商品名は必須です')
    
    # 畜種は必須
    if not product_data['livestock_type']:
        errors.append('畜種は必須です')
    
    # 分類は必須
    if not product_data['category']:
        errors.append('分類は必須です')
    
    # メーカーは必須
    if not product_data['manufacturer']:
        errors.append('メーカーは必須です')
    
    # 商品コードのバリデーション（未入力または9桁の数字のみ）
    product_code = product_data['product_code'].strip()
    if product_code:
        if not (product_code.isdigit() and len(product_code) == 9):
            errors.append('商品コードは9桁の数字で入力してください')
    
    # 新規価格履歴のバリデーション
    validated_dates = []
    for history in new_histories:
        try:
            formatted_date = validate_date_format(history['effective_year_month'])
            check_business_rules(formatted_date, product, validated_dates)
            validated_dates.append(formatted_date)
            
            # 粗利率算定バリデーション
            if '/' in history['effective_year_month']:
                year, month = map(int, history['effective_year_month'].split('/'))
                period_year = year if month >= 4 else year - 1
                determine_gross_margin_rate(product, period_year, history['wholesale_price'] or '都度見積', request)
        except ValueError as e:
            errors.append(str(e))
    
    if errors:
        error_msg = '; '.join(errors)
        raise ValueError(error_msg)
    
    return product_data, new_histories

def _update_reapplication(request, approval):
    """再申請待ちデータの更新処理"""
    print(f"=== _update_reapplication called ===")
    print(f"POST keys: {list(request.POST.keys())}")
    
    try:
        # 申請処理か保存処理か判定
        if 'submit_approval' in request.POST:
            print("Processing reapplication submission...")
            
            try:
                # バリデーション実行
                product_obj = Product.objects.get(pk=approval.product_number) if approval.product_number > 0 else None
                product_data, new_histories = validate_form_data(request, product_obj)
                
                # 商品情報を更新
                for field, value in product_data.items():
                    setattr(approval, field, value)
                
                # 既存価格履歴のメモを保持
                for key, value in request.POST.items():
                    if key.startswith('edit_memo_') and value.strip():
                        history_id = key.split('_')[-1]
                        try:
                            history = approval.price_histories.get(pk=history_id)
                            history.memo = value.strip()
                            history.save()
                        except Exception:
                            pass
                
                # 新規履歴を追加
                existing_approval_dates = list(approval.price_histories.values_list('effective_year_month', flat=True))
                for history in new_histories:
                    year, month = map(int, history['effective_year_month'].split('/'))
                    period_year = year if month >= 4 else year - 1
                    effective_year_month = f"{year:04d}/{month:02d}"
                    
                    check_business_rules(effective_year_month, product_obj, existing_approval_dates)
                    existing_approval_dates.append(effective_year_month)
                    
                    gross_margin_rate = determine_gross_margin_rate(product_obj, period_year, history['wholesale_price'] or '都度見積', request)
                    
                    PriceHistoryApproval.objects.create(
                        product=approval,
                        period_year=period_year,
                        effective_year_month=effective_year_month,
                        gross_margin_rate=gross_margin_rate,
                        wholesale_price=history['wholesale_price'] or '都度見積',
                        kenren_price=history['kenren_price'] if history['kenren_price'] else None,
                        revision_reason=history['revision_reason'],
                        memo=history['memo'],
                        applicant=get_current_user()
                    )
                
                # ステータスを申請中に変更
                approval.status = ''
                approval.save()
                
                return HttpResponse('<script>alert("再申請完了");location.href="/products/approvals/";</script>')
            except ValueError as e:
                return HttpResponse(f'<script>alert("{str(e)}");history.back();</script>', status=400)
        else:
            print("Processing save operation...")
            
            # 共通バリデーションを使用
            try:
                print(f"Getting product with pk={approval.product_number}")
                product_obj = Product.objects.get(pk=approval.product_number) if approval.product_number > 0 else None
                print(f"Product found: {product_obj}")
                product_data, new_histories = validate_form_data(request, product_obj)
                print(f"Validation passed: {len(new_histories)} new histories")
            except ValueError as e:
                print(f"Validation error in save: {str(e)}")
                return JsonResponse({'success': False, 'message': str(e)})
            except Product.DoesNotExist:
                print(f"Product not found: pk={approval.product_number}")
                return JsonResponse({'success': False, 'message': '商品が見つかりません'})
            except Exception as e:
                print(f"Unexpected error in save validation: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return JsonResponse({'success': False, 'message': f'エラーが発生しました: {str(e)}'})
            
            # 商品情報の更新
            print("Updating product data...")
            for field, value in product_data.items():
                setattr(approval, field, value)
            
            approval.save()
            print("Product data updated successfully")
            
            # 価格履歴の更新処理
            for key, value in request.POST.items():
                if key.startswith('edit_') and value.strip():
                    parts = key.split('_')
                    if len(parts) >= 3:
                        field = '_'.join(parts[1:-1])
                        history_id = parts[-1]
                        
                        try:
                            history = approval.price_histories.get(pk=history_id)
                            if field in ['kenren_price', 'memo', 'revision_reason', 'wholesale_price', 'retail_price']:
                                setattr(history, field, value.strip())
                                history.save()
                                print(f"Updated price history {history_id}: {field} = {value.strip()}")
                        except Exception as e:
                            print(f"Error updating price history {history_id}: {e}")
            
            # 削除フラグの処理
            for key, value in request.POST.items():
                if key.startswith('delete_') and value == 'true':
                    history_id = key.split('_')[1]
                    try:
                        history = approval.price_histories.get(pk=history_id)
                        history.is_delete_request = True
                        history.save()
                        print(f"Marked price history {history_id} for deletion")
                    except Exception as e:
                        print(f"Error marking price history {history_id} for deletion: {e}")
            
            # 既存の申請履歴との重複チェック用のリストを準備
            
            # 新規価格履歴の追加処理
            existing_approval_dates = list(approval.price_histories.values_list('effective_year_month', flat=True))
            
            try:
                for history in new_histories:
                    year, month = map(int, history['effective_year_month'].split('/'))
                    period_year = year if month >= 4 else year - 1
                    effective_year_month = f"{year:04d}/{month:02d}"
                    
                    # ビジネスルールチェック（重複防止）
                    try:
                        product_obj = Product.objects.get(pk=approval.product_number) if approval.product_number > 0 else None
                    except Product.DoesNotExist:
                        product_obj = None
                    check_business_rules(effective_year_month, product_obj, existing_approval_dates)
                    existing_approval_dates.append(effective_year_month)
                    
                    # 粗利率を算定（再申請時は申請データから取得）
                    try:
                        gross_margin_rate = determine_gross_margin_rate(
                            product_obj,
                            period_year,
                            history['wholesale_price'] or '都度見積',
                            request
                        )
                    except ValueError:
                        # 商品が存在しない場合は申請データから取得
                        existing_history = approval.price_histories.filter(is_active=True).first()
                        if existing_history:
                            gross_margin_rate = existing_history.gross_margin_rate
                        else:
                            gross_margin_rate = Decimal('1.1')  # デフォルト値
                    
                    PriceHistoryApproval.objects.create(
                        product=approval,
                        period_year=period_year,
                        effective_year_month=effective_year_month,
                        gross_margin_rate=gross_margin_rate,
                        wholesale_price=history['wholesale_price'] or '都度見積',
                        kenren_price=history['kenren_price'] if history['kenren_price'] else None,
                        revision_reason=history['revision_reason'],
                        memo=history['memo'],
                        applicant=get_current_user()
                    )
                    print(f"Added new price history: {effective_year_month}")
            except ValueError as e:
                return JsonResponse({'success': False, 'message': str(e)})
            
            print("Save completed successfully")
            response = JsonResponse({'success': True, 'message': '保存完了'})
            print(f"Returning response: {response}")
            return response
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)})
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': f'システムエラーが発生しました: {str(e)}'})

def bulk_approve(request):
    """選択式一括承認"""
    if request.method != 'POST':
        messages.error(request, '無効なリクエストです')
        return redirect('products_master:approval_list')
    
    try:
        approval_ids = request.POST.getlist('approval_ids')
        if not approval_ids:
            messages.error(request, '承認する項目が選択されていません')
            return redirect('products_master:approval_list')
        
        current_user = get_current_user()
        approved_count = 0
        error_count = 0
        error_messages = []
        
        for approval_id in approval_ids:
            try:
                approval = ProductApproval.objects.get(pk=approval_id, is_active=True)
                
                # 自己承認チェック
                if approval.applicant == current_user:
                    error_count += 1
                    error_msg = f"ID {approval_id}: 自分が申請したデータは承認できません"
                    error_messages.append(error_msg)
                    print(f"Error: {error_msg}")
                    continue
                
                _process_approval(approval)
                approved_count += 1
                print(f"Successfully approved: {approval_id}")
            except ProductApproval.DoesNotExist:
                error_count += 1
                error_msg = f"ID {approval_id}: 申請が見つかりません"
                error_messages.append(error_msg)
                print(f"Error: {error_msg}")
            except Exception as e:
                error_count += 1
                error_msg = f"ID {approval_id}: {str(e)}"
                error_messages.append(error_msg)
                print(f"Error: {error_msg}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        
        if error_count > 0:
            # エラー詳細をコンソールに出力
            print(f"Bulk approval errors ({error_count} errors):")
            for error_msg in error_messages:
                print(f"  - {error_msg}")
            
            if approved_count == 0:
                # 全てエラーの場合
                messages.error(request, '選択した申請は承認できませんでした。自分が申請したデータは承認できません。')
            else:
                # 一部エラーの場合
                messages.warning(request, f'{approved_count}件を承認しました。{error_count}件はエラーでした。')
        else:
            messages.success(request, f'{approved_count}件を一括承認しました')
        
        return redirect('products_master:approval_list')
        
    except Exception as e:
        messages.error(request, 'エラーが発生しました')
        return redirect('products_master:approval_list')

def api_manufacturers(request):
    """メーカーリストAPI"""
    manufacturers = list(Manufacturer.objects.filter(is_active=True).values('id', 'name'))
    return JsonResponse(manufacturers, safe=False)

def _get_dynamic_breadcrumbs_for_new(request):
    """新規作成画面の動的パンくずリスト"""
    referer = request.META.get('HTTP_REFERER', '')
    
    if 'integrated-pricelist' in referer:
        # デジタル価格表から来た場合
        return get_breadcrumbs('product_new', 
                              from_page_title='デジタル価格表', 
                              from_page_url='/products/integrated-pricelist/')
    else:
        # 商品一覧から来た場合（デフォルト）
        return get_breadcrumbs('product_new')

def api_gross_margins(request, pk):
    """粗利率管理API"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'GET':
        from dashboard.products_master.models import ProductGrossMarginRate
        
        margins = list(ProductGrossMarginRate.objects.filter(
            product=product
        ).values('period_year', 'gross_margin_rate', 'calculation_note').order_by('-period_year'))
        return JsonResponse(margins, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            margins_data = data.get('margins', [])
            
            from dashboard.products_master.models import ProductGrossMarginRate
            
            # 既存の粗利率を削除
            ProductGrossMarginRate.objects.filter(product=product).delete()
            
            # 新しい粗利率を保存
            for margin_data in margins_data:
                ProductGrossMarginRate.objects.create(
                    product=product,
                    period_year=margin_data['period_year'],
                    gross_margin_rate=Decimal(str(margin_data['gross_margin_rate'])),
                    calculation_note='手動設定'
                )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})

