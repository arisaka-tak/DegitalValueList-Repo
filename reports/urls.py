from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.index, name='index'),
    path('monthly/', views.monthly_pricelist, name='monthly_pricelist'),
    path('export/', views.export_excel, name='export_excel'),
]