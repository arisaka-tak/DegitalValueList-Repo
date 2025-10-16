from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from dashboard.products_master.models import Product, PriceHistory
from dashboard.products_master.forms import ProductForm
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

def product_create(request):
    """商品新規作成画面"""
    if request.method == 'POST':
        # POSTリクエストは申請処理を通す
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('products_master:product_new')
        return HttpResponseRedirect(url)
    else:
        form = ProductForm()
    
    context = {
        'current_user': get_current_user(),
        'form': form,
        'action_type': 'create',  # 統合テンプレート用パラメータ
        'page_title': '新規商品登録',
        'page_subtitle': '新しい商品を登録します',
        'breadcrumbs': get_breadcrumbs('product_new')
    }
    # 旧: return render(request, 'products_master/product_form.html', context)
    return render(request, 'products_master/product_action.html', context)

def product_edit(request, pk):
    """商品編集"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # POSTリクエストは申請処理を通す
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('products_master:product_detail', args=[pk])
        return HttpResponseRedirect(url)
    else:
        form = ProductForm(instance=product)
    
    context = {
        'current_user': get_current_user(),
        'form': form,
        'product': product,
        'action_type': 'edit',  # 統合テンプレート用パラメータ
        'page_title': f'{product.product_name} - 編集',
        'page_subtitle': '商品情報を編集します',
        'breadcrumbs': get_breadcrumbs('product_edit', 
                                      product_name=product.product_name,
                                      product_url=f'/products/products/{pk}/')
    }
    # 旧: return render(request, 'products_master/product_form.html', context)
    return render(request, 'products_master/product_action.html', context)

def product_copy(request, pk):
    """商品コピー（基本情報をコピーして新規作成モードで詳細画面へ）"""
    original_product = get_object_or_404(Product, pk=pk)
    
    # コピーモードで詳細画面にリダイレクト（copy_fromパラメータ付き）
    from django.urls import reverse
    from django.http import HttpResponseRedirect
    url = reverse('products_master:product_new') + f'?copy_from={pk}'
    return HttpResponseRedirect(url)

def product_delete(request, pk):
    """商品削除申請"""
    from dashboard.products_master.models import ProductApproval
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            # 削除申請を作成
            ProductApproval.objects.create(
                product_number=product.product_number,
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
                applicant=get_current_user(),
                status='削除申請'
            )
            
            # 商品マスタのステータスを更新
            product.status = '削除申請中'
            product.approver = ''
            product.save()
            
            messages.success(request, f'商品「{product.product_name}」の削除申請を行いました。')
            return redirect('products_master:product_list')
        except Exception as e:
            messages.error(request, f'削除申請に失敗しました: {str(e)}')
    
    context = {
        'current_user': get_current_user(),
        'product': product,
        'breadcrumbs': get_breadcrumbs('product_delete',
                                      product_name=product.product_name,
                                      product_url=f'/products/products/{pk}/')
    }
    return render(request, 'products_master/product_delete.html', context)

def product_new(request):
    """新規商品作成フォーム"""
    copy_from_id = request.GET.get('copy_from')
    
    if request.method == 'POST':
        # POSTリクエストはproduct_detail_newに任せる
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        url = reverse('products_master:product_new')
        return HttpResponseRedirect(url)
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
        'action_type': 'create',  # 統合テンプレート用パラメータ
        'page_title': '新規商品登録',
        'page_subtitle': '新しい商品を登録します',
        'breadcrumbs': get_breadcrumbs('product_new')
    }
    # 旧: return render(request, 'products_master/product_detail.html', context)
    return render(request, 'products_master/product_action.html', context)