from django.urls import path
from .index import views as index_views
from .product_list import views as list_views
from .product_detail import views as detail_views
from .product_create import views as create_views
from .integrated_pricelist import views as pricelist_views

app_name = 'products_master'

urlpatterns = [
    path('', index_views.index, name='index'),
    path('products/', list_views.product_list, name='product_list'),
    path('products/<int:pk>/', detail_views.product_detail, name='product_detail'),
    path('products/create/', create_views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', create_views.product_edit, name='product_edit'),
    path('products/<int:pk>/copy/', create_views.product_copy, name='product_copy'),
    path('products/<int:pk>/delete/', create_views.product_delete, name='product_delete'),
    path('products/<int:product_pk>/price-history/create/', detail_views.price_history_create, name='price_history_create'),
    path('price-history/<int:pk>/update/', detail_views.price_history_update, name='price_history_update'),
    path('price-history/<int:pk>/delete/', detail_views.price_history_delete, name='price_history_delete'),
    path('integrated-pricelist/', pricelist_views.integrated_pricelist, name='integrated_pricelist'),
]