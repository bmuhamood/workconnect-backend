# messaging/admin.py
from django.contrib import admin
from messaging.models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('participant_1', 'participant_2', 'is_blocked', 'last_message_at', 'created_at')
    list_filter = ('is_blocked', 'created_at', 'last_message_at')
    search_fields = ('participant_1__email', 'participant_2__email')
    readonly_fields = ('last_message_at', 'created_at', 'updated_at')
    fieldsets = (
        ('Participants', {
            'fields': ('participant_1', 'participant_2', 'contract')
        }),
        ('Status', {
            'fields': ('is_archived_1', 'is_archived_2', 'is_blocked', 'blocked_by')
        }),
        ('Metadata', {
            'fields': ('last_message_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'conversation', 'is_read', 'created_at')
    list_filter = ('is_read', 'is_system_message', 'status', 'created_at')
    search_fields = ('message_text', 'sender__email', 'receiver__email')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    fieldsets = (
        ('Message Content', {
            'fields': ('conversation', 'sender', 'receiver', 'message_text')
        }),
        ('Attachments', {
            'fields': ('attachment_url', 'attachment_type', 'attachment_name'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'is_read', 'read_at', 'is_system_message', 'system_message_type')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
