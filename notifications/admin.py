# notifications/admin.py
from django.contrib import admin
from notifications.models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'priority', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at', 'read_at', 'sent_email', 'sent_sms', 'sent_push')
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'type', 'priority', 'title', 'message')
        }),
        ('Actions', {
            'fields': ('action_url', 'action_text', 'data'),
            'classes': ('collapse',)
        }),
        ('Delivery', {
            'fields': ('sent_email', 'sent_sms', 'sent_push'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'created_at')
        }),
    )
    
    actions = ['mark_as_read', 'resend_notifications']
    
    def mark_as_read(self, request, queryset):
        """Admin action to mark notifications as read"""
        updated_count = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{updated_count} notifications marked as read.")
    mark_as_read.short_description = "Mark selected as read"
    
    def resend_notifications(self, request, queryset):
        """Admin action to resend notifications"""
        from notifications.services import NotificationService
        notification_service = NotificationService()
        
        resend_count = 0
        for notification in queryset:
            # Resend notification
            success = notification_service.send_notification(
                user=notification.user,
                notification_type=notification.type,
                title=notification.title,
                message=notification.message,
                data=notification.data
            )
            if success:
                resend_count += 1
        
        self.message_user(request, f"{resend_count} notifications resent.")
    resend_notifications.short_description = "Resend selected notifications"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'sms_notifications', 'push_notifications')
    list_filter = ('email_notifications', 'sms_notifications', 'push_notifications')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Preferences', {
            'fields': ('email_notifications', 'email_payments', 'email_contracts',
                      'email_messages', 'email_applications', 'email_reviews',
                      'email_verifications', 'email_security', 'email_promotions'),
            'classes': ('collapse',)
        }),
        ('SMS Preferences', {
            'fields': ('sms_notifications', 'sms_payments', 'sms_contracts',
                      'sms_verifications', 'sms_security'),
            'classes': ('collapse',)
        }),
        ('Push Preferences', {
            'fields': ('push_notifications', 'push_payments', 'push_contracts',
                      'push_messages', 'push_applications', 'push_reviews'),
            'classes': ('collapse',)
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
