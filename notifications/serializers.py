# notifications/serializers.py
from rest_framework import serializers
from notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = [
            'created_at', 'sent_email', 'sent_sms', 'sent_push',
            'is_read', 'read_at'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


class MarkAsReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    mark_all = serializers.BooleanField(default=False)


class QuietHoursSerializer(serializers.Serializer):
    """Serializer for setting quiet hours"""
    start = serializers.TimeField(required=False, allow_null=True)
    end = serializers.TimeField(required=False, allow_null=True)
    
    def validate(self, data):
        start = data.get('start')
        end = data.get('end')
        
        # If one is provided, both should be provided
        if (start and not end) or (end and not start):
            raise serializers.ValidationError(
                "Both start and end times must be provided together"
            )
        
        # If both are provided, validate
        if start and end:
            if start >= end:
                raise serializers.ValidationError(
                    "Start time must be before end time"
                )
        
        return data
