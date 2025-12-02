from django.urls import path
from . import views

app_name = 'system_admin'

urlpatterns = [
    path('export/', views.export_csv, name='export_csv'),
    path('import/', views.import_csv, name='import_csv'),
    path('clear/', views.clear_data, name='clear_data'),
]