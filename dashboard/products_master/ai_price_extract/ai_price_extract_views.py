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
from dashboard.products_master.pdf_processing.extract_di_only import (
    main as extract_di_main,
)
from dashboard.products_master.pdf_processing.process_ai_simple import (
    main as process_ai_main,
)
from dashboard.products_master.models import (
    Product,
    PriceHistoryApproval,
    ProductApproval,
    ProductGrossMarginRate,
)
from dashboard.products_master.ai_extract_models import (
    AIExtractTransaction,
    AIExtractTransactionDetail,
)
from dashboard.products_master.ai_services import process_extraction_results
from dashboard.products_master.forms import PDFUploadForm
from dashboard.products_master.product_detail.product_detail_views import (
    _process_approval,
)
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

# 20260710追加
from dashboard.products_master.models import ProductGrossMarginRate

# 追加終了


def ai_extract(request):
    """AI価格抽出入力画面"""
    pdf_form = PDFUploadForm()

    context = {
        "current_user": get_current_user(),
        "breadcrumbs": _get_dynamic_breadcrumbs_for_ai_extract(request),
        "pdf_form": pdf_form,
    }
    return render(request, "products_master/ai_extract_input.html", context)


def ai_extract_process(request):
    """AI価格抽出処理"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        # JSONデータを取得
        json_text = request.POST.get("json_data", "")
        if not json_text:
            return JsonResponse({"error": "JSONデータが入力されていません"}, status=400)

        # JSON解析
        json_data = json.loads(json_text)

        # 空文字をnullに正規化
        if "products" in json_data:
            for product in json_data["products"]:
                for key, value in product.items():
                    if value == "":
                        product[key] = None

        # 照合トランザクションを作成
        transaction_id = (
            f"MATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        )
        match_transaction = AIExtractTransaction.objects.create(
            transaction_id=transaction_id,
            executor=get_current_user(),
            effective_year_month="",  # 照合段階では未定
            revision_reason="",
            total_products=len(json_data.get("products", [])),
            status="照合中",
        )

        # 商品照合処理
        results = process_extraction_results(json_data)

        # 照合結果を明細テーブルに保存
        for i, result in enumerate(results.get("results", [])):
            extracted_data = result.get("extracted_data", {})
            candidates = result.get("candidates", [])

            # 最高スコアの候補を取得
            matched_product = None
            match_score = None
            if candidates:
                best_candidate = candidates[0]
                matched_product_id = best_candidate.get("product", {}).get("pk")
                if matched_product_id:
                    try:
                        matched_product = Product.objects.get(pk=matched_product_id)
                        match_score = best_candidate.get("score", 0)
                    except Product.DoesNotExist:
                        pass

            AIExtractTransactionDetail.objects.create(
                transaction=match_transaction,
                sequence=i + 1,
                extracted_product_name=extracted_data.get("product_name"),
                extracted_model_number=extracted_data.get("model_number"),
                extracted_manufacturer=extracted_data.get("manufacturer"),
                extracted_specification=extracted_data.get("specification"),
                extracted_price=str(extracted_data.get("new_price", "")),
                extracted_retail_price=(
                    str(extracted_data.get("retail_price", ""))
                    if extracted_data.get("retail_price")
                    else None
                ),
                # extracted_kenren_price=(
                #     str(extracted_data.get("kenren_price", ""))
                #     if extracted_data.get("kenren_price")
                #     else None
                # ),
                # extracted_shipping_fee=(
                #     str(extracted_data.get("shipping_fee", ""))
                #     if extracted_data.get("shipping_fee")
                #     else None
                # ),
                # extracted_gross_margin=(
                #     str(extracted_data.get("gross_margin", ""))
                #     if extracted_data.get("gross_margin")
                #     else None
                # ),
                extracted_revision_reason=extracted_data.get(
                    "revision_reason"
                ),  # 改定理由を保存
                matched_product=matched_product,
                match_score=match_score,
                status="未処理",
            )

        return JsonResponse(
            {
                "success": True,
                "redirect_url": f"/products/ai-extract/history/{match_transaction.pk}/",
            }
        )

    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"JSON解析エラー: {str(e)}"}, status=400)
    except ImportError as e:
        return JsonResponse({"error": f"ライブラリエラー: {str(e)}"}, status=500)
    except Exception as e:
        error_detail = traceback.format_exc()
        return JsonResponse(
            {"error": f"処理エラー: {str(e)}", "detail": error_detail}, status=500
        )


def _process_ai_extract_submission(request, results, json_data):
    """AI抽出結果からの申請データ作成処理（商品詳細の申請ロジックを使用）"""
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"=== AI価格抽出申請処理開始 ===")

        # 適用年月を取得
        effective_year_month = request.POST.get("effective_year_month")
        if not effective_year_month:
            messages.error(request, "適用年月を指定してください。")
            return redirect(request.path)

        # 一括改定理由を取得
        revision_reason = request.POST.get("revision_reason", "AI価格抽出による更新")

        # 照合時に作成されたトランザクションを取得・更新
        transaction_id = request.session.get("ai_extract_transaction_id")
        if transaction_id:
            transaction = AIExtractTransaction.objects.get(
                transaction_id=transaction_id
            )
            transaction.effective_year_month = effective_year_month.replace("-", "/")
            transaction.revision_reason = revision_reason
            transaction.status = "申請中"
            transaction.save()
        else:
            transaction_id = (
                f"AI_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            )
            transaction = AIExtractTransaction.objects.create(
                transaction_id=transaction_id,
                executor=get_current_user(),
                effective_year_month=effective_year_month.replace("-", "/"),
                revision_reason=revision_reason,
                total_products=len(results.get("results", [])),
                status="申請中",
            )

        created_count = 0
        skipped_count = 0

        for i, result in enumerate(results.get("results", [])):
            product_match = request.POST.get(f"product_match_{i}")

            detail, created = AIExtractTransactionDetail.objects.get_or_create(
                transaction=transaction,
                sequence=i + 1,
                defaults={
                    "extracted_product_name": result.get("extracted_data", {}).get(
                        "product_name"
                    ),
                    "extracted_model_number": result.get("extracted_data", {}).get(
                        "model_number"
                    ),
                    "extracted_manufacturer": result.get("extracted_data", {}).get(
                        "manufacturer"
                    ),
                    "extracted_specification": result.get("extracted_data", {}).get(
                        "specification"
                    ),
                    "status": "未処理",
                },
            )

            if detail.status in ["スキップ", "申請済"]:
                continue

            if not product_match:
                detail.status = "スキップ"
                detail.selected_candidate_text = "スキップ"
                detail.error_message = "商品が選択されていません"
                detail.save()
                skipped_count += 1
                continue

            try:
                product = Product.objects.get(pk=product_match)
            except Product.DoesNotExist:
                detail.status = "エラー"
                detail.error_message = f"商品ID {product_match} が見つかりません"
                detail.save()
                continue

            if (
                product.status == "申請中"
                or ProductApproval.objects.filter(
                    product_number=product.pk, is_active=True
                ).exists()
            ):
                detail.status = "エラー"
                detail.error_message = "既に申請中です"
                detail.save()
                continue

            # フォームから新価格を取得
            new_price_str = request.POST.get(f"new_price_{i}")
            retail_price_str = request.POST.get(f"retail_price_{i}")
            kenren_price_str = request.POST.get(f"kenren_price_{i}")
            shipping_fee_str = request.POST.get(f"shipping_fee_{i}")
            gross_margin_str = request.POST.get(f"gross_margin_{i}")

            if not new_price_str:
                detail.status = "エラー"
                detail.error_message = "新価格が入力されていません"
                detail.save()
                continue

            try:
                new_price = Decimal(str(new_price_str).strip())
            except (ValueError, TypeError):
                detail.status = "エラー"
                detail.error_message = f"新価格「{new_price_str}」が無効です"
                detail.save()
                continue

            year, month = map(int, effective_year_month.split("-"))
            individual_reason_str = request.POST.get(f"revision_reason_{i}", "").strip()
            final_reason = (
                individual_reason_str if individual_reason_str else revision_reason
            )

            # 前月の送料を取得
            previous_shipping_fee = None
            previous_month = (
                f"{year:04d}/{month-1:02d}" if month > 1 else f"{year-1:04d}/12"
            )
            previous_history = product.price_histories.filter(
                effective_year_month=previous_month, is_active=True
            ).first()
            if previous_history and previous_history.shipping_fee:
                previous_shipping_fee = previous_history.shipping_fee

            form_data = {
                "product_code": product.product_code,
                "livestock_type": product.livestock_type,
                "category": product.category,
                "manufacturer": product.manufacturer,
                "product_name": product.product_name,
                "model_number": product.model_number,
                "specification": product.specification,
                "shipping_unit": product.shipping_unit,
                "remarks": product.remarks,
                f"new_effective_year_month_1": f"{year:04d}/{month:02d}",
                f"new_wholesale_price_1": str(new_price),
                f"new_revision_reason_1": final_reason,
            }

            if retail_price_str and retail_price_str.strip():
                form_data[f"new_retail_price_1"] = retail_price_str.strip()
            if kenren_price_str and kenren_price_str.strip():
                form_data[f"new_kenren_price_1"] = kenren_price_str.strip()
            if gross_margin_str and gross_margin_str.strip():
                form_data[f"new_gross_margin_1"] = gross_margin_str.strip()

            if shipping_fee_str and shipping_fee_str.strip():
                form_data[f"new_shipping_fee_1"] = shipping_fee_str.strip()
            elif previous_shipping_fee:
                form_data[f"new_shipping_fee_1"] = str(previous_shipping_fee)

            from django.http import QueryDict

            mock_post = QueryDict("", mutable=True)
            mock_post.update(form_data)

            class MockRequest:
                def __init__(self, post_data):
                    self.POST = post_data
                    self.method = "POST"
                    self.path = "/ai-extract/"
                    self.META = {}
                    self.user = request.user

            mock_request = MockRequest(mock_post)

            from dashboard.products_master.product_detail.product_detail_views import (
                submit_approval_core,
            )

            try:
                product_approval = submit_approval_core(mock_request, product.pk)
                current_user = get_current_user()
                product_approval.applicant = current_user
                product_approval.save()
                product_approval.price_histories.update(applicant=current_user)

            except Exception as submit_error:
                detail.status = "エラー"
                detail.error_message = f"申請処理エラー: {str(submit_error)}"
                detail.save()
                continue

            detail.extracted_price = new_price_str
            detail.extracted_retail_price = (
                retail_price_str if retail_price_str else None
            )
            # detail.extracted_kenren_price = (
            #     kenren_price_str if kenren_price_str else None
            # )
            # detail.extracted_shipping_fee = (
            #     shipping_fee_str if shipping_fee_str else None
            # )
            # detail.extracted_gross_margin = (
            #     gross_margin_str if gross_margin_str else None
            # )
            detail.matched_product = product
            detail.selected_candidate_text = (
                f"{detail.match_score or 0}% - {product.product_name}"
            )
            detail.status = "申請済"
            if product_approval:
                detail.created_approval = product_approval
            detail.save()

            created_count += 1

        transaction.success_count = created_count
        transaction.skip_count = skipped_count
        transaction.save()

        all_details = transaction.details.all()
        if all_details.exists() and all(
            detail.status in ["スキップ", "申請済"] for detail in all_details
        ):
            transaction.soft_delete()

        if created_count > 0:
            messages.success(
                request, f"{created_count}件の価格履歴申請を作成しました。"
            )
        if skipped_count > 0:
            messages.info(request, f"{skipped_count}件をスキップしました。")

        return redirect(request.path)

    except Exception as e:
        messages.error(request, f"申請データ作成中にエラーが発生しました: {str(e)}")
        return redirect(request.path)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_rematch(request):
    """AI抽出結果の再照合API（結果をDBに保存）"""
    try:
        data = json.loads(request.body)
        transaction_pk = data.get("transaction_pk")
        sequence = data.get("sequence")
        extracted_data = data.get("extracted_data")

        if not transaction_pk or not sequence or not extracted_data:
            return JsonResponse({"error": "パラメータが不正です"}, status=400)

        for key, value in extracted_data.items():
            if value == "" or value is None:
                extracted_data[key] = None

        json_data = {"products": [extracted_data]}
        results = process_extraction_results(json_data)

        if results and "results" in results and len(results["results"]) > 0:
            result = results["results"][0]
            candidates = result.get("candidates", [])

            try:
                detail = AIExtractTransactionDetail.objects.get(
                    transaction__pk=transaction_pk, sequence=int(sequence)
                )

                if candidates:
                    best_candidate = candidates[0]
                    matched_product_id = best_candidate.get("product", {}).get("pk")
                    if matched_product_id:
                        try:
                            matched_product = Product.objects.get(pk=matched_product_id)
                            detail.matched_product = matched_product
                            detail.match_score = best_candidate.get("score", 0)
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
                    detail.matched_product = None
                    detail.match_score = None
                    detail.selected_candidate_text = None

                detail.save()

            except AIExtractTransactionDetail.DoesNotExist:
                return JsonResponse({"error": "照合結果が見つかりません"}, status=404)

            today = datetime.now().strftime("%Y/%m")

            for candidate in candidates:
                product_pk = candidate.get("product", {}).get("pk")
                if product_pk:
                    try:
                        product = Product.objects.get(pk=product_pk)
                        # 1. PriceHistory（価格履歴テーブル）から最新レコードを取得
                        current_price_history = (
                            product.price_histories.filter(
                                effective_year_month__lte=today, is_active=True
                            )
                            .order_by("-effective_year_month")
                            .first()
                        )

                        # 2. ProductGrossMarginRate（粗利率マスタ）から取得
                        gross_margin_obj = ProductGrossMarginRate.objects.filter(
                            product=product
                        ).first()

                        # --- 既存の仕切価格 ---
                        candidate["product"]["current_wholesale_price"] = (
                            current_price_history.wholesale_price
                            if current_price_history
                            else "-"
                        )

                        # --- 🆕 追加：県連価格、送料、粗利率 ---
                        candidate["product"]["current_kenren_price"] = (
                            current_price_history.kenren_price
                            if (
                                current_price_history
                                and current_price_history.kenren_price
                            )
                            else "-"
                        )
                        candidate["product"]["current_shipping_fee"] = (
                            current_price_history.shipping_fee
                            if (
                                current_price_history
                                and current_price_history.shipping_fee
                            )
                            else "-"
                        )

                        # 20270714 コード書き換えコメントアウト
                        # candidate["product"]["current_gross_margin_rate"] = (
                        #     gross_margin_obj.gross_margin_rate
                        #     if gross_margin_obj
                        #     else "-"
                        # )
                        # 20270714 コード書き換えコメントアウト終わり

                        # 20270714 🆕 ここから書き換え：小数第1位に丸める
                        if (
                            gross_margin_obj
                            and gross_margin_obj.gross_margin_rate is not None
                        ):
                            try:
                                candidate["product"][
                                    "current_gross_margin_rate"
                                ] = f"{float(gross_margin_obj.gross_margin_rate):.1f}"
                            except:
                                candidate["product"]["current_gross_margin_rate"] = str(
                                    gross_margin_obj.gross_margin_rate
                                )
                        else:
                            candidate["product"]["current_gross_margin_rate"] = "-"
                        # 20270714 🆕 ここまで書き換え

                        if candidate["product"].get("manufacturer"):
                            candidate["product"]["manufacturer"] = str(
                                candidate["product"]["manufacturer"]
                            )

                    except Product.DoesNotExist:
                        candidate["product"]["current_wholesale_price"] = "-"
                        candidate["product"]["current_kenren_price"] = "-"
                        candidate["product"]["current_shipping_fee"] = "-"
                        candidate["product"]["current_gross_margin_rate"] = "-"

            return JsonResponse({"success": True, "result": result})
        else:
            try:
                detail = AIExtractTransactionDetail.objects.get(
                    transaction__pk=transaction_pk, sequence=int(sequence)
                )
                detail.matched_product = None
                detail.match_score = None
                detail.selected_candidate_text = None
                detail.save()
            except AIExtractTransactionDetail.DoesNotExist:
                pass

            return JsonResponse(
                {
                    "success": True,
                    "result": {
                        "status": "no_match",
                        "message": "照合結果が取得できませんでした",
                    },
                }
            )

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSONデータが不正です"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"処理エラー: {str(e)}"}, status=500)


def setup_proxy_from_config():
    """プロキシ設定をconfig.iniから読み込み環境変数に設定"""
    import configparser
    from digital_pricelist_system.config_paths import CONFIG_PATH

    if CONFIG_PATH.exists():
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_PATH, encoding="utf-8")
            http_proxy = config.get("PROXY", "http_proxy", fallback="")
            https_proxy = config.get("PROXY", "https_proxy", fallback="")
            proxy_auth = config.get("PROXY", "proxy_auth", fallback="")

            if http_proxy:
                clean_proxy = http_proxy.replace("http://", "").replace("https://", "")
                if proxy_auth:
                    os.environ["HTTP_PROXY"] = f"http://{proxy_auth}@{clean_proxy}"
                else:
                    os.environ["HTTP_PROXY"] = f"http://{clean_proxy}"

            if https_proxy and "HTTP_PROXY" in os.environ:
                clean_proxy = https_proxy.replace("http://", "").replace("https://", "")
                if proxy_auth:
                    os.environ["HTTPS_PROXY"] = f"http://{proxy_auth}@{clean_proxy}"
                else:
                    os.environ["HTTPS_PROXY"] = f"http://{clean_proxy}"
        except Exception:
            pass


def ai_extract_pdf_process(request):
    """PDFアップロード・AI抽出処理"""
    setup_proxy_from_config()

    if request.method != "POST":
        messages.error(request, "POSTメソッドが必要です。")
        return redirect("products_master:ai_extract")

    pdf_form = PDFUploadForm(request.POST, request.FILES)
    if not pdf_form.is_valid():
        messages.error(request, f"フォームにエラーがあります: {pdf_form.errors}")
        return render(
            request,
            "products_master/ai_extract_input.html",
            {
                "current_user": get_current_user(),
                "breadcrumbs": get_breadcrumbs("ai_extract"),
                "pdf_form": pdf_form,
            },
        )

    try:
        pdf_file = pdf_form.cleaned_data["pdf_file"]
        transaction_name = (
            pdf_form.cleaned_data["transaction_name"]
            or f'PDF抽出_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            for chunk in pdf_file.chunks():
                temp_file.write(chunk)
            temp_pdf_path = temp_file.name

        try:
            temp_dir = tempfile.gettempdir()
            di_result_path = os.path.join(temp_dir, f"di_result_{os.getpid()}.pkl")
            ai_result_path = os.path.join(temp_dir, f"ai_results_{os.getpid()}.json")

            extract_di_main(temp_pdf_path, di_result_path)
            ai_results = process_ai_main(di_result_path, ai_result_path)

            for path in [di_result_path, ai_result_path]:
                if os.path.exists(path):
                    os.unlink(path)

        except Exception as e:
            if "getaddrinfo failed" in str(e) or "Failed to resolve" in str(e):
                messages.error(
                    request,
                    "ネットワークエラー: Azure Document Intelligenceサービスに接続できません。",
                )
                return redirect("products_master:ai_extract")
            else:
                raise e

        if ai_results is None:
            messages.error(request, "PDF処理が失敗しました。")
            return redirect("products_master:ai_extract")

        entities = ai_results.get("products", [])
        if not entities:
            messages.warning(request, "PDFから商品情報を抽出できませんでした。")
            return redirect("products_master:ai_extract")

        document_metadata = ai_results.get("document_metadata", {})
        manufacturer_name = document_metadata.get("sender", "")

        json_data = {
            "document_metadata": document_metadata,
            "products": [
                {
                    "product_name": entity.get("name"),
                    "new_price": entity.get("price"),
                    "retail_price": entity.get("retail_price"),
                    "kenren_price": entity.get("kenren_price"),
                    "shipping_fee": entity.get("shipping_fee"),
                    "gross_margin": entity.get("gross_margin"),
                    "model_number": entity.get("model"),
                    "manufacturer": manufacturer_name if manufacturer_name else None,
                    "specification": entity.get("spec"),
                }
                for entity in entities
            ],
        }

    finally:
        if os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)

    transaction_id = (
        f"PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    )
    sender = document_metadata.get("sender", "")
    reason = document_metadata.get("reason", "PDFからのAI抽出")

    match_transaction = AIExtractTransaction.objects.create(
        transaction_id=transaction_id,
        executor=get_current_user(),
        effective_year_month="",
        revision_reason=reason,
        remarks=f"{transaction_name} (送信元: {sender})",
        uploaded_pdf=pdf_file,
        total_products=len(entities),
        status="照合中",
    )

    results = process_extraction_results(json_data)

    for i, result in enumerate(results.get("results", [])):
        extracted_data = result.get("extracted_data", {})
        candidates = result.get("candidates", [])

        matched_product = None
        match_score = None
        if candidates:
            best_candidate = candidates[0]
            matched_product_id = best_candidate.get("product", {}).get("pk")
            if matched_product_id:
                try:
                    matched_product = Product.objects.get(pk=matched_product_id)
                    match_score = best_candidate.get("score", 0)
                except Product.DoesNotExist:
                    pass

        AIExtractTransactionDetail.objects.create(
            transaction=match_transaction,
            sequence=i + 1,
            extracted_product_name=extracted_data.get("product_name"),
            extracted_model_number=extracted_data.get("model_number"),
            extracted_manufacturer=extracted_data.get("manufacturer"),
            extracted_specification=extracted_data.get("specification"),
            extracted_price=str(extracted_data.get("new_price", "")),
            extracted_retail_price=(
                str(extracted_data.get("retail_price", ""))
                if extracted_data.get("retail_price")
                else None
            ),
            # extracted_kenren_price=(
            #     str(extracted_data.get("kenren_price", ""))
            #     if extracted_data.get("kenren_price")
            #     else None
            # ),
            # extracted_shipping_fee=(
            #     str(extracted_data.get("shipping_fee", ""))
            #     if extracted_data.get("shipping_fee")
            #     else None
            # ),
            # extracted_gross_margin=(
            #     str(extracted_data.get("gross_margin", ""))
            #     if extracted_data.get("gross_margin")
            #     else None
            # ),
            extracted_revision_reason="",
            matched_product=matched_product,
            match_score=match_score,
            status="未処理",
        )

    messages.success(request, f"PDFから{len(entities)}件の商品情報を抽出しました。")
    return redirect(
        "products_master:ai_extract_history_detail", pk=match_transaction.pk
    )


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_pdf_api(request):
    """PDFアップロードAPI（Ajax用）"""
    return JsonResponse({"error": "Deprecated"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_get_detail(request):
    """明細データを取得"""
    try:
        data = json.loads(request.body)
        detail = AIExtractTransactionDetail.objects.get(
            transaction__pk=data.get("transaction_pk"),
            sequence=int(data.get("sequence")),
        )
        return JsonResponse(
            {
                "extracted_product_name": detail.extracted_product_name or "",
                "extracted_model_number": detail.extracted_model_number or "",
                "extracted_specification": detail.extracted_specification or "",
                "extracted_manufacturer": detail.extracted_manufacturer or "",
                "extracted_price": detail.extracted_price or "",
                "extracted_revision_reason": detail.extracted_revision_reason or "",
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _get_dynamic_breadcrumbs_for_ai_extract(request):
    referer = request.META.get("HTTP_REFERER", "")
    if "integrated-pricelist" in referer:
        return get_breadcrumbs(
            "ai_extract",
            from_page_title="デジタル価格表",
            from_page_url="/products/integrated-pricelist/",
        )
    return get_breadcrumbs("ai_extract")


def ai_extract_search_products(request):
    """商品検索API（モーダル用）"""
    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()

        from django.db.models import Q

        products_query = Product.objects.select_related(
            "manufacturer", "category", "livestock_type"
        )

        # 絞り込み条件（既存ロジック）
        if data.get("category_id"):
            products_query = products_query.filter(category_id=data.get("category_id"))
        if data.get("livestock_type_id"):
            products_query = products_query.filter(
                livestock_type_id=data.get("livestock_type_id")
            )
        if data.get("manufacturer_id"):
            products_query = products_query.filter(
                manufacturer_id=data.get("manufacturer_id")
            )

        if query:
            products_query = products_query.filter(
                Q(product_name__icontains=query)
                | Q(model_number__icontains=query)
                | Q(specification__icontains=query)
            )

        products = products_query[:50]
        today = datetime.now().strftime("%Y/%m")

        result = []
        for product in products:
            # 1. 価格履歴テーブル（products_master_pricehistory）から最新レコードを取得
            current_price_history = (
                product.price_histories.filter(
                    effective_year_month__lte=today, is_active=True
                )
                .order_by("-effective_year_month")
                .first()
            )

            # 2. 粗利率テーブル（products_master_productgrossmarginrate）から該当商品のレコードを取得
            gross_margin_obj = ProductGrossMarginRate.objects.filter(
                product=product
            ).first()
            gross_margin_rate = (
                gross_margin_obj.gross_margin_rate if gross_margin_obj else "-"
            )

            # 辞書に指定のカラムデータをセット
            result.append(
                {
                    "pk": product.pk,
                    "product_name": product.product_name,
                    "model_number": product.model_number or "-",
                    "specification": product.specification or "-",
                    "manufacturer": (
                        str(product.manufacturer) if product.manufacturer else "-"
                    ),
                    "category_name": product.category.name if product.category else "-",
                    "shipping_unit": product.shipping_unit or "-",
                    "remarks": product.remarks or "-",
                    # 価格履歴テーブルから取得する項目
                    "current_wholesale_price": (
                        current_price_history.wholesale_price
                        if current_price_history
                        else "-"
                    ),
                    "kenren_price": (
                        current_price_history.kenren_price
                        if (
                            current_price_history and current_price_history.kenren_price
                        )
                        else "-"
                    ),
                    "shipping_fee": (
                        current_price_history.shipping_fee
                        if (
                            current_price_history and current_price_history.shipping_fee
                        )
                        else "-"
                    ),
                    # 粗利率テーブルから取得する項目
                    "gross_margin_rate": gross_margin_rate,
                    "display_info": f"{product.product_name} | {product.model_number or '-'} | {product.specification or '-'}",
                }
            )
        return JsonResponse({"products": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def ai_extract_get_masters(request):
    """マスタデータ取得API"""
    try:
        from dashboard.products_master.models import (
            Category,
            LivestockType,
            Manufacturer,
        )

        return JsonResponse(
            {
                "categories": [
                    {"id": c.id, "name": c.name}
                    for c in Category.objects.all().order_by("name")
                ],
                "livestock_types": [
                    {"id": l.id, "name": l.name}
                    for l in LivestockType.objects.all().order_by("name")
                ],
                "manufacturers": [
                    {"id": m.id, "name": m.name}
                    for m in Manufacturer.objects.all().order_by("name")
                ],
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ai_extract_update_detail(request):
    """AI抽出履歴の明細データを更新"""
    try:
        data = json.loads(request.body)
        transaction_pk = data.get("transaction_pk")
        sequence = data.get("sequence")

        if not transaction_pk:
            return JsonResponse({"error": "トランザクションIDが必要です"}, status=400)

        detail = AIExtractTransactionDetail.objects.get(
            transaction__pk=transaction_pk, sequence=int(sequence)
        )

        if "updates" in data:
            for update in data.get("updates", []):
                field = update.get("field")
                value = update.get("value")

                if field == "extracted_price":
                    detail.extracted_price = str(value) if value else ""
                elif field == "extracted_retail_price":
                    detail.extracted_retail_price = str(value) if value else None
                # elif field == "extracted_kenren_price":
                #     detail.extracted_kenren_price = str(value) if value else None
                # elif field == "extracted_shipping_fee":
                #     detail.extracted_shipping_fee = str(value) if value else None
                # elif field == "extracted_gross_margin":
                #     detail.extracted_gross_margin = str(value) if value else None
                elif field == "extracted_revision_reason":
                    detail.extracted_revision_reason = str(value) if value else ""
                elif field == "extracted_product_name":
                    detail.extracted_product_name = str(value) if value else ""
                elif field == "extracted_model_number":
                    detail.extracted_model_number = str(value) if value else ""
                elif field == "extracted_specification":
                    detail.extracted_specification = str(value) if value else ""
                elif field == "extracted_manufacturer":
                    detail.extracted_manufacturer = str(value) if value else ""
                elif field == "matched_product":
                    if value:
                        try:
                            product = Product.objects.get(pk=value)
                            detail.matched_product = product
                            detail.selected_candidate_text = (
                                f"{detail.match_score or 0}% - {product.product_name}"
                            )
                        except Product.DoesNotExist:
                            detail.matched_product = None
                            detail.selected_candidate_text = "スキップ"
                    else:
                        detail.matched_product = None
                        detail.selected_candidate_text = "スキップ"
            detail.save()
        else:
            field = data.get("field")
            value = data.get("value")
            if field == "extracted_price":
                detail.extracted_price = str(value) if value else ""
            elif field == "extracted_retail_price":
                detail.extracted_retail_price = str(value) if value else None
            # elif field == "extracted_kenren_price":
            #     detail.extracted_kenren_price = str(value) if value else None
            # elif field == "extracted_shipping_fee":
            #     detail.extracted_shipping_fee = str(value) if value else None
            # elif field == "extracted_gross_margin":
            #     detail.extracted_gross_margin = str(value) if value else None
            elif field == "extracted_revision_reason":
                detail.extracted_revision_reason = str(value) if value else ""
            elif field == "extracted_product_name":
                detail.extracted_product_name = str(value) if value else ""
            elif field == "extracted_model_number":
                detail.extracted_model_number = str(value) if value else ""
            elif field == "extracted_specification":
                detail.extracted_specification = str(value) if value else ""
            elif field == "extracted_manufacturer":
                detail.extracted_manufacturer = str(value) if value else ""
            elif field == "matched_product":
                if value:
                    try:
                        product = Product.objects.get(pk=value)
                        detail.matched_product = product
                        detail.selected_candidate_text = (
                            f"{detail.match_score or 0}% - {product.product_name}"
                        )
                    except Product.DoesNotExist:
                        pass
                else:
                    detail.matched_product = None
                    detail.selected_candidate_text = "スキップ"
            detail.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
