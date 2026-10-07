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
import tempfile


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
        products_to_update = Product.objects.filter(is_active=True).order_by(
            "livestock_type", "category", "manufacturer", "product_name"
        )
    else:
        # 通常時はsort_numが0の商品のみ
        products_to_update = Product.objects.filter(
            Q(sort_num=0) | Q(sort_num__isnull=True), is_active=True
        ).order_by("livestock_type", "category", "manufacturer", "product_name")

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
        product.save(update_fields=["sort_num"])
        sort_counter += 1


def integrated_pricelist(request):
    """統合価格表画面（全商品表示、価格なしはグレー）"""
    # デフォルトはシステム稼働日の翌月
    today = datetime.now()
    next_month = today.replace(day=1) + timedelta(days=32)
    default_month = next_month.strftime("%Y/%m")

    # フィルターパラメータを取得
    selected_month = request.GET.get("month", default_month)
    manufacturer_filter = request.GET.get("manufacturer", "").strip()
    product_name_filter = request.GET.get("product_name", "").strip()

    # HTML5 month入力からYYYY/MM形式に変換
    if selected_month and "-" in selected_month:
        selected_month = selected_month.replace("-", "/")

    # 適用年月一覧を取得（有効な商品のみ）
    available_months = (
        PriceHistory.objects.filter(product__is_active=True, is_active=True)
        .values_list("effective_year_month", flat=True)
        .distinct()
        .order_by("-effective_year_month")
    )

    # sort_numが未設定の商品に初期値を設定（条件付き）
    from django.db.models import Q

    if Product.objects.filter(
        Q(sort_num=0) | Q(sort_num__isnull=True), is_active=True
    ).exists():
        _initialize_sort_numbers()

    # 商品フィルターを適用（ノーマライズ検索）
    products_query = Product.objects.filter(is_active=True)

    if manufacturer_filter:
        # 全角・半角英数字のみ正規化して部分一致検索
        def normalize_simple(text):
            if not text:
                return ""
            text = unicodedata.normalize("NFKC", text)
            return text.upper()

        normalized_manufacturer = normalize_simple(manufacturer_filter)
        products_query = products_query.filter(
            manufacturer__name__icontains=normalized_manufacturer
        )

    if product_name_filter:
        # 全角・半角英数字のみ正規化して部分一致検索
        def normalize_simple(text):
            if not text:
                return ""
            text = unicodedata.normalize("NFKC", text)
            return text.upper()

        normalized_filter = normalize_simple(product_name_filter)
        products_query = products_query.filter(
            product_name__icontains=normalized_filter
        )

    # 全ての有効な商品を取得（関連データも一括取得）
    all_products = products_query.select_related(
        "livestock_type", "category", "manufacturer"
    ).order_by("livestock_type", "category", "manufacturer", "sort_num", "product_name")

    # 商品IDリストを取得
    product_ids = list(all_products.values_list("id", flat=True))

    # 価格履歴を一括取得してマッピング
    price_histories = {}
    previous_month_prices = {}

    # 前月を計算
    previous_month = None
    if selected_month:
        try:
            year, month = selected_month.split("/")
            year, month = int(year), int(month)
            if month == 1:
                previous_month = f"{year-1}/12"
            else:
                previous_month = f"{year}/{month-1:02d}"
        except:
            pass

    if selected_month:
        # サブクエリで各商品の最新価格履歴IDを取得
        from django.db.models import OuterRef, Subquery

        latest_histories = (
            PriceHistory.objects.filter(
                product=OuterRef("product"),
                is_active=True,
                effective_year_month__lte=selected_month,
            )
            .order_by("-effective_year_month")
            .values("id")[:1]
        )

        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories), product_id__in=product_ids
        ).select_related("product")

        # 前月価格履歴も取得
        if previous_month:
            prev_latest_histories = (
                PriceHistory.objects.filter(
                    product=OuterRef("product"),
                    is_active=True,
                    effective_year_month__lte=previous_month,
                )
                .order_by("-effective_year_month")
                .values("id")[:1]
            )

            prev_histories = PriceHistory.objects.filter(
                id__in=Subquery(prev_latest_histories), product_id__in=product_ids
            ).select_related("product")

            # 前月価格履歴マップを作成
            for prev_history in prev_histories:
                kenren_price = prev_history.kenren_price
                if (
                    not kenren_price
                    and prev_history.wholesale_price
                    and prev_history.wholesale_price != "都度見積"
                ):
                    try:
                        wholesale = float(
                            str(prev_history.wholesale_price).replace(",", "")
                        )
                        margin = float(prev_history.gross_margin_rate)
                        kenren_price = int(round(wholesale / margin / 10) * 10)
                    except:
                        kenren_price = "都度見積"
                previous_month_prices[prev_history.product_id] = {
                    "kenren_price": kenren_price,
                    "wholesale_price": prev_history.wholesale_price,
                }
    else:
        # 最新の価格履歴を取得
        from django.db.models import OuterRef, Subquery

        latest_histories = (
            PriceHistory.objects.filter(product=OuterRef("product"), is_active=True)
            .order_by("-effective_year_month")
            .values("id")[:1]
        )

        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories), product_id__in=product_ids
        ).select_related("product")

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
        has_valid_price = (
            price_history is not None and price_history.wholesale_price != 0
        )

        # 商品と価格履歴のペアを作成
        is_current_month = False
        if price_history and previous_month_prices.get(product.id) is not None:
            # 前月価格と現在価格を比較
            current_price = price_history.kenren_price
            if (
                not current_price
                and price_history.wholesale_price
                and price_history.wholesale_price != "都度見積"
            ):
                try:
                    wholesale = float(
                        str(price_history.wholesale_price).replace(",", "")
                    )
                    margin = float(price_history.gross_margin_rate)
                    current_price = int(round(wholesale / margin / 10) * 10)
                except:
                    current_price = "都度見積"

            prev_price = previous_month_prices.get(product.id)
            if prev_price:
                prev_kenren = (
                    prev_price.get("kenren_price")
                    if isinstance(prev_price, dict)
                    else prev_price
                )

            # 価格変動があった場合のみ色付け
            if current_price != prev_kenren:
                is_current_month = True

        product_data.append(
            {
                "product": product,
                "price_history": price_history,
                "has_price": has_valid_price,
                "is_group_start": is_group_start,
                "is_current_month": is_current_month,
                "previous_month_price": previous_month_prices.get(product.id),
            }
        )

    # ページネーション
    paginator = Paginator(product_data, 200)  # 200件ずつ表示
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "current_user": get_current_user(),
        "page_obj": page_obj,
        "available_months": available_months,
        "selected_month": selected_month,
        "breadcrumbs": get_breadcrumbs("integrated_pricelist"),
    }
    return render(request, "products_master/integrated_pricelist.html", context)


def update_sort_order(request):
    """ソート順序更新API"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POSTメソッドが必要です"})

    try:
        data = json.loads(request.body)
        updates = data.get("updates", [])

        if not updates:
            return JsonResponse({"success": False, "message": "更新データがありません"})

        # 一括更新
        with transaction.atomic():
            for update in updates:
                product_id = update.get("product_id")
                sort_num = update.get("sort_num")

                if product_id and sort_num is not None:
                    Product.objects.filter(pk=product_id).update(sort_num=sort_num)

        return JsonResponse({"success": True, "message": "ソート順序を更新しました"})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"エラー: {str(e)}"})


def export_excel(request):
    """デジタル価格表のExcel出力（フィルタリング対応）"""
    import logging

    logger = logging.getLogger(__name__)

    def format_price_for_excel(value):
        """価格をExcel用にフォーマット（数値のみ3桁区切り）"""
        if not value or value == "-" or value == "都度見積":
            return value
        try:
            # 数値に変換できる場合は3桁区切りを追加
            num_value = float(str(value).replace(",", ""))
            if num_value == int(num_value):
                return f"{int(num_value):,}"
            else:
                return f"{num_value:,.0f}"
        except (ValueError, TypeError):
            # 数値でない場合はそのまま返す
            return str(value)

    selected_month = request.GET.get("month", "")
    manufacturer_filter = request.GET.get("manufacturer", "").strip()
    product_name_filter = request.GET.get("product_name", "").strip()
    exclude_wholesale = request.GET.get("exclude_wholesale") == "1"

    logger.info(
        f"Excel出力開始 - selected_month: {selected_month}, manufacturer: {manufacturer_filter}, product_name: {product_name_filter}, exclude_wholesale: {exclude_wholesale}"
    )

    if selected_month and "-" in selected_month:
        selected_month = selected_month.replace("-", "/")

    _initialize_sort_numbers()

    # 画面と同じフィルタリング条件を適用
    products_query = Product.objects.filter(is_active=True)

    if manufacturer_filter:

        def normalize_simple(text):
            if not text:
                return ""
            text = unicodedata.normalize("NFKC", text)
            return text.upper()

        normalized_manufacturer = normalize_simple(manufacturer_filter)
        products_query = products_query.filter(
            manufacturer__name__icontains=normalized_manufacturer
        )

    if product_name_filter:

        def normalize_simple(text):
            if not text:
                return ""
            text = unicodedata.normalize("NFKC", text)
            return text.upper()

        normalized_filter = normalize_simple(product_name_filter)
        products_query = products_query.filter(
            product_name__icontains=normalized_filter
        )

    # データ取得を最適化（フィルタリング済み）
    all_products = (
        products_query.select_related("livestock_type", "category", "manufacturer")
        .only(
            "id",
            "product_name",
            "model_number",
            "specification",
            "shipping_unit",
            "remarks",
            "sort_num",
            "livestock_type__name",
            "category__name",
            "manufacturer__name",
        )
        .order_by(
            "livestock_type", "category", "manufacturer", "sort_num", "product_name"
        )
    )

    # 商品データを即座にリスト化してDBコネクションを解放
    product_list = list(all_products)
    product_ids = [p.id for p in product_list]

    # 価格履歴を一括取得
    if selected_month:
        from django.db.models import OuterRef, Subquery

        latest_histories = (
            PriceHistory.objects.filter(
                product=OuterRef("product"),
                is_active=True,
                effective_year_month__lte=selected_month,
            )
            .order_by("-effective_year_month")
            .values("id")[:1]
        )

        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories), product_id__in=product_ids
        )
    else:
        from django.db.models import OuterRef, Subquery

        latest_histories = (
            PriceHistory.objects.filter(product=OuterRef("product"), is_active=True)
            .order_by("-effective_year_month")
            .values("id")[:1]
        )

        histories = PriceHistory.objects.filter(
            id__in=Subquery(latest_histories), product_id__in=product_ids
        )

    # 価格履歴も即座にリスト化してDBコネクションを解放
    price_histories = {h.product_id: h for h in list(histories)}

    # 前月価格履歴を取得
    previous_month_prices = {}
    previous_month = None
    if selected_month:
        try:
            year, month = selected_month.split("/")
            year, month = int(year), int(month)
            if month == 1:
                previous_month = f"{year-1}/12"
            else:
                previous_month = f"{year}/{month-1:02d}"
        except:
            pass

    if previous_month:
        prev_latest_histories = (
            PriceHistory.objects.filter(
                product=OuterRef("product"),
                is_active=True,
                effective_year_month__lte=previous_month,
            )
            .order_by("-effective_year_month")
            .values("id")[:1]
        )

        prev_histories = PriceHistory.objects.filter(
            id__in=Subquery(prev_latest_histories), product_id__in=product_ids
        )

        for prev_history in prev_histories:
            kenren_price = prev_history.kenren_price
            if (
                not kenren_price
                and prev_history.wholesale_price
                and prev_history.wholesale_price != "都度見積"
            ):
                try:
                    wholesale = float(
                        str(prev_history.wholesale_price).replace(",", "")
                    )
                    margin = float(prev_history.gross_margin_rate)
                    kenren_price = int(round(wholesale / margin / 10) * 10)
                except:
                    kenren_price = "都度見積"
            previous_month_prices[prev_history.product_id] = {
                "kenren_price": kenren_price,
                "wholesale_price": prev_history.wholesale_price,
            }

    # 価格ありかつ仕切価格0円以外の商品のみフィルタ
    product_data = []
    for product in product_list:
        price_history = price_histories.get(product.id)
        if price_history and price_history.wholesale_price != 0:
            product_data.append(
                {
                    "product": product,
                    "price_history": price_history,
                    "has_price": True,
                    "previous_month_price": previous_month_prices.get(product.id),
                }
            )

    # テンプレートファイルを読み込み
    # config.iniからテンプレートパスを取得
    config = configparser.ConfigParser()
    template_path = None

    if CONFIG_PATH.exists():
        try:
            config.read(CONFIG_PATH, encoding="utf-8")
            template_path = config.get("FILES", "excel_template", fallback=None)
        except Exception:
            pass

    # テンプレートパスが設定されていない場合のフォールバック
    if not template_path:
        # PyInstaller環境でのテンプレートパス取得
        if getattr(sys, "frozen", False):
            # PyInstaller環境では一時フォルダから取得
            template_path = os.path.join(sys._MEIPASS, "degital_value_list.xlsx")
        else:
            # 開発環境では従来通り
            # template_path = os.path.join(settings.BASE_DIR, 'degital_value_list.xlsx')
            template_path = os.path.join(settings.BASE_DIR, "degital_value_list.xlsx")

    logger.info(
        f"使用するExcelテンプレート: {template_path} {'(存在)' if os.path.exists(template_path) else '(存在しない)'}"
    )

    try:
        wb = openpyxl.load_workbook(template_path)
        # [価格表]シートを指定（存在しない場合はアクティブシートを使用）
        try:
            ws = wb["価格表"]
        except KeyError:
            ws = wb.active

        # デフォルト行の高さを110ピクセルに設定
        ws.sheet_format.defaultRowHeight = 110

        # 表紙シートの{sysdate}、{effective_date}、{status}を置き換え
        try:
            cover_sheet = wb["表紙"]
            now = datetime.now()
            current_date = f"{now.year}年{now.month}月{now.day}日"

            # 選択した適用月の1日を作成
            effective_date_str = ""
            if selected_month:
                try:
                    year, month = selected_month.split("/")
                    effective_date_str = f"{year}年{int(month)}月1日"
                except:
                    effective_date_str = ""

            # 承認状態を取得
            is_approved = _check_approval_pdf(selected_month)
            status_str = "" if is_approved else "(未承認版)"

            for row in cover_sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        if "{sysdate}" in cell.value:
                            cell.value = cell.value.replace("{sysdate}", current_date)
                        if "{effective_date}" in cell.value and effective_date_str:
                            cell.value = cell.value.replace(
                                "{effective_date}", effective_date_str
                            )
                        if "{status}" in cell.value:
                            cell.value = cell.value.replace("{status}", status_str)
        except KeyError:
            pass  # 表紙シートがない場合はスキップ

    except FileNotFoundError:
        # テンプレートがない場合は新規作成
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "価格表"

        # デフォルト行の高さを110ピクセルに設定
        ws.sheet_format.defaultRowHeight = 110

        headers = [
            "№",
            "畜種",
            "分類",
            "メーカー",
            "商品名",
            "型式",
            "規格",
            "発送単位",
            "【{prev_month}】仕切価格",
            "【{yyyy.mm}～】仕切価格",
            "【{prev_month}】県連価格",
            "【{yyyy.mm}～】県連価格",
            "改定額",
            "【{yyyy.mm}】参考小売価格",
            "送料",
            "備考",
            "改定理由",
        ]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color="4472C4", end_color="4472C4", fill_type="solid"
            )
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # 既存データをクリア（5行目以降のデータ行）
    for row in range(5, ws.max_row + 1):
        for col in range(1, 18):  # 17列目までクリア
            ws.cell(row=row, column=col).value = None

    # ヘッダーの年月を更新
    if selected_month:
        # yyyy/mm形式をyyyy.mm形式に変換
        display_month = selected_month.replace("/", ".")

        # 前月をyyyy.mm形式に変換
        prev_display_month = ""
        if previous_month:
            prev_display_month = previous_month.replace("/", ".")

        # 全シートの{prev_month}を置き換え
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        if "{prev_month}" in cell.value and prev_display_month:
                            cell.value = cell.value.replace(
                                "{prev_month}", prev_display_month
                            )
                        if "{yyyy.mm}" in cell.value:
                            cell.value = cell.value.replace("{yyyy.mm}", display_month)

    # テンプレート行（4行目）の書式を取得
    template_row = 4

    row_num = 4
    excel_row_num = 1
    for item in product_data:
        product = item["product"]
        price_history = item["price_history"]
        has_price = item["has_price"]

        # 価格なしの商品はExcelに出���しない
        # 既に価格ありの商品のみフィルタ済み

        excel_row_num += 1

        kenren_price = ""
        if price_history.kenren_price:
            try:
                kenren_price = int(
                    float(str(price_history.kenren_price).replace(",", ""))
                )
            except:
                kenren_price = price_history.kenren_price
        else:
            try:
                if (
                    price_history.wholesale_price
                    and price_history.wholesale_price != "都度見積"
                ):
                    wholesale = float(
                        str(price_history.wholesale_price).replace(",", "")
                    )
                    margin = float(price_history.gross_margin_rate)
                    kenren_price = int(round(wholesale / margin / 10) * 10)
                else:
                    kenren_price = "都度見積"
            except:
                kenren_price = "都度見積"

        retail_price = ""
        if price_history.retail_price:
            try:
                retail_price = int(
                    float(str(price_history.retail_price).replace(",", ""))
                )
            except:
                retail_price = price_history.retail_price
        else:
            retail_price = "-"

        revision_amount = ""
        try:
            revision_amount = price_history.get_revision_amount()
        except:
            revision_amount = 0

        # 前月価格を取得
        previous_month_wholesale = ""
        previous_month_kenren = ""
        if item.get("previous_month_price"):
            prev_data = item["previous_month_price"]
            if isinstance(prev_data, dict):
                if prev_data.get("wholesale_price"):
                    try:
                        previous_month_wholesale = int(
                            float(str(prev_data["wholesale_price"]).replace(",", ""))
                        )
                    except:
                        previous_month_wholesale = prev_data["wholesale_price"]
                else:
                    previous_month_wholesale = "-"

                if prev_data.get("kenren_price"):
                    try:
                        previous_month_kenren = int(
                            float(str(prev_data["kenren_price"]).replace(",", ""))
                        )
                    except:
                        previous_month_kenren = prev_data["kenren_price"]
                else:
                    previous_month_kenren = "-"
            else:
                previous_month_kenren = prev_data
                previous_month_wholesale = "-"
        else:
            previous_month_wholesale = "-"
            previous_month_kenren = "-"

        # 価格をフォーマット
        wholesale_price_formatted = format_price_for_excel(
            price_history.wholesale_price
        )
        kenren_price_formatted = format_price_for_excel(kenren_price)
        retail_price_formatted = format_price_for_excel(retail_price)
        previous_month_wholesale_formatted = format_price_for_excel(
            previous_month_wholesale
        )
        previous_month_kenren_formatted = format_price_for_excel(previous_month_kenren)

        # 改定理由は指定月に改定が発生した場合のみ表示
        revision_reason = ""
        if selected_month:
            current_month_history = PriceHistory.objects.filter(
                product_id=product.id,
                is_active=True,
                effective_year_month=selected_month,
            ).first()
            if current_month_history:
                revision_reason = current_month_history.revision_reason or ""

        data = [
            excel_row_num - 1,
            str(product.livestock_type or ""),
            str(product.category or ""),
            str(product.manufacturer or ""),
            product.product_name or "",
            product.model_number or "",
            product.specification or "",
            product.shipping_unit or "",
            previous_month_wholesale_formatted,
            wholesale_price_formatted,
            previous_month_kenren_formatted,
            kenren_price_formatted,
            revision_amount,
            retail_price_formatted,
            (
                price_history.shipping_fee.replace("\r\n", "\n")
                if price_history and price_history.shipping_fee
                else ""
            ),
            product.remarks or "",
            revision_reason,
        ]

        # データを書き込み
        for col, value in enumerate(data, 1):
            ws.cell(row=row_num, column=col, value=value)

        row_num += 1

    # テンプレート行（4行目）の書式をコピー
    if row_num > 4:
        template_styles = []
        for col in range(1, 18):  # 17列目まで拡張
            template_cell = ws.cell(row=4, column=col)
            # wrap_text設定を確認してログ出力
            if col == 15:  # 送料列（O列）
                wrap_text = (
                    template_cell.alignment.wrap_text
                    if template_cell.alignment
                    else False
                )
                logger.info(f"テンプレート送料列のwrap_text設定: {wrap_text}")

                # 行の高さの自動調整設定を確認
                row_height = ws.row_dimensions[4].height
                auto_fit = ws.row_dimensions[4].height is None
                logger.info(
                    f"テンプレート4行目の高さ設定: {row_height}, 自動調整: {auto_fit}"
                )

            template_styles.append(
                {
                    "font": template_cell.font.copy() if template_cell.font else None,
                    "border": (
                        template_cell.border.copy() if template_cell.border else None
                    ),
                    "fill": template_cell.fill.copy() if template_cell.fill else None,
                    "alignment": (
                        template_cell.alignment.copy()
                        if template_cell.alignment
                        else None
                    ),
                    "number_format": template_cell.number_format,
                }
            )

        # データ行にスタイルを適用
        gray_fill = PatternFill(
            start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"
        )
        yellow_fill = PatternFill(
            start_color="FFFF99", end_color="FFFF99", fill_type="solid"
        )  # 改定額0以外の色

        for row in range(4, row_num):
            is_gray_row = (row - 4) % 2 == 1  # 奇数行をグレーに

            # 該当行の商品データを取得
            item_index = row - 4  # rowは4から開始、product_dataは0から開始
            if item_index < len(product_data):
                item = product_data[item_index]
                price_history = item["price_history"]
                prev_price = item.get("previous_month_price")

                # 前月価格と現在価格を比較
                has_revision = False
                if price_history and prev_price is not None:
                    current_price = price_history.kenren_price
                    if (
                        not current_price
                        and price_history.wholesale_price
                        and price_history.wholesale_price != "都度見積"
                    ):
                        try:
                            wholesale = float(
                                str(price_history.wholesale_price).replace(",", "")
                            )
                            margin = float(price_history.gross_margin_rate)
                            current_price = int(round(wholesale / margin / 10) * 10)
                        except:
                            current_price = "都度見積"

                    # 前月県連価格を取得
                    prev_kenren_price = (
                        prev_price.get("kenren_price")
                        if isinstance(prev_price, dict)
                        else prev_price
                    )

                    # 価格変動があった場合のみ色付け
                    if current_price != prev_kenren_price:
                        has_revision = True
            else:
                has_revision = False

            for col in range(1, 19):  # 18列目まで拡張（ダミーカラム含む）
                cell = ws.cell(row=row, column=col)
                if col <= 17:
                    # 通常のデータ列
                    style = template_styles[col - 1]
                    if style["font"]:
                        cell.font = style["font"]
                    if style["border"]:
                        cell.border = style["border"]

                    # 背景色の優先順位：改定額あり > グレー行 > デフォルト
                    if has_revision:
                        cell.fill = yellow_fill
                    elif is_gray_row:
                        cell.fill = gray_fill
                    elif style["fill"]:
                        cell.fill = style["fill"]

                    if style["alignment"]:
                        cell.alignment = style["alignment"]
                    if style["number_format"]:
                        cell.number_format = style["number_format"]

                    # --- 2026/06/04 【ここから追加】特定の列で値がハイフンの場合に中央寄せにする ---
                    if col in [16, 17]:
                        # セルの値を取得し、文字列の左右の空白を削る
                        cell_val = (
                            str(cell.value).strip() if cell.value is not None else ""
                        )
                        if cell_val in ["-", "ー", "－", "―"]:
                            cell.alignment = Alignment(
                                horizontal="center", vertical="center"
                            )
                    # --- 2026/06/04【ここまで追加】 ---
                else:
                    # ダミーカラム（18列目）はテンプレートからコピー
                    template_dummy_cell = ws.cell(row=4, column=18)
                    if template_dummy_cell.font:
                        cell.font = template_dummy_cell.font.copy()
                    if template_dummy_cell.border:
                        cell.border = template_dummy_cell.border.copy()
                    if template_dummy_cell.fill:
                        cell.fill = template_dummy_cell.fill.copy()
                    if template_dummy_cell.alignment:
                        cell.alignment = template_dummy_cell.alignment.copy()

    # 仕切価格列を除外する場合は列を非表示にする
    if exclude_wholesale:
        # I列（前月仕切価格）とJ列（仕切価格）を非表示
        ws.column_dimensions[get_column_letter(9)].hidden = True
        ws.column_dimensions[get_column_letter(10)].hidden = True

    # 承認状態をチェック
    is_approved = _check_approval_pdf(selected_month)
    approval_status = "確定版" if is_approved else "未承認版"

    # 未承認版の表示（セル結合で目立たせる）
    if not is_approved:
        # A1:D2を結合して大きな警告を表示
        ws.merge_cells("A1:D2")
        warning_cell = ws["A1"]
        warning_cell.value = "【未承認版】"
        warning_cell.font = Font(
            bold=True, color="FFFFFF", size=30
        )  # 白文字、30ポイント
        warning_cell.fill = PatternFill(
            start_color="FF0000", end_color="FF0000", fill_type="solid"
        )  # 赤背景
        warning_cell.alignment = Alignment(
            horizontal="center", vertical="center"
        )  # 中央揃え

    if selected_month:
        filename = (
            f'{selected_month.replace("/", "")}デジタル価格表_{approval_status}.xlsx'
        )
    else:
        filename = (
            f'{datetime.now().strftime("%Y%m")}デジタル価格表_{approval_status}.xlsx'
        )

    # 最終出力用に保存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    # UTF-8エンコードでファイル名を設定
    encoded_filename = urllib.parse.quote(filename.encode("utf-8"))
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"

    return response


def reset_sort_order(request):
    """ソート順序リセットAPI"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POSTメソッドが必要です"})

    try:
        # 全商品のsort_numを0にリセット
        with transaction.atomic():
            Product.objects.filter(is_active=True).update(sort_num=0)

        return JsonResponse(
            {"success": True, "message": "ソート順序をリセットしました"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": f"エラー: {str(e)}"})


def cross_page_move(request):
    """ページ境界移動API"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POSTメソッドが必要です"})

    try:
        data = json.loads(request.body)
        product_id = data.get("product_id")
        direction = data.get("direction")  # 'prev' or 'next'
        current_page = data.get("current_page", 1)

        if not product_id or direction not in ["prev", "next"]:
            return JsonResponse({"success": False, "message": "パラメータが不正です"})

        # 対象商品を取得
        target_product = Product.objects.get(pk=product_id, is_active=True)

        # 同じグループの商品を取得
        group_products = Product.objects.filter(
            livestock_type=target_product.livestock_type,
            category=target_product.category,
            manufacturer=target_product.manufacturer,
            is_active=True,
        ).order_by("sort_num", "product_name")

        products_list = list(group_products)
        target_index = next(
            (i for i, p in enumerate(products_list) if p.id == product_id), None
        )

        if target_index is None:
            return JsonResponse({"success": False, "message": "商品が見つかりません"})

        # 移動先を決定
        if direction == "prev":
            # 前ページの末尾へ（一つ前の商品と入れ替え）
            if target_index == 0:
                return JsonResponse(
                    {"success": False, "message": "これ以上上に移動できません"}
                )
            swap_index = target_index - 1
        else:  # next
            # 次ページの先頭へ（一つ後の商品と入れ替え）
            if target_index >= len(products_list) - 1:
                return JsonResponse(
                    {"success": False, "message": "これ以上下に移動できません"}
                )
            swap_index = target_index + 1

        # 商品を入れ替え
        with transaction.atomic():
            products_list[target_index], products_list[swap_index] = (
                products_list[swap_index],
                products_list[target_index],
            )

            # sort_numを更新
            for i, product in enumerate(products_list, 1):
                product.sort_num = i
                product.save(update_fields=["sort_num"])

        # リダイレクトURLを構築
        from django.urls import reverse

        redirect_page = current_page
        if direction == "prev" and current_page > 1:
            redirect_page = current_page - 1
        elif direction == "next":
            redirect_page = current_page + 1

        redirect_url = (
            reverse("products_master:integrated_pricelist") + f"?page={redirect_page}"
        )

        return JsonResponse(
            {
                "success": True,
                "message": "商品を移動しました",
                "redirect_url": redirect_url,
            }
        )

    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": "商品が見つかりません"})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"エラー: {str(e)}"})


def upload_approval_pdf(request):
    """承認PDFアップロード機能"""
    if request.method == "POST":
        try:
            year_month = request.POST.get("year_month")
            pdf_file = request.FILES.get("pdf_file")

            if not year_month or not pdf_file:
                messages.error(request, "年月とPDFファイルを選択してください")
                return redirect("products_master:upload_approval_pdf")

            # ファイル拡張子チェック
            if not pdf_file.name.lower().endswith(".pdf"):
                messages.error(request, "PDFファイルを選択してください")
                return redirect("products_master:upload_approval_pdf")

            # YYYY-MMをYYYY/MMに変換
            if "-" in year_month:
                year_month = year_month.replace("-", "/")

            # ファイル名を生成
            approval_month = year_month.replace("/", "")

            # 保存ディレクトリをconfig.iniのmedia_rootから取得
            from digital_pricelist_system.settings import get_media_root

            media_root = get_media_root()
            approval_dir = media_root / "approval"
            approval_dir.mkdir(parents=True, exist_ok=True)

            # ファイルを保存
            file_path = approval_dir / f"{approval_month}_approval.pdf"
            with open(file_path, "wb") as f:
                for chunk in pdf_file.chunks():
                    f.write(chunk)

            # テーブルに記録（既存の場合は更新）
            ApprovalPdf.objects.update_or_create(
                year_month=year_month,
                defaults={
                    "pdf_file_path": str(file_path),
                    "uploaded_by": get_current_user(),
                },
            )

            # 古いPDFを自動削除
            _cleanup_old_approval_pdfs()

            messages.success(request, f"{year_month}の承認PDFをアップロードしました")
            return redirect("products_master:upload_approval_pdf")

        except Exception as e:
            messages.error(request, f"アップロード中にエラーが発生しました: {str(e)}")
            return redirect("products_master:upload_approval_pdf")

    # 既存の承認PDF一覧を取得（3年度以内のデータのみ）
    from datetime import datetime

    current_date = datetime.now()

    # 現在の年度を計算（4月～3月）
    if current_date.month >= 4:
        current_fiscal_year = current_date.year
    else:
        current_fiscal_year = current_date.year - 1

    # 3年度前の3月までを削除対象とする
    cutoff_fiscal_year = current_fiscal_year - 3
    cutoff_month = f"{cutoff_fiscal_year + 1}/3"  # 3年度前の3月以降のデータを表示

    approved_pdfs = ApprovalPdf.objects.filter(year_month__gt=cutoff_month).order_by(
        "-year_month"
    )

    context = {
        "current_user": get_current_user(),
        "approved_pdfs": approved_pdfs,
        "breadcrumbs": get_breadcrumbs("upload_approval_pdf"),
    }
    return render(request, "products_master/upload_approval_pdf.html", context)


def _cleanup_old_approval_pdfs():
    """古い承認PDFを自動削除（3年度以上前のデータ）"""
    try:
        from datetime import datetime
        import os

        current_date = datetime.now()

        # 現在の年度を計算（4月～3月）
        if current_date.month >= 4:
            current_fiscal_year = current_date.year
        else:
            current_fiscal_year = current_date.year - 1

        # 3年度前の3月までを削除対象とする
        cutoff_fiscal_year = current_fiscal_year - 3
        cutoff_month = f"{cutoff_fiscal_year + 1}/3"  # 3年度前の3月までを削除対象

        # 削除対象のPDFを取得
        old_pdfs = ApprovalPdf.objects.filter(year_month__lte=cutoff_month)

        deleted_count = 0
        for pdf in old_pdfs:
            try:
                # ファイルを削除
                if os.path.exists(pdf.pdf_file_path):
                    os.remove(pdf.pdf_file_path)

                # DBレコードを削除
                pdf.delete()
                deleted_count += 1

            except Exception as e:
                # ログ出力はしない（サイレントに続行）
                continue

        return deleted_count

    except Exception:
        # エラーが発生してもメイン処理に影響しないようにサイレントに処理
        return 0


def download_approval_pdf(request, pk):
    """承認PDFダウンロード"""
    try:
        approval_pdf = ApprovalPdf.objects.get(pk=pk)

        if not os.path.exists(approval_pdf.pdf_file_path):
            messages.error(request, "ファイルが見つかりません")
            return redirect("products_master:upload_approval_pdf")

        with open(approval_pdf.pdf_file_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/pdf")
            filename = f'{approval_pdf.year_month.replace("/", "")}_approval.pdf'
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

    except ApprovalPdf.DoesNotExist:
        messages.error(request, "承認PDFが見つかりません")
        return redirect("products_master:upload_approval_pdf")
    except Exception as e:
        messages.error(request, f"ダウンロード中にエラーが発生しました: {str(e)}")
        return redirect("products_master:upload_approval_pdf")
