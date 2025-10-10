from django.shortcuts import render
from digital_pricelist_system.utils import get_current_user

def dashboard(request):
    """ダッシュボード画面"""
    context = {
        'current_user': get_current_user(),
    }
    return render(request, 'dashboard.html', context)