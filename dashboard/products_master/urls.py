from django.urls import path
from .product_list import product_list_views as list_views
from .product_detail import product_detail_views as detail_views

from .integrated_pricelist import integrated_pricelist_views as pricelist_views
from .ai_price_extract import ai_price_extract_views as ai_views
from .ai_price_extract import ai_history_views as ai_history_views
from .product_delete import product_delete_views as delete_views
from . import master_views

app_name = 'products_master'

urlpatterns = [
    path('', list_views.product_list, name='product_list'),
    path('products/', list_views.product_list, name='product_list'),
    path('regenerate-keywords/', list_views.regenerate_keywords_batch, name='regenerate_keywords_batch'),
    path('products/<int:pk>/', detail_views.product_detail, name='product_detail'),
    path('new/', detail_views.product_detail_new, name='product_new'),
    path('products/<int:pk>/copy/', detail_views.product_copy, name='product_copy'),

    path('products/<int:product_pk>/price-history/create/', detail_views.price_history_create, name='price_history_create'),
    path('products/<int:pk>/add-row/', detail_views.add_price_row, name='add_price_row'),
    path('new/add-row/', detail_views.add_price_row, name='add_price_row_new'),
    path('calc-kenren-price/<int:pk>/', detail_views.calc_kenren_price, name='calc_kenren_price'),
    path('products/<int:pk>/preview-save/', detail_views.preview_save, name='preview_save'),
    path('new/preview-save/', detail_views.preview_save, name='preview_save_new'),

    
    # 承認ワークフロー
    path('approvals/', detail_views.approval_list, name='approval_list'),
    path('approvals/<int:pk>/', detail_views.approval_detail, name='approval_detail'),
    path('approvals/<int:pk>/approve/', detail_views.approve_application, name='approve_application'),
    path('approvals/<int:pk>/reject/', detail_views.reject_application, name='reject_application'),
    path('approvals/<int:pk>/cancel/', detail_views.cancel_application, name='cancel_application'),
    path('approvals/bulk-approve/', detail_views.bulk_approve, name='bulk_approve'),

    path('price-history/<int:pk>/update/', detail_views.price_history_update, name='price_history_update'),
    path('price-history/<int:pk>/delete/', detail_views.price_history_delete, name='price_history_delete'),
    path('integrated-pricelist/', pricelist_views.integrated_pricelist, name='integrated_pricelist'),
    path('integrated-pricelist/update-sort/', pricelist_views.update_sort_order, name='update_sort_order'),
    path('integrated-pricelist/reset-sort/', pricelist_views.reset_sort_order, name='reset_sort_order'),
    path('integrated-pricelist/export-excel/', pricelist_views.export_excel, name='export_excel'),
    
    # AI価格抽出
    path('ai-extract/', ai_history_views.ai_extract_history, name='ai_extract'),
    path('ai-extract/input/', ai_views.ai_extract, name='ai_extract_input'),
    path('ai-extract/process/', ai_views.ai_extract_process, name='ai_extract_process'),
    path('ai-extract/pdf-process/', ai_views.ai_extract_pdf_process, name='ai_extract_pdf_process'),
    path('ai-extract/pdf-api/', ai_views.ai_extract_pdf_api, name='ai_extract_pdf_api'),
    path('ai-extract/rematch/', ai_views.ai_extract_rematch, name='ai_extract_rematch'),
    path('ai-extract/update-detail/', ai_views.ai_extract_update_detail, name='ai_extract_update_detail'),
    path('ai-extract/history/<int:pk>/', ai_history_views.ai_extract_history_detail, name='ai_extract_history_detail'),
    path('ai-extract/history/<int:pk>/delete/', ai_history_views.ai_extract_history_delete, name='ai_extract_history_delete'),
    
    # 商品削除
    path('products/<int:pk>/delete/', delete_views.product_delete, name='product_delete'),
    
    # マスタメンテナンス
    path('masters/livestock-types/', master_views.livestock_type_list, name='livestock_type_list'),
    path('masters/livestock-types/create/', master_views.livestock_type_create, name='livestock_type_create'),
    path('masters/livestock-types/<int:pk>/edit/', master_views.livestock_type_edit, name='livestock_type_edit'),
    path('masters/livestock-types/<int:pk>/delete/', master_views.livestock_type_delete, name='livestock_type_delete'),
    path('masters/categories/', master_views.category_list, name='category_list'),
    path('masters/categories/create/', master_views.category_create, name='category_create'),
    path('masters/categories/<int:pk>/edit/', master_views.category_edit, name='category_edit'),
    path('masters/categories/<int:pk>/delete/', master_views.category_delete, name='category_delete'),
    path('masters/manufacturers/', master_views.manufacturer_list, name='manufacturer_list'),
    path('masters/manufacturers/create/', master_views.manufacturer_create, name='manufacturer_create'),
    path('masters/manufacturers/<int:pk>/edit/', master_views.manufacturer_edit, name='manufacturer_edit'),
    path('masters/manufacturers/<int:pk>/delete/', master_views.manufacturer_delete, name='manufacturer_delete'),
    
    # API
    path('api/manufacturers/', detail_views.api_manufacturers, name='api_manufacturers'),
    path('api/gross-margins/<int:pk>/', detail_views.api_gross_margins, name='api_gross_margins'),
]