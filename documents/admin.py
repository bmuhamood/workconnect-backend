# documents/admin.py
from django.contrib import admin
from documents.models import (
    WorkerDocument, DocumentVerificationRequest, DocumentTypeConfig
)


@admin.register(WorkerDocument)
class WorkerDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'worker', 'document_type', 'status', 'verified_by',
        'uploaded_at', 'expiry_date', 'is_expiring_soon'
    )
    list_filter = ('document_type', 'status', 'uploaded_at', 'expiry_date')
    search_fields = (
        'worker__first_name', 'worker__last_name', 
        'document_number', 'issuing_authority'
    )
    readonly_fields = (
        'uploaded_at', 'updated_at', 'verified_at',
        'ai_ocr_result', 'ai_confidence_score', 'ai_extracted_data'
    )
    fieldsets = (
        ('Document Information', {
            'fields': ('worker', 'document_type', 'document_file')
        }),
        ('Document Details', {
            'fields': ('document_number', 'issue_date', 'expiry_date', 'issuing_authority')
        }),
        ('Verification Status', {
            'fields': ('status', 'verified_by', 'verification_notes')
        }),
        ('AI Processing', {
            'fields': ('ai_ocr_result', 'ai_confidence_score', 'ai_extracted_data'),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('uploaded_by', 'uploaded_at', 'updated_at', 'verified_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_selected', 'reject_selected', 'mark_expired']
    
    def is_expiring_soon(self, obj):
        return obj.is_expiring_soon()
    is_expiring_soon.boolean = True
    is_expiring_soon.short_description = 'Expiring Soon'
    
    def verify_selected(self, request, queryset):
        """Admin action to verify selected documents"""
        updated = queryset.update(
            status=WorkerDocument.Status.VERIFIED,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f"{updated} documents verified.")
    verify_selected.short_description = "Verify selected documents"
    
    def reject_selected(self, request, queryset):
        """Admin action to reject selected documents"""
        updated = queryset.update(
            status=WorkerDocument.Status.REJECTED,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f"{updated} documents rejected.")
    reject_selected.short_description = "Reject selected documents"
    
    def mark_expired(self, request, queryset):
        """Admin action to mark selected documents as expired"""
        updated = queryset.update(status=WorkerDocument.Status.EXPIRED)
        self.message_user(request, f"{updated} documents marked as expired.")
    mark_expired.short_description = "Mark as expired"


@admin.register(DocumentVerificationRequest)
class DocumentVerificationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'status', 'ai_service_used',
        'requested_at', 'completed_at', 'confidence_score'
    )
    list_filter = ('status', 'ai_service_used', 'requested_at')
    search_fields = ('document__worker__first_name', 'document__worker__last_name')
    readonly_fields = (
        'requested_at', 'processed_at', 'completed_at',
        'ai_response', 'verification_result', 'error_message'
    )
    fieldsets = (
        ('Request Information', {
            'fields': ('document', 'ai_service_used', 'ai_request_id')
        }),
        ('Status', {
            'fields': ('status', 'confidence_score')
        }),
        ('Results', {
            'fields': ('ai_response', 'verification_result', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'processed_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentTypeConfig)
class DocumentTypeConfigAdmin(admin.ModelAdmin):
    list_display = (
        'document_type', 'display_name', 'is_required',
        'use_ai_verification', 'display_order'
    )
    list_filter = ('is_required', 'use_ai_verification')
    search_fields = ('document_type', 'display_name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('document_type', 'display_name', 'description', 'help_text')
        }),
        ('Requirements', {
            'fields': ('is_required', 'requires_expiry_date', 
                      'requires_document_number', 'requires_issuing_authority')
        }),
        ('File Validation', {
            'fields': ('allowed_file_types', 'max_file_size_mb')
        }),
        ('AI Settings', {
            'fields': ('use_ai_verification', 'ai_service')
        }),
        ('Display', {
            'fields': ('display_order',)
        }),
    )