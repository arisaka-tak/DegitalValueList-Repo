from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from dashboard.products_master.models import Product
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs


def product_delete(request, pk):
    """商品削除申請"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            from dashboard.products_master.models import ProductApproval, PriceHistoryApproval
            
            # 既に申請中かチェック
            if product.status:
                messages.error(request, 'この商品は既に申請中です')
                return redirect('products_master:product_list')
            
            # トランザクション内で処理を実行
            with transaction.atomic():
                # 申請テーブルに削除申請を作成
                approval_product = ProductApproval.objects.create(
                    product_number=product.pk,
                    product_code=product.product_code,
                    livestock_type=product.livestock_type,
                    category=product.category,
                    manufacturer=product.manufacturer,
                    product_name=product.product_name,
                    model_number=product.model_number,
                    specification=product.specification,
                    shipping_unit=product.shipping_unit,
                    shipping_fee=product.shipping_fee,
                    remarks=product.remarks,
                    status='削除申請',
                    applicant=get_current_user()
                )
                
                # 既存の価格履歴も申請テーブルにコピー（削除申請フラグ付き）
                for history in product.price_histories.filter(is_active=True):
                    PriceHistoryApproval.objects.create(
                        product=approval_product,
                        period_year=history.period_year,
                        effective_year_month=history.effective_year_month,
                        gross_margin_rate=history.gross_margin_rate,
                        wholesale_price=history.wholesale_price,
                        kenren_price=history.kenren_price,
                        retail_price=history.retail_price,
                        revision_amount=history.revision_amount,
                        revision_reason=history.revision_reason,
                        is_delete_request=True,
                        applicant=get_current_user()
                    )
                
                # 全ての処理が成功した場合のみステータスを変更
                product.status = '削除申請'
                product.save()
            
            messages.success(request, f'商品「{product.product_name}」の削除申請を受け付けました。')
            return redirect('products_master:product_list')
        except Exception as e:
            messages.error(request, f'削除申請中にエラーが発生しました: {str(e)}')
            return redirect('products_master:product_list')
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'breadcrumbs': get_breadcrumbs('product_delete', product_name=product.product_name)
    }
    return render(request, 'products_master/product_delete.html', context)