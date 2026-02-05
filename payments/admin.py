from django.contrib import admin
from .models import (
    PayrollCycle, EmployerInvoice, WorkerPayment,
    ServiceFeeTransaction, WorkerPaymentMethod,
    ServiceFeeConfig, PaymentTransaction
)


class PayrollCycleAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'total_contracts', 'total_worker_salaries',
                   'total_service_fees', 'invoices_generated', 'payments_processed',
                   'cycle_closed', 'created_at')
    list_filter = ('year', 'month', 'cycle_closed')
    search_fields = ('month', 'year')
    readonly_fields = ('created_at', 'invoice_generation_date', 'payment_processing_date', 'closed_at')
    
    fieldsets = (
        ('Cycle Information', {
            'fields': ('month', 'year')
        }),
        ('Statistics', {
            'fields': ('total_contracts', 'total_worker_salaries', 'total_service_fees', 'total_revenue')
        }),
        ('Status Flags', {
            'fields': ('invoices_generated', 'payments_processed', 'cycle_closed')
        }),
        ('Dates', {
            'fields': ('invoice_generation_date', 'payment_processing_date', 'closed_at', 'created_at')
        }),
    )


class EmployerInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'employer', 'contract', 'status', 'total_amount',
                   'due_date', 'paid_date', 'created_at')
    list_filter = ('status', 'due_date', 'payroll_cycle')
    search_fields = ('invoice_number', 'employer__user__email', 'employer__first_name',
                    'employer__last_name', 'transaction_reference')
    readonly_fields = ('created_at', 'updated_at', 'paid_date')
    raw_id_fields = ('payroll_cycle', 'contract', 'employer')
    
    fieldsets = (
        ('Invoice Details', {
            'fields': ('invoice_number', 'payroll_cycle', 'contract', 'employer')
        }),
        ('Amounts', {
            'fields': ('worker_salary_amount', 'service_fee_amount', 'additional_fees', 'total_amount')
        }),
        ('Payment Details', {
            'fields': ('status', 'due_date', 'paid_date', 'payment_method', 'transaction_reference')
        }),
        ('Document', {
            'fields': ('invoice_pdf_url',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class WorkerPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_reference', 'worker', 'contract', 'status', 'net_amount',
                   'payment_method', 'scheduled_date', 'disbursement_date')
    list_filter = ('status', 'payment_method', 'scheduled_date')
    search_fields = ('payment_reference', 'worker__first_name', 'worker__last_name',
                    'transaction_id', 'account_number')
    readonly_fields = ('created_at', 'updated_at', 'disbursement_date')
    raw_id_fields = ('payroll_cycle', 'contract', 'worker', 'invoice')
    
    fieldsets = (
        ('Payment Details', {
            'fields': ('payment_reference', 'payroll_cycle', 'contract', 'worker', 'invoice')
        }),
        ('Amounts', {
            'fields': ('salary_amount', 'deductions', 'net_amount')
        }),
        ('Payment Method', {
            'fields': ('payment_method', 'payment_provider', 'account_number', 'account_name')
        }),
        ('Status', {
            'fields': ('status', 'transaction_id', 'transaction_receipt_url')
        }),
        ('Documents', {
            'fields': ('payslip_pdf_url',)
        }),
        ('Dates', {
            'fields': ('scheduled_date', 'disbursement_date', 'created_at', 'updated_at')
        }),
        ('Error Handling', {
            'fields': ('failure_reason', 'retry_count')
        }),
    )


class ServiceFeeTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'amount', 'transaction_date')
    list_filter = ('transaction_date',)
    search_fields = ('invoice__invoice_number', 'notes')
    raw_id_fields = ('invoice', 'payroll_cycle')
    readonly_fields = ('transaction_date',)


class WorkerPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('worker', 'method_type', 'account_number', 'is_default', 'is_verified')
    list_filter = ('method_type', 'is_default', 'is_verified')
    search_fields = ('worker__first_name', 'worker__last_name', 'account_number', 'account_name')
    raw_id_fields = ('worker',)
    readonly_fields = ('verified_at', 'created_at', 'updated_at')


class ServiceFeeConfigAdmin(admin.ModelAdmin):
    list_display = ('category', 'fee_type', 'is_active', 'effective_from', 'created_at')
    list_filter = ('fee_type', 'is_active', 'effective_from')
    search_fields = ('category__name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'fee_type', 'is_active', 'effective_from')
        }),
        ('Fixed Amount Configuration', {
            'fields': ('fixed_amount',),
            'classes': ('collapse',)
        }),
        ('Percentage Configuration', {
            'fields': ('percentage',),
            'classes': ('collapse',)
        }),
        ('Tiered Configuration', {
            'fields': ('tier_config',),
            'classes': ('collapse',)
        }),
        ('Limits', {
            'fields': ('minimum_fee', 'maximum_fee')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('external_reference', 'transaction_type', 'amount', 'status',
                   'payment_method', 'initiated_at', 'completed_at')
    list_filter = ('transaction_type', 'status', 'payment_method', 'initiated_at')
    search_fields = ('external_reference', 'internal_reference', 'transaction_id',
                    'payer_user__email', 'payee_user__email')
    readonly_fields = ('initiated_at', 'completed_at')
    raw_id_fields = ('payer_user', 'payee_user', 'invoice', 'worker_payment')
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_type', 'external_reference', 'internal_reference')
        }),
        ('Amount', {
            'fields': ('amount', 'currency')
        }),
        ('Payment Method', {
            'fields': ('payment_method', 'payment_provider')
        }),
        ('Status', {
            'fields': ('status', 'provider_status', 'provider_response')
        }),
        ('Users', {
            'fields': ('payer_user', 'payee_user')
        }),
        ('Related Entities', {
            'fields': ('invoice', 'worker_payment')
        }),
        ('Timestamps', {
            'fields': ('initiated_at', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent')
        }),
    )


admin.site.register(PayrollCycle, PayrollCycleAdmin)
admin.site.register(EmployerInvoice, EmployerInvoiceAdmin)
admin.site.register(WorkerPayment, WorkerPaymentAdmin)
admin.site.register(ServiceFeeTransaction, ServiceFeeTransactionAdmin)
admin.site.register(WorkerPaymentMethod, WorkerPaymentMethodAdmin)
admin.site.register(ServiceFeeConfig, ServiceFeeConfigAdmin)
admin.site.register(PaymentTransaction, PaymentTransactionAdmin)
