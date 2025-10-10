from django.shortcuts import render
from digital_pricelist_system.utils import get_current_user

def index(request):
    """商品マスタ管理メイン画面"""
    context = {
        'current_user': get_current_user(),
        'breadcrumbs': [
            {'title': '商品マスタ管理', 'url': None}
        ]
    }
    return render(request, 'products_master/index.html', context)