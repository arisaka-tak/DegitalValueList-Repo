from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from dashboard.products_master.models import Product, PriceHistory, ProductApproval, PriceHistoryApproval
from django.db.models import Q
from decimal import Decimal
from dashboard.products_master.forms import ProductForm
from digital_pricelist_system.utils import get_current_user

def product_detail(request, pk):
    """商品詳細画面"""
    print(f"=== product_detail called: method={request.method}, pk={pk} ===")
    product = get_object_or_404(Product, pk=pk)
    price_histories = product.price_histories.filter(is_active=True).order_by('-effective_year_month')
    
    if request.method == 'POST':
        print("=== POST request detected, calling save_product_and_histories ===")
        # 一括保存処理
        return save_product_and_histories(request, product)
    else:
        print("=== GET request, rendering form ===")
        form = ProductForm(instance=product)
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'form': form,
        'price_histories': price_histories,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': f'{product.product_name}', 'url': None}
        ]
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
        for key, value in request.POST.items():
            if key.startswith('delete_') and value == 'true':
                print(f"Delete history: {key} = {value}")
                history_id = key.split('_')[1]
                try:
                    history = PriceHistory.objects.get(pk=history_id, product=product)
                    if hasattr(history, 'is_deletable') and history.is_deletable():
                        if hasattr(history, 'soft_delete'):
                            history.soft_delete()
                        else:
                            history.is_active = False
                            history.save()
                        print(f"Deleted history {history_id}")
                except (PriceHistory.DoesNotExist, ValueError) as e:
                    print(f"History {history_id} delete error: {e}")
        
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
        # 一括保存処理
        return save_product_and_histories(request)
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
        'is_new': True,  # 新規作成フラグ
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': '新規作成', 'url': None}
        ]
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
            
            # 日付形式をバリデーション
            try:
                if '/' not in effective_year_month:
                    return HttpResponse('適用年月はYYYY/MM形式で入力してください', status=400)
                
                year_str, month_str = effective_year_month.split('/')
                year = int(year_str)
                month = int(month_str)
                
                if year < 2000 or year > 2099:
                    return HttpResponse('年は2000～2099の範囲で入力してください', status=400)
                
                if month < 1 or month > 12:
                    return HttpResponse('月は1～12の範囲で入力してください', status=400)
                
                # 正しい形式に整形
                effective_year_month = f"{year:04d}/{month:02d}"
                
            except ValueError:
                return HttpResponse('適用年月はYYYY/MM形式で入力してください', status=400)
            
            if not wholesale_price:
                wholesale_price = '都度見積'
            
            # 年度を自動算出
            period_year = year if month >= 4 else year - 1
            
            # 重複チェック
            if PriceHistory.objects.filter(product=product, effective_year_month=effective_year_month, is_active=True).exists():
                return HttpResponse(f'{effective_year_month}の価格履歴は既に存在します', status=400)
            
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
        if pk:
            product = get_object_or_404(Product, pk=pk)
        else:
            product = None
        
        # 商品情報を取得
        if product:
            form = ProductForm(request.POST, instance=product)
        else:
            form = ProductForm(request.POST)
        
        if not form.is_valid():
            return HttpResponse('<script>alert("商品情報にエラーがあります");</script>')
        
        # 申請テーブルに商品情報をコピー
        if product:
            # 既存商品の場合
            temp_product_number = product.product_number
        else:
            # 新規商品の場合は仮番号を自動採番
            last_temp = ProductApproval.objects.filter(product_number__lt=0).order_by('product_number').first()
            temp_product_number = (last_temp.product_number - 1) if last_temp else -1
        
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
            remarks=form.cleaned_data.get('remarks')
        )
        
        # 価格履歴を申請テーブルにコピー
        if product:
            # 既存商品の場合
            for history in product.price_histories.filter(is_active=True):
                # 更新内容をチェック
                wholesale_price = request.POST.get(f'edit_wholesale_price_{history.pk}', '').strip()
                kenren_price = request.POST.get(f'edit_kenren_price_{history.pk}', '').strip()
                revision_reason = request.POST.get(f'edit_revision_reason_{history.pk}', '').strip()
                delete_flag = request.POST.get(f'delete_{history.pk}', 'false')
                
                if delete_flag == 'true':
                    continue  # 削除予定の履歴はコピーしない
                
                PriceHistoryApproval.objects.create(
                    product=approval_product,
                    period_year=history.period_year,
                    effective_year_month=history.effective_year_month,
                    gross_margin_rate=history.gross_margin_rate,
                    wholesale_price=wholesale_price if wholesale_price else history.wholesale_price,
                    kenren_price=kenren_price if kenren_price else history.kenren_price,
                    retail_price=history.retail_price,
                    revision_amount=0,
                    revision_reason=revision_reason if revision_reason else history.revision_reason
                )
        
        # 新規履歴を申請テーブルに追加
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
                    
                    # 粗利率を算定
                    try:
                        print(f"Calculating gross margin rate: product={product}, period_year={period_year}, wholesale_price={wholesale_price}")
                        gross_margin_rate = calculate_gross_margin_rate(product, period_year, wholesale_price or '都度見積')
                        print(f"Calculated gross margin rate: {gross_margin_rate}")
                    except ValueError as e:
                        print(f"Gross margin rate calculation error: {e}")
                        return HttpResponse(f'<script>alert("{str(e)}");location.reload();</script>')
                    
                    PriceHistoryApproval.objects.create(
                        product=approval_product,
                        period_year=period_year,
                        effective_year_month=effective_year_month,
                        gross_margin_rate=gross_margin_rate,
                        wholesale_price=wholesale_price or '都度見積',
                        kenren_price=kenren_price if kenren_price else None,
                        revision_amount=0,
                        revision_reason=revision_reason
                    )
        
        return HttpResponse('<script>alert("申請完了");location.reload();</script>')
        
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        return HttpResponse('<script>alert("エラー発生");</script>', status=500)

def calculate_gross_margin_rate(product, period_year, wholesale_price):
    """粗利率を算定"""
    # 都度見積等の文字列の場合はデフォルト値
    try:
        wholesale_numeric = float(wholesale_price.replace(',', ''))
    except (ValueError, AttributeError):
        # 数値でない場合（都度見積等）はデフォルト値
        return Decimal('1.0')
    
    if wholesale_numeric <= 0:
        return Decimal('1.0')  # 0以下の場合もデフォルト値
    
    # 前年度最終県連価格を取得
    prev_year = period_year - 1
    prev_kenren_price = None
    
    if product:
        prev_history = PriceHistory.objects.filter(
            product=product,
            period_year=prev_year,
            is_active=True
        ).order_by('-effective_year_month').first()
        
        if prev_history:
            prev_kenren_price = prev_history._get_numeric_kenren_price()
    
    # 前年度データがない場合、対象年度の最初の県連価格を使用
    if prev_kenren_price is None and product:
        first_history = PriceHistory.objects.filter(
            product=product,
            period_year=period_year,
            is_active=True
        ).order_by('effective_year_month').first()
        
        if first_history:
            prev_kenren_price = first_history._get_numeric_kenren_price()
    
    # 年度初め仕切価格を取得
    year_start_wholesale = None
    
    if product:
        april_history = PriceHistory.objects.filter(
            product=product,
            period_year=period_year,
            effective_year_month=f'{period_year}/04',
            is_active=True
        ).first()
        
        if april_history and april_history.wholesale_price != '都度見積':
            try:
                year_start_wholesale = float(april_history.wholesale_price.replace(',', ''))
            except (ValueError, AttributeError):
                pass
    
    # 4月データがない場合、年度内最初の仕切価格を使用
    if year_start_wholesale is None and product:
        first_history = PriceHistory.objects.filter(
            product=product,
            period_year=period_year,
            is_active=True
        ).order_by('effective_year_month').first()
        
        if first_history and first_history.wholesale_price != '都度見積':
            try:
                year_start_wholesale = float(first_history.wholesale_price.replace(',', ''))
            except (ValueError, AttributeError):
                pass
    
    # 新商品の場合、現在の仕切価格を使用
    if year_start_wholesale is None:
        year_start_wholesale = wholesale_numeric
    
    # 粗利率を算定
    if prev_kenren_price is not None and year_start_wholesale > 0:
        gross_margin_rate = prev_kenren_price / year_start_wholesale
        return Decimal(str(round(gross_margin_rate, 6)))
    
    # 算定不可の場合はエラー
    raise ValueError('粗利率を算定できません。県連価格を手動で入力してください。')

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
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '承認待ち一覧', 'url': None}
        ]
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
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '承認待ち一覧', 'url': '/products/approvals/'},
            {'title': f'{approval.product_name}', 'url': None}
        ]
    }
    return render(request, 'products_master/approval_detail.html', context)

def approve_application(request, pk):
    """申請を承認"""
    if request.method != 'POST':
        return HttpResponse('Invalid method', status=405)
    
    try:
        approval = get_object_or_404(ProductApproval, pk=pk)
        
        # 既存商品を更新または新規作成
        if approval.product_number > 0:
            # 既存商品の更新
            product = Product.objects.get(product_number=approval.product_number)
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
            product.save()
        else:
            # 新規商品の作成（正規番号を自動採番）
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
                remarks=approval.remarks
            )
        
        # 価格履歴を本テーブルにコピー
        for approval_history in approval.price_histories.filter(is_active=True):
            existing_history = PriceHistory.objects.filter(
                product=product,
                effective_year_month=approval_history.effective_year_month,
                is_active=True
            ).first()
            
            if existing_history:
                existing_history.wholesale_price = approval_history.wholesale_price
                existing_history.kenren_price = approval_history.kenren_price
                existing_history.revision_reason = approval_history.revision_reason
                existing_history.save()
            else:
                PriceHistory.objects.create(
                    product=product,
                    period_year=approval_history.period_year,
                    effective_year_month=approval_history.effective_year_month,
                    gross_margin_rate=approval_history.gross_margin_rate,
                    wholesale_price=approval_history.wholesale_price,
                    kenren_price=approval_history.kenren_price,
                    retail_price=approval_history.retail_price,
                    revision_reason=approval_history.revision_reason
                )
        
        approval.delete()
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
        approval.delete()
        return HttpResponse('<script>alert("却下完了");location.href="/products/approvals/";</script>')
    except Exception as e:
        return HttpResponse('<script>alert("エラー発生");</script>', status=500)

