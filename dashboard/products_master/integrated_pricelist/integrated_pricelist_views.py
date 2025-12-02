from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from dashboard.products_master.models import Product, PriceHistory
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import io

def _initialize_sort_numbers(force_reset=False):
    """畜種・分類・メーカーごとにsort_numを初期化"""
    from django.db.models import Q
    
    if force_reset:
        # 強制リセット時は全商品を対象
        products_to_update = Product.objects.filter(
            is_active=True
        ).order_by('livestock_type', 'category', 'manufacturer', 'product_name')
    else:
        # 通常時はsort_numが0の商品のみ
        products_to_update = Product.objects.filter(
            Q(sort_num=0) | Q(sort_num__isnull=True),
            is_active=True
        ).order_by('livestock_type', 'category', 'manufacturer', 'product_name')
    
    if not products_to_update.exists():
        return
    
    # グループ別に連番を振る
    current_group = None
    sort_counter = 1
    
    for product in products_to_update:
        group_key = (product.livestock_type, product.category, product.manufacturer)
        
        if current_group != group_key:
            current_group = group_key
            sort_counter = 1
        
        product.sort_num = sort_counter
        product.save(update_fields=['sort_num'])
        sort_counter += 1

def integrated_pricelist(request):
    """統合価格表画面（全商品表示、価格なしはグレー）"""
    # デフォルトはシステム稼働日の翌月
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    default_month = next_month.strftime('%Y/%m')
    
    # 適用年月フィルター
    selected_month = request.GET.get('month', default_month)
    
    # HTML5 month入力からYYYY/MM形式に変換
    if selected_month and '-' in selected_month:
        selected_month = selected_month.replace('-', '/')
    
    # 適用年月一覧を取得（有効な商品のみ）
    available_months = PriceHistory.objects.filter(
        product__is_active=True, 
        is_active=True
    ).values_list('effective_year_month', flat=True).distinct().order_by('-effective_year_month')
    
    # sort_numが未設定の商品に初期値を設定
    _initialize_sort_numbers()
    
    # 全ての有効な商品を取得
    all_products = Product.objects.filter(is_active=True).order_by(
        'livestock_type', 'category', 'manufacturer', 'sort_num', 'product_name'
    )
    
    # 各商品に対して価格履歴を取得またはNoneを設定
    product_data = []
    previous_group = None
    
    for product in all_products:
        price_history = None
        
        if selected_month:
            # 指定年月以下で最新の価格履歴を取得
            price_history = PriceHistory.objects.filter(
                product=product,
                is_active=True,
                effective_year_month__lte=selected_month
            ).order_by('-effective_year_month').first()
        else:
            # 最新の価格履歴を取得
            price_history = PriceHistory.objects.filter(
                product=product,
                is_active=True
            ).order_by('-effective_year_month').first()
        
        # グループの境界を判定
        current_group = (product.livestock_type, product.category, product.manufacturer)
        is_group_start = previous_group != current_group
        previous_group = current_group
        
        # 商品と価格履歴のペアを作成
        product_data.append({
            'product': product,
            'price_history': price_history,
            'has_price': price_history is not None,
            'is_group_start': is_group_start
        })
    
    # ページネーション
    paginator = Paginator(product_data, 200)  # 200件ずつ表示
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'current_user': get_current_user(),
        'page_obj': page_obj,
        'available_months': available_months,
        'selected_month': selected_month,
        'breadcrumbs': get_breadcrumbs('integrated_pricelist')
    }
    return render(request, 'products_master/integrated_pricelist.html', context)

def update_sort_order(request):
    """ソート順序更新API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドが必要です'})
    
    try:
        import json
        from django.http import JsonResponse
        from django.db import transaction
        
        data = json.loads(request.body)
        updates = data.get('updates', [])
        
        if not updates:
            return JsonResponse({'success': False, 'message': '更新データがありません'})
        
        # 一括更新
        with transaction.atomic():
            for update in updates:
                product_id = update.get('product_id')
                sort_num = update.get('sort_num')
                
                if product_id and sort_num is not None:
                    Product.objects.filter(pk=product_id).update(sort_num=sort_num)
        
        return JsonResponse({'success': True, 'message': 'ソート順序を更新しました'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'})

def export_excel(request):
    """デジタル価格表のExcel出力"""
    selected_month = request.GET.get('month', '')
    if selected_month and '-' in selected_month:
        selected_month = selected_month.replace('-', '/')
    
    _initialize_sort_numbers()
    
    all_products = Product.objects.filter(is_active=True).order_by(
        'livestock_type', 'category', 'manufacturer', 'sort_num', 'product_name'
    )
    
    product_data = []
    for product in all_products:
        price_history = None
        
        if selected_month:
            price_history = PriceHistory.objects.filter(
                product=product,
                is_active=True,
                effective_year_month__lte=selected_month
            ).order_by('-effective_year_month').first()
        else:
            price_history = PriceHistory.objects.filter(
                product=product,
                is_active=True
            ).order_by('-effective_year_month').first()
        
        product_data.append({
            'product': product,
            'price_history': price_history,
            'has_price': price_history is not None
        })
    
    # テンプレートファイルを読み込み
    import os
    from django.conf import settings
    
    template_path = os.path.join(settings.BASE_DIR, 'degital_value_list.xlsx')
    
    try:
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active
    except FileNotFoundError:
        # テンプレートがない場合は新規作成
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'デジタル価格表'
        
        headers = [
            '№', '畜種', '分類', 'メーカー', '商品名', '型式', '規格', '発送単位',
            '県連価格', '改定額', '参考小売価格', '送料', '備考', '改定理由'
        ]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # 既存データをクリア（5行目以降のデータ行）
    for row in range(5, ws.max_row + 1):
        for col in range(1, 15):
            ws.cell(row=row, column=col).value = None
    
    # ヘッダーの年月を更新
    if selected_month:
        # yyyy/mm形式をyyyy.mm形式に変換
        display_month = selected_month.replace('/', '.')
        
        # I3セル（県連価格）の年月を更新
        kenren_header = ws.cell(row=3, column=9)
        if kenren_header.value:
            kenren_header.value = str(kenren_header.value).replace('{yyyy.mm}', display_month)
        
        # K3セル（参考小売価格）の年月を更新
        retail_header = ws.cell(row=3, column=11)
        if retail_header.value:
            retail_header.value = str(retail_header.value).replace('{yyyy.mm}', display_month)
    
    # テンプレート行（4行目）の書式を取得
    template_row = 4
    
    row_num = 4
    excel_row_num = 1
    for item in product_data:
        product = item['product']
        price_history = item['price_history']
        has_price = item['has_price']
        
        # 価格なしの商品はExcelに出���しない
        if not has_price:
            continue
        
        excel_row_num += 1
        
        kenren_price = ''
        if price_history.kenren_price:
            try:
                kenren_price = int(float(str(price_history.kenren_price).replace(',', '')))
            except:
                kenren_price = price_history.kenren_price
        else:
            try:
                if price_history.wholesale_price and price_history.wholesale_price != '都度見積':
                    wholesale = float(str(price_history.wholesale_price).replace(',', ''))
                    margin = float(price_history.gross_margin_rate)
                    kenren_price = int(wholesale * margin)
                else:
                    kenren_price = '都度見積'
            except:
                kenren_price = '都度見積'
        
        retail_price = ''
        if price_history.retail_price:
            try:
                retail_price = int(float(str(price_history.retail_price).replace(',', '')))
            except:
                retail_price = price_history.retail_price
        else:
            retail_price = '-'
        
        revision_amount = ''
        try:
            revision_amount = price_history.get_revision_amount()
        except:
            revision_amount = 0
        
        data = [
            excel_row_num - 1, product.livestock_type or '', product.category or '', product.manufacturer or '',
            product.product_name or '', product.model_number or '', product.specification or '',
            product.shipping_unit or '', kenren_price, revision_amount, retail_price,
            product.shipping_fee or '', product.remarks or '',
            price_history.revision_reason if price_history.revision_reason else ''
        ]
        
        # テンプレート行を複製して書式を保持
        if row_num > template_row:
            ws.insert_rows(row_num)
            # 行の高さをコピー
            ws.row_dimensions[row_num].height = ws.row_dimensions[template_row].height
            for col in range(1, 15):
                template_cell = ws.cell(row=template_row, column=col)
                new_cell = ws.cell(row=row_num, column=col)
                if template_cell.has_style:
                    new_cell.font = template_cell.font.copy()
                    new_cell.border = template_cell.border.copy()
                    new_cell.fill = template_cell.fill.copy()
                    new_cell.number_format = template_cell.number_format
                    new_cell.protection = template_cell.protection.copy()
                    new_cell.alignment = template_cell.alignment.copy()
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            # 奇数行をグレーに設定
            if excel_row_num % 2 == 1:
                cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
        
        row_num += 1
    
    if selected_month:
        filename = f'デジタル価格表_{selected_month.replace("/", "")}.xlsx'
    else:
        filename = f'デジタル価格表_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

def reset_sort_order(request):
    """ソート順序リセットAPI"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドが必要です'})
    
    try:
        from django.db import transaction
        
        # 全商品のsort_numを0にリセット
        with transaction.atomic():
            Product.objects.filter(is_active=True).update(sort_num=0)
        
        return JsonResponse({'success': True, 'message': 'ソート順序をリセットしました'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'})