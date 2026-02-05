from django.contrib import admin
from .models import Contract, ContractReplacement, ContractDocument


class ContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_title', 'employer', 'worker', 'status', 'start_date', 
                   'trial_end_date', 'worker_salary_amount', 'service_fee_amount')
    list_filter = ('status', 'contract_type', 'is_trial', 'start_date')
    search_fields = ('job_title', 'employer__user__email', 'worker__user__email', 
                    'employer__first_name', 'worker__first_name')
    readonly_fields = ('created_at', 'updated_at', 'activated_at', 'completed_at')
    raw_id_fields = ('employer', 'worker', 'category', 'created_by')
    
    fieldsets = (
        ('Contract Details', {
            'fields': ('employer', 'worker', 'category', 'job_title', 'job_description')
        }),
        ('Financial Terms', {
            'fields': ('worker_salary_amount', 'service_fee_amount', 'total_monthly_cost', 
                      'payment_frequency')
        }),
        ('Dates', {
            'fields': ('start_date', 'trial_end_date', 'end_date', 'trial_duration_days')
        }),
        ('Work Details', {
            'fields': ('contract_type', 'work_location', 'work_hours_per_week', 'work_schedule')
        }),
        ('Trial Period', {
            'fields': ('is_trial', 'trial_passed', 'trial_feedback')
        }),
        ('Status', {
            'fields': ('status', 'signed_by_employer', 'signed_by_worker', 
                      'employer_signature_date', 'worker_signature_date')
        }),
        ('Documents', {
            'fields': ('contract_document_url',)
        }),
        ('Termination', {
            'fields': ('termination_reason', 'termination_initiated_by')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'activated_at', 'completed_at')
        }),
    )


class ContractReplacementAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_contract', 'original_worker', 'replacement_worker', 
                   'status', 'is_free_replacement', 'replacement_fee', 'requested_at')
    list_filter = ('status', 'is_free_replacement')
    search_fields = ('original_contract__job_title', 'original_worker__first_name', 
                    'replacement_worker__first_name')
    raw_id_fields = ('original_contract', 'original_worker', 'replacement_worker', 
                    'new_contract', 'requested_by')
    
    readonly_fields = ('requested_at', 'completed_at')


class ContractDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'contract', 'document_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('document_type',)
    search_fields = ('document_name', 'contract__job_title')
    raw_id_fields = ('contract', 'uploaded_by')
    readonly_fields = ('uploaded_at',)


admin.site.register(Contract, ContractAdmin)
admin.site.register(ContractReplacement, ContractReplacementAdmin)
admin.site.register(ContractDocument, ContractDocumentAdmin)
