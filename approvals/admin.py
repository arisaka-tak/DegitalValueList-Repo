from django.contrib import admin
from .models import ChangeRequest, ApprovalHistory

@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'request_type', 'status', 'requester', 'target_product', 'requested_at', 'ai_extracted']
    list_filter = ['request_type', 'status', 'ai_extracted', 'requested_at']
    search_fields = ['requester', 'target_product__product_name']
    ordering = ['-requested_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('target_product')

@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ['change_request', 'approver', 'action', 'processed_at']
    list_filter = ['action', 'processed_at']
    search_fields = ['change_request__id', 'approver']
    ordering = ['-processed_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('change_request')