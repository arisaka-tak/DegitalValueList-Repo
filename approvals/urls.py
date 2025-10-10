from django.urls import path
from . import views

app_name = 'approvals'

urlpatterns = [
    path('', views.index, name='index'),
    path('requests/', views.request_list, name='request_list'),
    path('pending/', views.pending_list, name='pending_list'),
]