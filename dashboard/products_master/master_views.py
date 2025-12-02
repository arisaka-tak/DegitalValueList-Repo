from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from dashboard.products_master.models import LivestockType, Category, Manufacturer
from digital_pricelist_system.utils import get_current_user
from digital_pricelist_system.breadcrumbs import get_breadcrumbs

def livestock_type_list(request):
    """畜種マスタ一覧"""
    livestock_types = LivestockType.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    context = {
        'current_user': get_current_user(),
        'livestock_types': livestock_types,
        'breadcrumbs': get_breadcrumbs('livestock_type_list')
    }
    return render(request, 'products_master/livestock_type_list.html', context)

def livestock_type_create(request):
    """畜種マスタ新規作成"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        
        if not name:
            messages.error(request, '畜種名は必須です')
        elif LivestockType.objects.filter(name=name).exists():
            messages.error(request, 'この畜種名は既に存在します')
        else:
            LivestockType.objects.create(
                name=name,
                sort_order=int(sort_order) if sort_order else 0
            )
            messages.success(request, '畜種を作成しました')
            return redirect('products_master:livestock_type_list')
    
    return render(request, 'products_master/livestock_type_form.html', {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('livestock_type_create')
    })

def livestock_type_edit(request, pk):
    """畜種マスタ編集"""
    livestock_type = get_object_or_404(LivestockType, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        
        if not name:
            messages.error(request, '畜種名は必須です')
        elif LivestockType.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'この畜種名は既に存在します')
        else:
            livestock_type.name = name
            livestock_type.sort_order = int(sort_order) if sort_order else 0
            livestock_type.save()
            messages.success(request, '畜種を更新しました')
            return redirect('products_master:livestock_type_list')
    
    context = {
        'current_user': get_current_user(),
        'livestock_type': livestock_type,
        'breadcrumbs': get_breadcrumbs('livestock_type_edit', livestock_type_name=livestock_type.name)
    }
    return render(request, 'products_master/livestock_type_form.html', context)

def livestock_type_delete(request, pk):
    """畜種マスタ削除"""
    if request.method == 'POST':
        livestock_type = get_object_or_404(LivestockType, pk=pk)
        livestock_type.is_active = False
        livestock_type.save()
        messages.success(request, '畜種を削除しました')
    return redirect('products_master:livestock_type_list')

def category_list(request):
    """分類マスタ一覧"""
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    context = {
        'current_user': get_current_user(),
        'categories': categories,
        'breadcrumbs': get_breadcrumbs('category_list')
    }
    return render(request, 'products_master/category_list.html', context)

def category_create(request):
    """分類マスタ新規作成"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        
        if not name:
            messages.error(request, '分類名は必須です')
        elif Category.objects.filter(name=name).exists():
            messages.error(request, 'この分類名は既に存在します')
        else:
            Category.objects.create(
                name=name,
                sort_order=int(sort_order) if sort_order else 0
            )
            messages.success(request, '分類を作成しました')
            return redirect('products_master:category_list')
    
    return render(request, 'products_master/category_form.html', {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('category_create')
    })

def category_edit(request, pk):
    """分類マスタ編集"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        
        if not name:
            messages.error(request, '分類名は必須です')
        elif Category.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'この分類名は既に存在します')
        else:
            category.name = name
            category.sort_order = int(sort_order) if sort_order else 0
            category.save()
            messages.success(request, '分類を更新しました')
            return redirect('products_master:category_list')
    
    context = {
        'current_user': get_current_user(),
        'category': category,
        'breadcrumbs': get_breadcrumbs('category_edit', category_name=category.name)
    }
    return render(request, 'products_master/category_form.html', context)

def category_delete(request, pk):
    """分類マスタ削除"""
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=pk)
        category.is_active = False
        category.save()
        messages.success(request, '分類を削除しました')
    return redirect('products_master:category_list')

def manufacturer_list(request):
    """メーカーマスタ一覧"""
    search_query = request.GET.get('search', '')
    manufacturers = Manufacturer.objects.filter(is_active=True)
    
    if search_query:
        manufacturers = manufacturers.filter(name__icontains=search_query)
    
    manufacturers = manufacturers.order_by('name')
    
    context = {
        'current_user': get_current_user(),
        'manufacturers': manufacturers,
        'search_query': search_query,
        'breadcrumbs': get_breadcrumbs('manufacturer_list')
    }
    return render(request, 'products_master/manufacturer_list.html', context)

def manufacturer_create(request):
    """メーカーマスタ新規作成"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, 'メーカー名は必須です')
        elif Manufacturer.objects.filter(name=name).exists():
            messages.error(request, 'このメーカー名は既に存在します')
        else:
            Manufacturer.objects.create(name=name)
            messages.success(request, 'メーカーを作成しました')
            return redirect('products_master:manufacturer_list')
    
    return render(request, 'products_master/manufacturer_form.html', {
        'current_user': get_current_user(),
        'breadcrumbs': get_breadcrumbs('manufacturer_create')
    })

def manufacturer_edit(request, pk):
    """メーカーマスタ編集"""
    manufacturer = get_object_or_404(Manufacturer, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, 'メーカー名は必須です')
        elif Manufacturer.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'このメーカー名は既に存在します')
        else:
            manufacturer.name = name
            manufacturer.save()
            messages.success(request, 'メーカーを更新しました')
            return redirect('products_master:manufacturer_list')
    
    context = {
        'current_user': get_current_user(),
        'manufacturer': manufacturer,
        'breadcrumbs': get_breadcrumbs('manufacturer_edit', manufacturer_name=manufacturer.name)
    }
    return render(request, 'products_master/manufacturer_form.html', context)

def manufacturer_delete(request, pk):
    """メーカーマスタ削除"""
    if request.method == 'POST':
        manufacturer = get_object_or_404(Manufacturer, pk=pk)
        manufacturer.is_active = False
        manufacturer.save()
        messages.success(request, 'メーカーを削除しました')
    return redirect('products_master:manufacturer_list')