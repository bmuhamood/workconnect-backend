# analytics/admin.py
from django.contrib import admin
from analytics.models import PlatformMetric, UserActivityLog


@admin.register(PlatformMetric)
class PlatformMetricAdmin(admin.ModelAdmin):
    list_display = ('metric_date', 'total_revenue', 'total_users', 'active_contracts', 'new_registrations')
    list_filter = ('metric_date',)
    search_fields = ()
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Date', {
            'fields': ('metric_date',)
        }),
        ('User Metrics', {
            'fields': ('total_users', 'active_employers', 'active_workers',
                      'new_registrations', 'new_employers', 'new_workers')
        }),
        ('Contract Metrics', {
            'fields': ('active_contracts', 'new_contracts', 'completed_contracts')
        }),
        ('Financial Metrics', {
            'fields': ('total_revenue', 'service_fees_collected', 'worker_salaries_disbursed')
        }),
        ('Engagement Metrics', {
            'fields': ('total_job_postings', 'total_applications', 'total_messages')
        }),
        ('Conversion Metrics', {
            'fields': ('application_to_hire_rate', 'trial_success_rate')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_metrics']
    
    def recalculate_metrics(self, request, queryset):
        """Recalculate metrics for selected dates"""
        for metric in queryset:
            new_metric = PlatformMetric.calculate_daily_metrics(metric.metric_date)
        
        self.message_user(request, f"{queryset.count()} metrics recalculated.")
    recalculate_metrics.short_description = "Recalculate selected metrics"


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'entity_type', 'created_at')
    list_filter = ('action_type', 'entity_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('User', {
            'fields': ('user', 'action_type')
        }),
        ('Entity', {
            'fields': ('entity_type', 'entity_id')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent', 'location'),
            'classes': ('collapse',)
        }),
        ('Data', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Date', {
            'fields': ('created_at',)
        }),
    )
