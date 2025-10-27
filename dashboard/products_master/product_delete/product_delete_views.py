from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from dashboard.products_master.models import Product
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs


def product_delete(request, pk):
    """商品削除申請"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            # 削除申請処理をここに実装
            # 実際の削除ではなく、削除申請を作成
            messages.success(request, f'商品「{product.product_name}」の削除申請を受け付けました。')
            return redirect('products_master:product_list')
        except Exception as e:
            messages.error(request, f'削除申請中にエラーが発生しました: {str(e)}')
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'breadcrumbs': get_breadcrumbs('product_delete', product_name=product.product_name)
    }
    return render(request, 'products_master/product_delete.html', context)