from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'system_admin'

# 互換性のためのリダイレクト関数
def redirect_export_csv(request):
    return redirect('system_admin:export_csv')

def redirect_import_csv(request):
    return redirect('system_admin:import_csv')

def redirect_clear_data(request):
    return redirect('system_admin:clear_data')

urlpatterns = [
    path('export/', views.export_csv, name='export_csv'),
    path('import/', views.import_csv, name='import_csv'),
    path('clear/', views.clear_data, name='clear_data'),
    path('status-reset/', views.status_reset, name='status_reset'),
    path('regenerate-keywords/', views.regenerate_keywords_batch, name='regenerate_keywords_batch'),
    # 古いURL形式との互換性
    path('export_csv/', redirect_export_csv),
    path('import_csv/', redirect_import_csv),
    path('clear_data/', redirect_clear_data),
]