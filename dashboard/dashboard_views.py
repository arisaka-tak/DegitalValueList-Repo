from django.shortcuts import render
from digital_pricelist_system.utils import get_current_user, is_admin_user

def dashboard(request):
    """ダッシュボード画面"""
    context = {
        'current_user': get_current_user(),
        'is_admin': is_admin_user(),
    }
    return render(request, 'dashboard.html', context)

def sidebar(request):
    """サイドバー表示"""
    context = {
        'current_user': get_current_user(),
        'is_admin': is_admin_user(),
    }
    return render(request, 'sidebar.html', context)