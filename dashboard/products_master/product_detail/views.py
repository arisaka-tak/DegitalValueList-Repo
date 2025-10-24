import json
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from dashboard.products_master.models import Product, PriceHistory, ProductApproval, PriceHistoryApproval
from django.db.models import Q
from decimal import Decimal
from dashboard.products_master.forms import ProductForm
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs
from django.views.decorators.csrf import csrf_exempt

def product_detail(request, pk):
    """商品詳細画面"""
    print(f"=== product_detail called: method={request.method}, pk={pk} ===")
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
            'gross_margin_rate': str(history.gross_margin_rate) if history.gross_margin_rate else None,
            'revision_amount': history.get_revision_amount(),
            'revision_reason': history.revision_reason or '',
            'is_editable': history.is_editable()
        }
        for history in price_histories
    ])
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'form': form,
        'price_histories': price_histories,
        'price_histories_json': price_histories_json,
        'breadcrumbs': get_breadcrumbs('product_detail', product_name=product.product_name)
    }
    return render(request, 'products_master/product_detail.html', context)

def save_product_and_histories(request, product=None):
    """商品情報と価格履歴を一括保存"""
    print("=== save_product_and_histories START ===")
    try:
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
                    
                    PriceHistory.objects.create(
                        product=product,
                        period_year=period_year,
                        effective_year_month=effective_year_month,
                        wholesale_price=wholesale_price or '\u90fd\u5ea6\u898b\u7a4d',
                        gross_margin_rate=1.1,
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
        
        # 4. 削除処理
        print(f"=== 削除処理開始 ===")
        for key, value in request.POST.items():
            if key.startswith('delete_'):
                print(f"Found delete key: {key} = {value}")
                if value == 'true':
                    print(f"Delete history: {key} = {value}")
                    history_id = key.split('_')[1]
                    try:
                        history = PriceHistory.objects.get(pk=history_id, product=product)
                        print(f"Found history {history_id}: {history.effective_year_month}")
                        print(f"is_deletable: {history.is_deletable()}")
                        if history.is_deletable():
                            history.is_active = False
                            history.save()
                            print(f"Successfully deleted history {history_id}")
                        else:
                            print(f"History {history_id} is not deletable")
                    except (PriceHistory.DoesNotExist, ValueError) as e:
                        print(f"History {history_id} delete error: {e}")
        
        print("=== 削除処理終了 ===")
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
    copy_from_id = request.GET.get('copy_from')
    
    if request.method == 'POST':
        # 申請処理
        return submit_approval(request, None)
    else:
        # コピー元がある場合はその情報で初期化
        if copy_from_id:
            try:
                original_product = Product.objects.get(pk=copy_from_id)
                initial_data = {
                    'product_code': original_product.product_code,
                    'livestock_type': original_product.livestock_type,
                    'category': original_product.category,
                    'manufacturer': original_product.manufacturer,
                    'product_name': original_product.product_name,
                    'model_number': original_product.model_number,
                    'specification': original_product.specification,
                    'shipping_unit': original_product.shipping_unit,
                    'shipping_fee': original_product.shipping_fee,
                    'remarks': original_product.remarks,
                }
                form = ProductForm(initial=initial_data)
            except Product.DoesNotExist:
                form = ProductForm()
        else:
            form = ProductForm()
    
    context = {
        'current_user': get_current_user(),
        'product': None,  # 新規作成モード
        'form': form,
        'price_histories': [],  # 空の価格履歴
        'price_histories_json': '[]',  # 空のJSON配列
        'is_new': True,  # 新規作成フラグ
        'breadcrumbs': get_breadcrumbs('product_new')
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
            
            price_history = PriceHistory.objects.create(
                product=product,
                period_year=period_year,
                effective_year_month=effective_year_month,
                wholesale_price=wholesale_price,
                kenren_price=kenren_price if kenren_price else None,
                revision_reason=revision_reason if revision_reason else None,
                gross_margin_rate=1.1,
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
                'revision_reason': revision_reason if revision_reason else history.revision_reason,
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

def submit_approval(request, pk=None):
    """申請テーブルにデータをコピー"""
    try:
        print(f"=== submit_approval called: pk={pk}, method={request.method} ===")
        print(f"Request path: {request.path}")
        print(f"POST data keys: {list(request.POST.keys())}")
        
        # 重複申請チェック用のログ
        existing_approvals = ProductApproval.objects.filter(is_active=True)
        print(f"Existing approvals count: {existing_approvals.count()}")
        for approval in existing_approvals:
            print(f"  - Approval {approval.pk}: {approval.product_name} (product_number: {approval.product_number})")
        
        if pk:
            product = get_object_or_404(Product, pk=pk)
            # ステータスが空でない商品は多重申請を禁止
            if product.status:
                return HttpResponse('<script>alert("この商品は既に申請中です");history.back();</script>')
        else:
            product = None
        
        # 商品情報を取得
        if product:
            form = ProductForm(request.POST, instance=product)
        else:
            form = ProductForm(request.POST)
        
        if not form.is_valid():
            # エラー時にフォームを再表示（入力値とエラー情報付き）
            # POSTデータから価格履歴を復元
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
                'product': None,
                'form': form,  # エラー情報と入力値を含む
                'price_histories': [],
                'preview_histories': preview_histories,
                'is_new': True,
                'breadcrumbs': [
                    {'title': '商品マスタ管理', 'url': '/products/'},
                    {'title': '商品一覧', 'url': '/products/products/'},
                    {'title': '新規作成', 'url': None}
                ]
            }
            return render(request, 'products_master/product_detail.html', context)
        
        # 日付バリデーション
        print("=== 日付バリデーション開始 ===")
        validated_dates = []  # 同一申請内での重複チェック用
        
        for key, value in request.POST.items():
            if key.startswith('new_effective_year_month_') and value.strip():
                try:
                    formatted_date = validate_date_format(value.strip())
                    check_business_rules(formatted_date, product, validated_dates)
                    validated_dates.append(formatted_date)
                except ValueError as e:
                    return _return_form_with_error(request, product, form, str(e))
        
        # 粗利率算定バリデーション
        print("=== 粗利率算定バリデーション開始 ===")
        for key, value in request.POST.items():
            if key.startswith('new_effective_year_month_') and value.strip():
                index = key.split('_')[-1]
                wholesale_price = request.POST.get(f'new_wholesale_price_{index}', '').strip()
                
                if '/' in value:
                    year, month = map(int, value.split('/'))
                    period_year = year if month >= 4 else year - 1
                    
                    try:
                        calculate_gross_margin_rate(product, period_year, wholesale_price or '都度見積', request)
                    except ValueError as e:
                        return _return_form_with_error(request, product, form, str(e))
        
        print("=== バリデーション完了 ===")
        
        # 申請テーブルに商品情報をコピー
        if product:
            # 既存商品の場合
            temp_product_number = product.product_number
            # 商品マスタ側のステータスのみ「申請中」に更新（商品情報は更新しない）
            Product.objects.filter(pk=product.pk).update(status='申請中', approver='')
        else:
            # 新規商品の場合は仮番号を自動採番
            last_temp = ProductApproval.objects.filter(product_number__lt=0).order_by('product_number').first()
            temp_product_number = (last_temp.product_number - 1) if last_temp else -1
            print(f"New product temp number: {temp_product_number} (last_temp: {last_temp.product_number if last_temp else 'None'})")
        
        # 申請テーブルに商品情報をコピー
        if product:
            # 既存商品の場合はフォームデータを使用（申請内容）
            approval_product = ProductApproval.objects.create(
                product_number=temp_product_number,
                product_code=form.cleaned_data.get('product_code'),
                livestock_type=form.cleaned_data.get('livestock_type'),
                category=form.cleaned_data.get('category'),
                manufacturer=form.cleaned_data.get('manufacturer'),
                product_name=form.cleaned_data.get('product_name'),
                model_number=form.cleaned_data.get('model_number'),
                specification=form.cleaned_data.get('specification'),
                shipping_unit=form.cleaned_data.get('shipping_unit'),
                shipping_fee=form.cleaned_data.get('shipping_fee'),
                remarks=form.cleaned_data.get('remarks'),
                applicant=get_current_user()
            )
        else:
            # 新規商品の場合はフォームデータを使用
            approval_product = ProductApproval.objects.create(
                product_number=temp_product_number,
                product_code=form.cleaned_data.get('product_code'),
                livestock_type=form.cleaned_data.get('livestock_type'),
                category=form.cleaned_data.get('category'),
                manufacturer=form.cleaned_data.get('manufacturer'),
                product_name=form.cleaned_data.get('product_name'),
                model_number=form.cleaned_data.get('model_number'),
                specification=form.cleaned_data.get('specification'),
                shipping_unit=form.cleaned_data.get('shipping_unit'),
                shipping_fee=form.cleaned_data.get('shipping_fee'),
                remarks=form.cleaned_data.get('remarks'),
                applicant=get_current_user()
            )
        print(f"Created ProductApproval: pk={approval_product.pk}, product_number={approval_product.product_number}, name={approval_product.product_name}")
        
        # 価格履歴を申請テーブルにコピー
        if product:
            # 既存商品の場合
            for history in product.price_histories.filter(is_active=True):
                # 更新内容をチェック
                wholesale_price = request.POST.get(f'edit_wholesale_price_{history.pk}', '').strip()
                kenren_price = request.POST.get(f'edit_kenren_price_{history.pk}', '').strip()
                revision_reason = request.POST.get(f'edit_revision_reason_{history.pk}', '').strip()
                delete_flag = request.POST.get(f'delete_{history.pk}', 'false')
                
                PriceHistoryApproval.objects.create(
                    product=approval_product,
                    period_year=history.period_year,
                    effective_year_month=history.effective_year_month,
                    gross_margin_rate=history.gross_margin_rate,
                    wholesale_price=wholesale_price if wholesale_price else history.wholesale_price,
                    kenren_price=kenren_price if kenren_price else history.kenren_price,
                    retail_price=history.retail_price,
                    revision_amount=0,
                    revision_reason=revision_reason if revision_reason else history.revision_reason,
                    is_delete_request=(delete_flag == 'true'),
                    applicant=get_current_user()
                )
        
        # 新規履歴を申請テーブルに追加
        print("=== 新規履歴の申請テーブル追加開始 ===")
        for key, value in request.POST.items():
            if key.startswith('new_effective_year_month_') and value.strip():
                print(f"Found new history: {key} = {value}")
                index = key.split('_')[-1]
                effective_year_month = value.strip()
                wholesale_price = request.POST.get(f'new_wholesale_price_{index}', '').strip()
                kenren_price = request.POST.get(f'new_kenren_price_{index}', '').strip()
                revision_reason = request.POST.get(f'new_revision_reason_{index}', '').strip()
                print(f"Index: {index}, wholesale: {wholesale_price}, kenren: {kenren_price}")
                
                if '/' in effective_year_month:
                    year, month = map(int, effective_year_month.split('/'))
                    period_year = year if month >= 4 else year - 1
                    effective_year_month = f"{year:04d}/{month:02d}"
                    
                    # 粗利率を再算定（既に事前チェック済みなのでエラーは発生しないはず）
                    gross_margin_rate = calculate_gross_margin_rate(product, period_year, wholesale_price or '都度見積', request)
                    
                    print(f"Creating PriceHistoryApproval: {effective_year_month}")
                    PriceHistoryApproval.objects.create(
                        product=approval_product,
                        period_year=period_year,
                        effective_year_month=effective_year_month,
                        gross_margin_rate=gross_margin_rate,
                        wholesale_price=wholesale_price or '都度見積',
                        kenren_price=kenren_price if kenren_price else None,
                        revision_amount=0,
                        revision_reason=revision_reason,
                        applicant=get_current_user()
                    )
                    print(f"Successfully created PriceHistoryApproval for {effective_year_month}")
        
        print(f"=== submit_approval completed successfully ===")
        return HttpResponse('<script>alert("申請完了");location.href="/products/products/";</script>')
        
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return HttpResponse('<script>alert("エラー発生");</script>', status=500)

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
    """ビジネスルールのチェック"""
    if existing_dates is None:
        existing_dates = []
    
    year, month = map(int, formatted_date.split('/'))
    
    # 既存商品の場合のチェック
    if product:
        temp_history = PriceHistory(product=product, effective_year_month=formatted_date)
        if not temp_history.is_editable():
            from datetime import datetime
            today = datetime.now().strftime('%Y/%m')
            latest_editable = PriceHistory.objects.filter(
                product=product, effective_year_month__lt=today, is_active=True
            ).order_by('-effective_year_month').first()
            
            if latest_editable:
                raise ValueError(f'編集不可な範囲の日付です。{latest_editable.effective_year_month}より後の日付を入力してください。')
            else:
                raise ValueError('編集不可な範囲の日付です。')
        
        if PriceHistory.objects.filter(product=product, effective_year_month=formatted_date, is_active=True).exists():
            raise ValueError(f'{formatted_date}の価格履歴は既に存在します。')
    
    # 2年度以上先の登録禁止
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_period_year = current_year if current_month >= 4 else current_year - 1
    input_period_year = year if month >= 4 else year - 1
    
    if input_period_year > current_period_year + 1:
        raise ValueError(f'{input_period_year}年度は2年度以上先のため登録できません。')
    
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
                'gross_margin_rate': str(history.gross_margin_rate) if history.gross_margin_rate else None,
                'revision_amount': history.get_revision_amount(),
                'revision_reason': history.revision_reason or '',
                'is_editable': history.is_editable()
            }
            for history in price_histories
        ])
    else:
        price_histories = []
        price_histories_json = '[]'
    
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
        'preview_histories': preview_histories,
        'is_new': not bool(product),
        'error_message': error_message,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': '新規作成' if not product else f'{product.product_name}', 'url': None}
        ]
    }
    return render(request, 'products_master/product_detail.html', context)

def calculate_gross_margin_rate(product, period_year, wholesale_price, request=None):
    """粗利率を算定（シンプル版）"""
    from dashboard.products_master.models import ProductGrossMarginRate, PriceHistory
    
    # 現在入力されている県連価格を取得
    current_kenren_price = None
    if request:
        for key, value in request.POST.items():
            if key.startswith('new_wholesale_price_') and value.strip() == wholesale_price:
                current_index = key.split('_')[-1]
                kenren_value = request.POST.get(f'new_kenren_price_{current_index}', '').strip()
                if kenren_value:
                    try:
                        current_kenren_price = float(kenren_value.replace(',', ''))
                    except (ValueError, AttributeError):
                        pass
                break
    
    # ①県連価格が入力されている場合はチェック終了
    if current_kenren_price is not None:
        return Decimal('1.0')  # 仮の値（実際は使用されない）
    
    # ②県連価格が未入力の場合は粗利テーブルの登録確認
    if product:
        try:
            margin_rate_record = ProductGrossMarginRate.objects.get(
                product=product,
                period_year=period_year
            )
            return margin_rate_record.gross_margin_rate
        except ProductGrossMarginRate.DoesNotExist:
            pass
    
    # 仕切価格のチェック
    try:
        wholesale_numeric = float(wholesale_price.replace(',', ''))
    except (ValueError, AttributeError):
        raise ValueError('仕切価格が数字でない場合、県連価格は手入力してください。')
    
    # 粗利テーブルに未登録の場合は過去の県連価格から算出
    if product and wholesale_numeric > 0:
        # 過去の価格履歴を取得（手入力・自動計算どちらでも）
        past_history = PriceHistory.objects.filter(
            product=product,
            period_year__lt=period_year,
            is_active=True
        ).order_by('-period_year', '-effective_year_month').first()
        
        if past_history:
            try:
                # 手入力の県連価格がある場合
                if past_history.kenren_price:
                    past_kenren_price = float(str(past_history.kenren_price).replace(',', ''))
                else:
                    # 自動計算された県連価格を使用
                    past_wholesale = float(str(past_history.wholesale_price).replace(',', '')) if past_history.wholesale_price != '都度見積' else None
                    if past_wholesale and past_history.gross_margin_rate:
                        past_kenren_price = past_wholesale * float(past_history.gross_margin_rate)
                    else:
                        raise ValueError('過去の価格データが不完全')
                
                calculated_rate = past_kenren_price / wholesale_numeric
                gross_margin_rate = Decimal(str(round(calculated_rate, 6)))
                
                # 粗利率が1.0以下の場合は警告
                if gross_margin_rate <= 1.0:
                    raise ValueError('仕切価格が県連価格より高い状態です。登録してもよいですか？')
                
                return gross_margin_rate
            except (ValueError, TypeError):
                pass
    
    # 過去の県連価格がない場合は手入力必須エラー
    raise ValueError(f'{period_year}年度の粗利率が未設定です。仕切価格・県連価格を手入力してください。')

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
    price_histories = approval.price_histories.filter(is_active=True).order_by('-effective_year_month')
    
    # 元データとの差分を計算
    original_product = None
    if approval.product_number > 0:
        try:
            original_product = Product.objects.get(product_number=approval.product_number)
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
            'shipping_fee': approval.shipping_fee != original_product.shipping_fee,
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
                    'revision_reason': history.revision_reason != original_history.revision_reason,
                }
            else:
                # 新規履歴は全て差分
                history.diff_flags = {
                    'wholesale_price': True,
                    'kenren_price': True,
                    'revision_reason': True,
                }
        else:
            # 新規商品は全て差分
            history.diff_flags = {
                'wholesale_price': True,
                'kenren_price': True,
                'revision_reason': True,
            }
    
    context = {
        'current_user': get_current_user(),
        'approval': approval,
        'price_histories': price_histories,
        'diff_flags': diff_flags,
        'is_new_product': not bool(original_product),
        'breadcrumbs': get_breadcrumbs('approval_detail', product_name=approval.product_name)
    }
    return render(request, 'products_master/approval_detail.html', context)

def _process_approval(approval):
    """承認処理の共通ロジック"""
    if approval.product_number > 0:
        # 既存商品の更新
        product = Product.objects.get(product_number=approval.product_number)
        
        # 削除申請の場合は論理削除
        if approval.status == '削除申請':
            product.soft_delete()
            approval.delete()
            return
        
        # 商品情報を更新
        product.product_code = approval.product_code
        product.livestock_type = approval.livestock_type
        product.category = approval.category
        product.manufacturer = approval.manufacturer
        product.product_name = approval.product_name
        product.model_number = approval.model_number
        product.specification = approval.specification
        product.shipping_unit = approval.shipping_unit
        product.shipping_fee = approval.shipping_fee
        product.remarks = approval.remarks
        product.status = ''
        product.approver = get_current_user()
        product.save()
        
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
            else:
                # 更新または新規作成の場合
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
                        'revision_amount': approval_history.revision_amount,
                        'revision_reason': approval_history.revision_reason,
                    }
                )
                if not created:
                    # 既存の場合は更新
                    history.period_year = approval_history.period_year
                    history.gross_margin_rate = approval_history.gross_margin_rate
                    history.wholesale_price = approval_history.wholesale_price
                    history.kenren_price = approval_history.kenren_price
                    history.retail_price = approval_history.retail_price
                    history.revision_amount = approval_history.revision_amount
                    history.revision_reason = approval_history.revision_reason
                    history.save()
                
                # 新規粗利率をProductGrossMarginRateテーブルに登録（既存の場合はスキップ）
                if not ProductGrossMarginRate.objects.filter(
                    product=product,
                    period_year=approval_history.period_year
                ).exists():
                    ProductGrossMarginRate.objects.create(
                        product=product,
                        period_year=approval_history.period_year,
                        gross_margin_rate=approval_history.gross_margin_rate
                    )
    else:
        # 新規商品の作成
        product = Product.objects.create(
            product_code=approval.product_code,
            livestock_type=approval.livestock_type,
            category=approval.category,
            manufacturer=approval.manufacturer,
            product_name=approval.product_name,
            model_number=approval.model_number,
            specification=approval.specification,
            shipping_unit=approval.shipping_unit,
            shipping_fee=approval.shipping_fee,
            remarks=approval.remarks,
            status='',
            approver=get_current_user()
        )
        
        # 価格履歴を作成し、新規粗利率をテーブルに登録
        for approval_history in approval.price_histories.filter(is_active=True):
            PriceHistory.objects.create(
                product=product,
                period_year=approval_history.period_year,
                effective_year_month=approval_history.effective_year_month,
                gross_margin_rate=approval_history.gross_margin_rate,
                wholesale_price=approval_history.wholesale_price,
                kenren_price=approval_history.kenren_price,
                retail_price=approval_history.retail_price,
                revision_amount=approval_history.revision_amount,
                revision_reason=approval_history.revision_reason,
            )
            
            # 新規粗利率をProductGrossMarginRateテーブルに登録（既存の場合はスキップ）
            if not ProductGrossMarginRate.objects.filter(
                product=product,
                period_year=approval_history.period_year
            ).exists():
                ProductGrossMarginRate.objects.create(
                    product=product,
                    period_year=approval_history.period_year,
                    gross_margin_rate=approval_history.gross_margin_rate
                )
    
    # 承認テーブルから削除
    approval.delete()

def approve_application(request, pk):
    """申請を承認"""
    if request.method != 'POST':
        return HttpResponse('Invalid method', status=405)
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        _process_approval(approval)
        return HttpResponse('<script>alert("承認完了");location.href="/products/approvals/";</script>')
        
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return HttpResponse('<script>alert("エラー発生");</script>', status=500)

def reject_application(request, pk):
    """申請を却下"""
    if request.method != 'POST':
        return HttpResponse('Invalid method', status=405)
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 既存商品の場合はステータスをクリア
        if approval.product_number > 0:
            try:
                product = Product.objects.get(product_number=approval.product_number)
                product.status = ''
                product.save()
            except Product.DoesNotExist:
                pass
        
        approval.delete()
        return HttpResponse('<script>alert("却下完了");location.href="/products/approvals/";</script>')
    except Exception as e:
        return HttpResponse('<script>alert("エラー発生");</script>', status=500)



def bulk_approve(request):
    """一括承認"""
    if request.method != 'POST':
        return HttpResponse('Invalid method', status=405)
    
    try:
        approvals = ProductApproval.objects.filter(is_active=True)
        approved_count = 0
        
        for approval in approvals:
            try:
                _process_approval(approval)  # 共通処理を使用
                approved_count += 1
            except Exception:
                continue
        
        return HttpResponse(f'<script>alert("{approved_count}件を一括承認しました");location.reload();</script>')
        
    except Exception:
        return HttpResponse('<script>alert("エラー発生");</script>', status=500)

