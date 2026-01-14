from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q, OuterRef, Subquery
from django.db import transaction
from django.conf import settings
from dashboard.products_master.models import Product, PriceHistory, ApprovalPdf
from dashboard.products_master.ai_services import normalize_text
import unicodedata
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs
from digital_pricelist_system.config_paths import CONFIG_PATH
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import io
import os
import sys
import json
import configparser
import urllib.parse

def _check_approval_pdf(year_month):
    """承認PDFの存在をチェック
    
    Args:
        year_month (str): YYYY/MM形式の年月
    
    Returns:
        bool: 承認PDFが存在するかどうか
    """
    if not year_month:
        return False
    
    return ApprovalPdf.objects.filter(year_month=year_month).exists()

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
    
    # フィルターパラメータを取得
    selected_month = request.GET.get('month', default_month)
    manufacturer_filter = request.GET.get('manufacturer', '').strip()
    product_name_filter = request.GET.get('product_name', '').strip()
    
    # HTML5 month入力からYYYY/MM形式に変換
    if selected_month and '-' in selected_month:
        selected_month = selected_month.replace('-', '/')
    
    # 適用年月一覧を取得（有効な商品のみ）
    available_months = PriceHistory.objects.filter(
        product__is_active=True, 
        is_active=True
    ).values_list('effective_year_month', flat=True).distinct().order_by('-effective_year_month')
    
    # sort_numが未設定の商品に初期値を設定（条件付き）
    from django.db.models import Q
    if Product.objects.filter(Q(sort_num=0) | Q(sort_num__isnull=True), is_active=True).exists():
        _initialize_sort_numbers()
    
    # 商品フィルターを適用（ノーマライズ検索）
    products_query = Product.objects.filter(is_active=True)
    
    if manufacturer_filter:
        # 全角・半角英数字のみ正規化して部分一致検索
        def normalize_simple(text):
            if not text:
                return ""
            text = unicodedata.normalize('NFKC', text)
            return text.upper()
        
        normalized_manufacturer = normalize_simple(manufacturer_filter)
        products_query = products_query.filter(manufacturer__name__icontains=normalized_manufacturer)
    
    if product_name_filter:
        # 全角・半角英数字のみ正規化して部分一致検索
        def normalize_simple(text):
            if not text:
                return ""
            text = unicodedata.normalize('NFKC', text)
            return text.upper()
        
        normalized_filter = normalize_simple(product_name_filter)
        products_query = products_query.filter(product_name__icontains=normalized_filter)
    
    # 全ての有効な商品を取得（関連データも一括取得）
    all_products = products_query.select_related(
        'livestock_type', 'category', 'manufacturer'
    ).order_by('livestock_type', 'category', 'manufacturer', 'sort_num', 'product_name')
    
    # 商品IDリストを取得
    product_ids = list(all_products.values_list('id', flat=True))
    
    # 価格履歴を一括取得してマッピング
    price_histories = {}
    if selected_month:
        # サブクエリで各商品の最新価格履歴IDを取得
        from django.db.models import OuterRef, Subquery
        latest_histories = PriceHistory.objects.filter(
            product=OuterRef('product'),
            is_active=True,
            effective_year_month__lte=selected_month
        ).order_by('-effective_year_month').values('id')[:1]
        
        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories),
            product_id__in=product_ids
        ).select_related('product')
    else:
        # 最新の価格履歴を取得
        from django.db.models import OuterRef, Subquery
        latest_histories = PriceHistory.objects.filter(
            product=OuterRef('product'),
            is_active=True
        ).order_by('-effective_year_month').values('id')[:1]
        
        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories),
            product_id__in=product_ids
        ).select_related('product')
    
    # 商品IDをキーとした価格履歴マップを作成
    for history in histories:
        price_histories[history.product_id] = history
    
    # 商品データを構築
    product_data = []
    previous_group = None
    
    for product in all_products:
        price_history = price_histories.get(product.id)
        
        # グループの境界を判定
        current_group = (product.livestock_type, product.category, product.manufacturer)
        is_group_start = previous_group != current_group
        previous_group = current_group
        
        # 仕切価格0円の場合は価格なし扱い
        has_valid_price = price_history is not None and price_history.wholesale_price != 0
        
        # 商品と価格履歴のペアを作成
        product_data.append({
            'product': product,
            'price_history': price_history,
            'has_price': has_valid_price,
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
    
    # データ取得を最適化（必要な列のみ取得）
    all_products = Product.objects.filter(is_active=True).select_related(
        'livestock_type', 'category', 'manufacturer'
    ).only(
        'id', 'product_name', 'model_number', 'specification', 'shipping_unit', 
        'shipping_fee', 'remarks', 'sort_num',
        'livestock_type__name', 'category__name', 'manufacturer__name'
    ).order_by('livestock_type', 'category', 'manufacturer', 'sort_num', 'product_name')
    
    # 商品データを即座にリスト化してDBコネクションを解放
    product_list = list(all_products)
    product_ids = [p.id for p in product_list]
    
    # 価格履歴を一括取得
    if selected_month:
        from django.db.models import OuterRef, Subquery
        latest_histories = PriceHistory.objects.filter(
            product=OuterRef('product'),
            is_active=True,
            effective_year_month__lte=selected_month
        ).order_by('-effective_year_month').values('id')[:1]
        
        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories),
            product_id__in=product_ids
        )
    else:
        from django.db.models import OuterRef, Subquery
        latest_histories = PriceHistory.objects.filter(
            product=OuterRef('product'),
            is_active=True
        ).order_by('-effective_year_month').values('id')[:1]
        
        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories),
            product_id__in=product_ids
        )
    
    # 価格履歴も即座にリスト化してDBコネクションを解放
    price_histories = {h.product_id: h for h in list(histories)}
    
    # 価格ありかつ仕切価格0円以外の商品のみフィルタ
    product_data = []
    for product in product_list:
        price_history = price_histories.get(product.id)
        if price_history and price_history.wholesale_price != 0:
            product_data.append({
                'product': product,
                'price_history': price_history,
                'has_price': True
            })
    
    # テンプレートファイルを読み込み
    # config.iniからテンプレートパスを取得
    config = configparser.ConfigParser()
    template_path = None
    
    if CONFIG_PATH.exists():
        try:
            config.read(CONFIG_PATH, encoding='utf-8')
            template_path = config.get('FILES', 'excel_template', fallback=None)
        except Exception:
            pass
    
    # テンプレートパスが設定されていない場合のフォールバック
    if not template_path:
        # PyInstaller環境でのテンプレートパス取得
        if getattr(sys, 'frozen', False):
            # PyInstaller環境では一時フォルダから取得
            template_path = os.path.join(sys._MEIPASS, 'degital_value_list.xlsx')
        else:
            # 開発環境では従来通り
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
        # 既に価格ありの商品のみフィルタ済み
        
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
            excel_row_num - 1, str(product.livestock_type or ''), str(product.category or ''), str(product.manufacturer or ''),
            product.product_name or '', product.model_number or '', product.specification or '',
            product.shipping_unit or '', kenren_price, revision_amount, retail_price,
            product.shipping_fee or '', product.remarks or '',
            price_history.revision_reason if price_history.revision_reason else ''
        ]
        
        # データを書き込み（スタイルは最後に一括設定）
        for col, value in enumerate(data, 1):
            ws.cell(row=row_num, column=col, value=value)
        
        row_num += 1
    
    # テンプレート行（4行目）の書式をコピー
    if row_num > 4:
        template_styles = []
        for col in range(1, 15):
            template_cell = ws.cell(row=4, column=col)
            template_styles.append({
                'font': template_cell.font.copy() if template_cell.font else None,
                'border': template_cell.border.copy() if template_cell.border else None,
                'fill': template_cell.fill.copy() if template_cell.fill else None,
                'alignment': template_cell.alignment.copy() if template_cell.alignment else None,
                'number_format': template_cell.number_format
            })
        
        # データ行にスタイルを適用
        gray_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
        
        for row in range(5, row_num):
            is_gray_row = (row - 4) % 2 == 1  # 奇数行をグレーに
            
            for col in range(1, 15):
                cell = ws.cell(row=row, column=col)
                style = template_styles[col-1]
                if style['font']:
                    cell.font = style['font']
                if style['border']:
                    cell.border = style['border']
                if is_gray_row:
                    cell.fill = gray_fill
                elif style['fill']:
                    cell.fill = style['fill']
                if style['alignment']:
                    cell.alignment = style['alignment']
                if style['number_format']:
                    cell.number_format = style['number_format']
    
    # 承認状態をチェック
    is_approved = _check_approval_pdf(selected_month)
    approval_status = '確定版' if is_approved else '未承認版'
    
    # 未承認版の表示（セル結合で目立たせる）
    if not is_approved:
        # A1:D2を結合して大きな警告を表示
        ws.merge_cells('A1:D2')
        warning_cell = ws['A1']
        warning_cell.value = '【未承認版】'
        warning_cell.font = Font(bold=True, color='FFFFFF', size=30)  # 白文字、30ポイント
        warning_cell.fill = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')  # 赤背景
        warning_cell.alignment = Alignment(horizontal='center', vertical='center')  # 中央揃え
    
    if selected_month:
        filename = f'{selected_month.replace("/", "")}デジタル価格表_{approval_status}.xlsx'
    else:
        filename = f'{datetime.now().strftime("%Y%m")}デジタル価格表_{approval_status}.xlsx'
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    # UTF-8エンコードでファイル名を設定
    encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
    response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'
    
    return response

def reset_sort_order(request):
    """ソート順序リセットAPI"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドが必要です'})
    
    try:
        # 全商品のsort_numを0にリセット
        with transaction.atomic():
            Product.objects.filter(is_active=True).update(sort_num=0)
        
        return JsonResponse({'success': True, 'message': 'ソート順序をリセットしました'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'})

def cross_page_move(request):
    """ページ境界移動API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドが必要です'})
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        direction = data.get('direction')  # 'prev' or 'next'
        current_page = data.get('current_page', 1)
        
        if not product_id or direction not in ['prev', 'next']:
            return JsonResponse({'success': False, 'message': 'パラメータが不正です'})
        
        # 対象商品を取得
        target_product = Product.objects.get(pk=product_id, is_active=True)
        
        # 同じグループの商品を取得
        group_products = Product.objects.filter(
            livestock_type=target_product.livestock_type,
            category=target_product.category,
            manufacturer=target_product.manufacturer,
            is_active=True
        ).order_by('sort_num', 'product_name')
        
        products_list = list(group_products)
        target_index = next((i for i, p in enumerate(products_list) if p.id == product_id), None)
        
        if target_index is None:
            return JsonResponse({'success': False, 'message': '商品が見つかりません'})
        
        # 移動先を決定
        if direction == 'prev':
            # 前ページの末尾へ（一つ前の商品と入れ替え）
            if target_index == 0:
                return JsonResponse({'success': False, 'message': 'これ以上上に移動できません'})
            swap_index = target_index - 1
        else:  # next
            # 次ページの先頭へ（一つ後の商品と入れ替え）
            if target_index >= len(products_list) - 1:
                return JsonResponse({'success': False, 'message': 'これ以上下に移動できません'})
            swap_index = target_index + 1
        
        # 商品を入れ替え
        with transaction.atomic():
            products_list[target_index], products_list[swap_index] = products_list[swap_index], products_list[target_index]
            
            # sort_numを更新
            for i, product in enumerate(products_list, 1):
                product.sort_num = i
                product.save(update_fields=['sort_num'])
        
        # リダイレクトURLを構築
        from django.urls import reverse
        redirect_page = current_page
        if direction == 'prev' and current_page > 1:
            redirect_page = current_page - 1
        elif direction == 'next':
            redirect_page = current_page + 1
        
        redirect_url = reverse('products_master:integrated_pricelist') + f'?page={redirect_page}'
        
        return JsonResponse({
            'success': True, 
            'message': '商品を移動しました',
            'redirect_url': redirect_url
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': '商品が見つかりません'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'})
def upload_approval_pdf(request):
    """承認PDFアップロード機能"""
    if request.method == 'POST':
        try:
            year_month = request.POST.get('year_month')
            pdf_file = request.FILES.get('pdf_file')
            
            if not year_month or not pdf_file:
                messages.error(request, '年月とPDFファイルを選択してください')
                return redirect('products_master:upload_approval_pdf')
            
            # ファイル拡張子チェック
            if not pdf_file.name.lower().endswith('.pdf'):
                messages.error(request, 'PDFファイルを選択してください')
                return redirect('products_master:upload_approval_pdf')
            
            # YYYY-MMをYYYY/MMに変換
            if '-' in year_month:
                year_month = year_month.replace('-', '/')
            
            # ファイル名を生成
            approval_month = year_month.replace('/', '')
            
            # 保存ディレクトリを作成
            approval_dir = os.path.join(settings.MEDIA_ROOT, 'approval')
            os.makedirs(approval_dir, exist_ok=True)
            
            # ファイルを保存
            file_path = os.path.join(approval_dir, f'{approval_month}_approval.pdf')
            with open(file_path, 'wb') as f:
                for chunk in pdf_file.chunks():
                    f.write(chunk)
            
            # テーブルに記録（既存の場合は更新）
            ApprovalPdf.objects.update_or_create(
                year_month=year_month,
                defaults={
                    'pdf_file_path': file_path,
                    'uploaded_by': get_current_user()
                }
            )
            
            messages.success(request, f'{year_month}の承認PDFをアップロードしました')
            return redirect('products_master:upload_approval_pdf')
            
        except Exception as e:
            messages.error(request, f'アップロード中にエラーが発生しました: {str(e)}')
            return redirect('products_master:upload_approval_pdf')
    
    # 既存の承認PDF一覧を取得
    approved_pdfs = ApprovalPdf.objects.all().order_by('-year_month')
    
    context = {
        'current_user': get_current_user(),
        'approved_pdfs': approved_pdfs,
        'breadcrumbs': get_breadcrumbs('upload_approval_pdf')
    }
    return render(request, 'products_master/upload_approval_pdf.html', context)
def download_approval_pdf(request, pk):
    """承認PDFダウンロード"""
    try:
        approval_pdf = ApprovalPdf.objects.get(pk=pk)
        
        if not os.path.exists(approval_pdf.pdf_file_path):
            messages.error(request, 'ファイルが見つかりません')
            return redirect('products_master:upload_approval_pdf')
        
        with open(approval_pdf.pdf_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            filename = f'{approval_pdf.year_month.replace("/", "")}_approval.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except ApprovalPdf.DoesNotExist:
        messages.error(request, '承認PDFが見つかりません')
        return redirect('products_master:upload_approval_pdf')
    except Exception as e:
        messages.error(request, f'ダウンロード中にエラーが発生しました: {str(e)}')
        return redirect('products_master:upload_approval_pdf')