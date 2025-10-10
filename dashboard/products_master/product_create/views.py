from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from dashboard.products_master.models import Product, PriceHistory
from dashboard.products_master.forms import ProductForm
from digital_pricelist_system.utils import get_current_user

def product_create(request):
    """商品新規作成画面"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    messages.success(request, f'商品「{product.product_name}」を作成しました。')
                    return redirect('products_master:product_detail', pk=product.pk)
            except Exception as e:
                messages.error(request, f'商品の作成に失敗しました: {str(e)}')
    else:
        form = ProductForm()
    
    context = {
        'current_user': get_current_user(),
        'form': form,
        'page_title': '新規商品登録',
        'page_subtitle': '新しい商品を登録します',
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': '新規作成', 'url': None}
        ]
    }
    return render(request, 'products_master/product_form.html', context)

def product_edit(request, pk):
    """商品編集"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                updated_product = form.save()
                messages.success(request, f'商品「{updated_product.product_name}」を更新しました。')
                return redirect('products_master:product_detail', pk=updated_product.pk)
            except Exception as e:
                messages.error(request, f'更新に失敗しました: {str(e)}')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'current_user': get_current_user(),
        'form': form,
        'product': product,
        'page_title': f'{product.product_name} - 編集',
        'page_subtitle': '商品情報を編集します',
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': f'{product.product_name}', 'url': f'/products/products/{pk}/'},
            {'title': '編集', 'url': None}
        ]
    }
    return render(request, 'products_master/product_form.html', context)

def product_copy(request, pk):
    """商品コピー（新規採番で作成）"""
    original_product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    new_product = form.save()
                    # 元の価格履歴をコピー
                    for history in original_product.price_histories.all():
                        PriceHistory.objects.create(
                            product=new_product,
                            period_year=history.period_year,
                            effective_year_month=history.effective_year_month,
                            end_year_month=history.end_year_month,
                            gross_margin_rate=history.gross_margin_rate,
                            wholesale_price=history.wholesale_price,
                            kenren_price=history.kenren_price,
                            retail_price=history.retail_price,
                            revision_amount=history.revision_amount,
                            revision_reason=history.revision_reason
                        )
                    messages.success(request, f'商品「{new_product.product_name}」を作成しました。')
                    return redirect('products_master:product_detail', pk=new_product.pk)
            except Exception as e:
                messages.error(request, f'コピーに失敗しました: {str(e)}')
    else:
        # 元の商品情報をコピーしてフォームに設定
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
    
    context = {
        'current_user': get_current_user(),
        'form': form,
        'original_product': original_product,
        'page_title': f'{original_product.product_name} - コピー作成',
        'page_subtitle': '新しい商品番号でコピーします',
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': f'{original_product.product_name}', 'url': f'/products/products/{pk}/'},
            {'title': 'コピー', 'url': None}
        ]
    }
    return render(request, 'products_master/product_form.html', context)

def product_delete(request, pk):
    """商品論理削除"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            product.soft_delete()
            messages.success(request, f'商品「{product.product_name}」を削除しました。')
            return redirect('products_master:product_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': '/products/'},
            {'title': '商品一覧', 'url': '/products/products/'},
            {'title': f'{product.product_name}', 'url': f'/products/products/{pk}/'},
            {'title': '削除確認', 'url': None}
        ]
    }
    return render(request, 'products_master/product_delete.html', context)