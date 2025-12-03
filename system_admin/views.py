import csv
import io
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from dashboard.products_master.models import Product, PriceHistory, LivestockType, Category, Manufacturer, ProductGrossMarginRate, ProductApproval, PriceHistoryApproval
from datetime import datetime
try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

def export_csv(request):
    """DBデータをCSVエクスポート"""
    if request.method == 'POST':
        export_type = request.POST.get('export_type')
        
        if export_type == 'products':
            return export_products_csv()
        elif export_type == 'price_histories':
            return export_price_histories_csv()
        elif export_type == 'masters':
            return export_masters_csv()
    
    return render(request, 'system_admin/export.html')

def export_products_csv():
    """商品マスタをCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', '商品コード', '畜種', 'カテゴリ', 'メーカー', '商品名', '型式', '規格', '発送単位', '送料', '備考', '有効', '作成日時', '更新日時'])
    
    for product in Product.objects.all():
        writer.writerow([
            product.pk,
            product.product_code or '',
            product.livestock_type.name if product.livestock_type else '',
            product.category.name if product.category else '',
            product.manufacturer.name if product.manufacturer else '',
            product.product_name,
            product.model_number or '',
            product.specification or '',
            product.shipping_unit or '',
            product.shipping_fee or '',
            product.remarks or '',
            product.is_active,
            product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            product.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

def export_price_histories_csv():
    """価格履歴をCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="price_histories_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', '商品ID', '商品名', '年度', '適用年月', '粗利率', '仕切価格', '県連価格', '参考小売価格', '改定理由', '有効', '作成日時'])
    
    for history in PriceHistory.objects.select_related('product').all():
        writer.writerow([
            history.pk,
            history.product.pk,
            history.product.product_name,
            history.period_year,
            history.effective_year_month,
            history.gross_margin_rate,
            history.wholesale_price,
            history.kenren_price or '',
            history.retail_price or '',
            history.revision_reason or '',
            history.is_active,
            history.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

def export_masters_csv():
    """マスタデータをCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="masters_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # 畜種マスタ
    writer.writerow(['=== 畜種マスタ ==='])
    writer.writerow(['ID', '畜種名', '表示順', '有効'])
    for item in LivestockType.objects.all():
        writer.writerow([item.pk, item.name, item.sort_order, item.is_active])
    
    writer.writerow([])
    
    # カテゴリマスタ
    writer.writerow(['=== カテゴリマスタ ==='])
    writer.writerow(['ID', 'カテゴリ名', '表示順', '有効'])
    for item in Category.objects.all():
        writer.writerow([item.pk, item.name, item.sort_order, item.is_active])
    
    writer.writerow([])
    
    # メーカーマスタ
    writer.writerow(['=== メーカーマスタ ==='])
    writer.writerow(['ID', 'メーカー名', '有効'])
    for item in Manufacturer.objects.all():
        writer.writerow([item.pk, item.name, item.is_active])
    
    return response

def import_csv(request):
    """CSVインポート機能"""
    if request.method == 'POST':
        if 'preview' in request.POST:
            return handle_csv_preview(request)
        elif 'execute' in request.POST:
            return handle_csv_import(request)
    
    return render(request, 'system_admin/import.html')

def handle_csv_preview(request):
    """CSV/Excelプレビュー処理"""
    try:
        uploaded_file = request.FILES.get('csv_file')
        if not uploaded_file:
            messages.error(request, 'ファイルを選択してください')
            return render(request, 'system_admin/import.html')
        
        # ファイル形式を判定
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            if not EXCEL_SUPPORT:
                messages.error(request, 'Excelファイルの処理にはopenpyxlライブラリが必要です。pip install openpyxl でインストールしてください。')
                return render(request, 'system_admin/import.html')
            rows = read_excel_file(uploaded_file)
        else:
            # CSVを読み込み
            csv_data = uploaded_file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(csv_data))
            rows = list(reader)
        
        if len(rows) < 2:
            messages.error(request, 'CSVファイルにデータがありません')
            return render(request, 'system_admin/import.html')
        
        # ヘッダー行をスキップ
        data_rows = rows[1:]
        
        # データを解析
        preview_data = []
        errors = []
        
        for row_num, row in enumerate(data_rows, start=2):
            try:
                product_data, price_histories = parse_csv_row(row, row_num)
                if product_data is not None and price_histories is not None:  # 空行でない場合のみ追加
                    preview_data.append({
                        'row_num': row_num,
                        'product': product_data,
                        'histories': price_histories
                    })
            except ValueError as e:
                errors.append(f'行{row_num}: {str(e)}')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'system_admin/import.html')
        
        # セッションにデータを保存
        request.session['import_data'] = {
            'file_type': 'excel' if file_name.endswith(('.xlsx', '.xls')) else 'csv',
            'preview_data': preview_data
        }
        
        return render(request, 'system_admin/import_preview.html', {
            'preview_data': preview_data
        })
        
    except Exception as e:
        messages.error(request, f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
        return render(request, 'system_admin/import.html')

def handle_csv_import(request):
    """CSV実行処理"""
    try:
        import_data = request.session.get('import_data')
        if not import_data:
            messages.error(request, 'インポートデータが見つかりません。最初からやり直してください。')
            return redirect('system_admin:import_csv')
        
        preview_data = import_data['preview_data']
        
        with transaction.atomic():
            created_products = 0
            created_histories = 0
            
            for item in preview_data:
                product_data = item['product']
                price_histories = item['histories']
                
                # マスタデータの取得または作成
                livestock_type, _ = LivestockType.objects.get_or_create(
                    name=product_data['livestock_type'],
                    defaults={'sort_order': 999, 'is_active': True}
                )
                
                category, _ = Category.objects.get_or_create(
                    name=product_data['category'],
                    defaults={'sort_order': 999, 'is_active': True}
                )
                
                manufacturer, _ = Manufacturer.objects.get_or_create(
                    name=product_data['manufacturer'],
                    defaults={'is_active': True}
                )
                
                # 商品作成
                product = Product.objects.create(
                    product_code=product_data['product_code'] or None,
                    livestock_type=livestock_type,
                    category=category,
                    manufacturer=manufacturer,
                    product_name=product_data['product_name'],
                    model_number=product_data['model_number'] or None,
                    specification=product_data['specification'] or None,
                    shipping_unit=product_data['shipping_unit'] or None,
                    shipping_fee=product_data['shipping_fee'] or None,
                    remarks=product_data['remarks'] or None
                )
                created_products += 1
                
                # 価格履歴作成と粗利率テーブル更新
                year_margins = {}  # 年度別の最新粗利率を記録
                
                for history_data in price_histories:
                    # 粗利率計算（数値の場合のみ）
                    gross_margin_rate = Decimal(str(history_data['kenren_num'])) / Decimal(str(history_data['wholesale_num']))
                    
                    # 価格履歴作成
                    PriceHistory.objects.create(
                        product=product,
                        period_year=history_data['period_year'],
                        effective_year_month=history_data['effective_year_month'],
                        gross_margin_rate=gross_margin_rate,
                        wholesale_price=history_data['wholesale_price'],  # 文字列
                        kenren_price=history_data['kenren_price'],  # 文字列
                        retail_price=history_data['retail_price'],  # 文字列
                        revision_reason=history_data['revision_reason'] or None
                    )
                    created_histories += 1
                    
                    # 年度別最新粗利率を記録
                    period_year = history_data['period_year']
                    effective_date = history_data['effective_year_month']
                    
                    if period_year not in year_margins or effective_date > year_margins[period_year]['date']:
                        year_margins[period_year] = {
                            'rate': gross_margin_rate,
                            'date': effective_date
                        }
                
                # 粗利率テーブル更新
                for period_year, margin_info in year_margins.items():
                    ProductGrossMarginRate.objects.update_or_create(
                        product=product,
                        period_year=period_year,
                        defaults={
                            'gross_margin_rate': margin_info['rate'],
                            'calculation_note': 'CSVインポート時自動計算'
                        }
                    )
        
        # セッションデータをクリア
        if 'import_data' in request.session:
            del request.session['import_data']
        
        messages.success(request, f'インポートが完了しました。商品: {created_products}件, 価格履歴: {created_histories}件')
        return redirect('system_admin:import_csv')
        
    except Exception as e:
        messages.error(request, f'インポート中にエラーが発生しました: {str(e)}')
        return redirect('system_admin:import_csv')

def parse_csv_row(row, row_num):
    """CSV行を解析"""
    if len(row) < 15:  # 最低限の列数チェック
        raise ValueError('列数が不足しています')
    
    # 空行チェック（主要項目がすべて空の場合はスキップ）
    main_fields = [str(row[i]).strip() for i in range(1, 5)]  # 畜種、分類、メーカー、商品名
    if not any(main_fields):
        return None, None  # 空行として扱う
    
    # 商品マスタ部（0-9列目）
    product_data = {
        'product_code': str(row[0]).strip() if str(row[0]).strip() else None,
        'livestock_type': str(row[1]).strip(),
        'category': str(row[2]).strip(),
        'manufacturer': str(row[3]).strip(),
        'product_name': str(row[4]).strip(),
        'model_number': str(row[5]).strip() if str(row[5]).strip() else None,
        'specification': str(row[6]).strip() if str(row[6]).strip() else None,
        'shipping_unit': str(row[7]).strip() if str(row[7]).strip() else None,
        'shipping_fee': str(row[8]).strip() if str(row[8]).strip() else None,
        'remarks': str(row[9]).strip() if str(row[9]).strip() else None,
    }
    
    # 必須項目チェック
    if not product_data['livestock_type']:
        raise ValueError('畜種は必須です')
    if not product_data['category']:
        raise ValueError('カテゴリは必須です')
    if not product_data['manufacturer']:
        raise ValueError('メーカーは必須です')
    if not product_data['product_name']:
        raise ValueError('商品名は必須です')
    
    # 価格履歴部（10列目以降、5列セット）
    price_histories = []
    history_start = 10
    
    while history_start + 4 < len(row):
        effective_year_month = str(row[history_start]).strip()
        if not effective_year_month:  # 適用年月が空なら終了
            break
        
        wholesale_price = str(row[history_start + 1]).strip()
        kenren_price = str(row[history_start + 2]).strip()
        retail_price = str(row[history_start + 3]).strip()
        revision_reason = str(row[history_start + 4]).strip()
        
        # バリデーション
        if not wholesale_price or not kenren_price:
            raise ValueError(f'適用年月{effective_year_month}: 仕切価格と県連価格は必須です')
        
        # 日付形式チェック
        if not effective_year_month.count('/') == 1:
            raise ValueError(f'適用年月の形式が正しくありません: {effective_year_month}')
        
        try:
            year_str, month_str = effective_year_month.split('/')
            year = int(year_str)
            month = int(month_str)
            if not (2000 <= year <= 2099 and 1 <= month <= 12):
                raise ValueError()
            period_year = year if month >= 4 else year - 1
            # 月を2桁にフォーマット
            effective_year_month = f'{year:04d}/{month:02d}'
        except ValueError:
            raise ValueError(f'適用年月の形式が正しくありません: {effective_year_month}')
        
        # 価格は文字列として保存（数値・文字列両方対応）
        wholesale_value = wholesale_price.strip()
        kenren_value = kenren_price.strip()
        retail_value = retail_price.strip() if retail_price.strip() else None
        
        # 粗利率計算用に数値変換を試行（数値の場合のみ）
        try:
            wholesale_num = float(wholesale_value.replace(',', ''))
            kenren_num = float(kenren_value.replace(',', ''))
        except ValueError:
            # 文字列の場合は粗利率を0.0に設定（画面と同じ）
            wholesale_num = 1.0
            kenren_num = 0.0
        
        price_histories.append({
            'effective_year_month': effective_year_month,  # 既にフォーマット済み
            'period_year': period_year,
            'wholesale_price': wholesale_value,  # 文字列として保存
            'kenren_price': kenren_value,  # 文字列として保存
            'retail_price': retail_value,  # 文字列として保存
            'revision_reason': revision_reason if revision_reason else None,
            'wholesale_num': wholesale_num,  # 粗利率計算用
            'kenren_num': kenren_num  # 粗利率計算用
        })
        
        history_start += 5
    
    if not price_histories:
        raise ValueError('価格履歴が1件もありません')
    
    return product_data, price_histories

def read_excel_file(uploaded_file):
    """エクセルファイルを読み込んでCSV形式のリストに変換"""
    workbook = openpyxl.load_workbook(uploaded_file, data_only=True)
    worksheet = workbook.active
    
    rows = []
    for row in worksheet.iter_rows(values_only=True):
        # Noneを空文字列に変換
        converted_row = [str(cell) if cell is not None else '' for cell in row]
        rows.append(converted_row)
    
    return rows

def clear_data(request):
    """データクリア機能"""
    if request.method == 'POST':
        confirmation_text = request.POST.get('confirmation_text', '').strip()
        
        if confirmation_text == 'ZLC_Digital_ValueList':
            try:
                with transaction.atomic():
                    # 関連データを順番に削除
                    deleted_counts = {
                        'price_histories': PriceHistory.objects.all().count(),
                        'price_history_approvals': 0,
                        'product_approvals': 0,
                        'gross_margin_rates': 0,
                        'products': Product.objects.all().count(),
                        'livestock_types': LivestockType.objects.all().count(),
                        'categories': Category.objects.all().count(),
                        'manufacturers': Manufacturer.objects.all().count()
                    }
                    
                    # 価格履歴承認テーブル
                    try:
                        from dashboard.products_master.models import PriceHistoryApproval
                        deleted_counts['price_history_approvals'] = PriceHistoryApproval.objects.all().count()
                        PriceHistoryApproval.objects.all().delete()
                    except:
                        pass
                    
                    # 商品承認テーブル
                    try:
                        from dashboard.products_master.models import ProductApproval
                        deleted_counts['product_approvals'] = ProductApproval.objects.all().count()
                        ProductApproval.objects.all().delete()
                    except:
                        pass
                    
                    # 粗利率テーブル
                    deleted_counts['gross_margin_rates'] = ProductGrossMarginRate.objects.all().count()
                    ProductGrossMarginRate.objects.all().delete()
                    
                    # 価格履歴
                    PriceHistory.objects.all().delete()
                    
                    # 商品マスタ
                    Product.objects.all().delete()
                    
                    # マスタデータ
                    LivestockType.objects.all().delete()
                    Category.objects.all().delete()
                    Manufacturer.objects.all().delete()
                
                messages.success(request, f'データクリアが完了しました。削除件数: 商品{deleted_counts["products"]}件, 価格履歴{deleted_counts["price_histories"]}件, 畜種{deleted_counts["livestock_types"]}件, カテゴリ{deleted_counts["categories"]}件, メーカー{deleted_counts["manufacturers"]}件')
                return redirect('system_admin:clear_data')
                
            except Exception as e:
                messages.error(request, f'データクリア中にエラーが発生しました: {str(e)}')
                return render(request, 'system_admin/clear_data.html')
        else:
            messages.error(request, '確認テキストが正しくありません。正確に「ZLC_Digital_ValueList」と入力してください。')
            return render(request, 'system_admin/clear_data.html')
    
    return render(request, 'system_admin/clear_data.html')

def status_reset(request):
    """ステータス強制リセット機能（全ての申請中商品を強制リセット）"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ステータスが設定されている全ての商品をリセット
                reset_count = Product.objects.exclude(status='').exclude(status__isnull=True).update(status='')
                
                if reset_count > 0:
                    messages.success(request, f'{reset_count}件の商品のステータスをリセットしました。')
                else:
                    messages.info(request, 'リセット対象の商品はありませんでした。')
                
                return redirect('system_admin:status_reset')
                
        except Exception as e:
            messages.error(request, f'ステータスリセット中にエラーが発生しました: {str(e)}')
    
    # リセット対象の商品を表示
    status_products = Product.objects.exclude(status='').exclude(status__isnull=True)
    
    return render(request, 'system_admin/status_reset.html', {
        'status_products': status_products
    })