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
    path('new/', detail_views.product_detail_new, name='product_new'),
    path('products/create/', create_views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', create_views.product_edit, name='product_edit'),
    path('products/<int:pk>/copy/', create_views.product_copy, name='product_copy'),
    path('products/<int:pk>/delete/', create_views.product_delete, name='product_delete'),
    path('products/<int:product_pk>/price-history/create/', detail_views.price_history_create, name='price_history_create'),
    path('products/<int:pk>/add-row/', detail_views.add_price_row, name='add_price_row'),
    path('new/add-row/', detail_views.add_price_row, name='add_price_row_new'),
    path('calc-kenren-price/<int:pk>/', detail_views.calc_kenren_price, name='calc_kenren_price'),
    path('products/<int:pk>/preview-save/', detail_views.preview_save, name='preview_save'),
    path('new/preview-save/', detail_views.preview_save, name='preview_save_new'),
    path('products/<int:pk>/submit-approval/', detail_views.submit_approval, name='submit_approval'),
    path('new/submit-approval/', detail_views.submit_approval, name='submit_approval_new'),
    
    # 承認ワークフロー
    path('approvals/', detail_views.approval_list, name='approval_list'),
    path('approvals/<int:pk>/', detail_views.approval_detail, name='approval_detail'),
    path('approvals/<int:pk>/approve/', detail_views.approve_application, name='approve_application'),
    path('approvals/<int:pk>/reject/', detail_views.reject_application, name='reject_application'),
    path('approvals/bulk-approve/', detail_views.bulk_approve, name='bulk_approve'),

    path('price-history/<int:pk>/update/', detail_views.price_history_update, name='price_history_update'),
    path('price-history/<int:pk>/delete/', detail_views.price_history_delete, name='price_history_delete'),
    path('integrated-pricelist/', pricelist_views.integrated_pricelist, name='integrated_pricelist'),
]