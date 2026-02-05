# notifications/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from notifications.models import Notification, NotificationPreference
from notifications.serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    MarkAsReadSerializer, QuietHoursSerializer
)
from notifications.services import NotificationService
from users.permissions import IsAdmin


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['admin', 'super_admin']:
            return Notification.objects.all()
        
        return Notification.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
        
        # Count by type
        count_by_type = {}
        for notification_type, _ in Notification.Type.choices:
            count = unread_notifications.filter(type=notification_type).count()
            if count > 0:
                count_by_type[notification_type] = count
        
        serializer = self.get_serializer(unread_notifications, many=True)
        
        return Response({
            "total_unread": unread_notifications.count(),
            "count_by_type": count_by_type,
            "notifications": serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """Mark notifications as read"""
        serializer = MarkAsReadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if data.get('mark_all'):
            # Mark all notifications as read
            updated_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            
            return Response({
                "status": "all_marked_read",
                "updated_count": updated_count
            })
        
        else:
            # Mark specific notifications as read
            notification_ids = data.get('notification_ids', [])
            
            if not notification_ids:
                return Response(
                    {"error": "No notification IDs provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_count = 0
            for notification_id in notification_ids:
                try:
                    notification = Notification.objects.get(
                        id=notification_id,
                        user=request.user
                    )
                    if not notification.is_read:
                        notification.is_read = True
                        notification.read_at = timezone.now()
                        notification.save()
                        updated_count += 1
                except Notification.DoesNotExist:
                    continue
            
            return Response({
                "status": "marked_read",
                "updated_count": updated_count
            })
    
    @action(detail=True, methods=['post'])
    def mark_single_read(self, request, pk=None):
        """Mark a single notification as read"""
        notification = self.get_object()
        
        # Check permission
        if notification.user != request.user and request.user.role not in ['admin', 'super_admin']:
            return Response(
                {"error": "You don't have permission to mark this notification as read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        
        return Response({
            "status": "marked_read",
            "notification_id": str(notification.id)
        })
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Clear all notifications for the user"""
        deleted_count, _ = Notification.objects.filter(user=request.user).delete()
        
        return Response({
            "status": "cleared",
            "deleted_count": deleted_count
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for notification preferences"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['admin', 'super_admin']:
            return NotificationPreference.objects.all()
        
        return NotificationPreference.objects.filter(user=user)
    
    def get_object(self):
        # Get or create preferences for the user
        user = self.request.user
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults=self.get_default_preferences()
        )
        return preferences
    
    def get_default_preferences(self):
        """Get default notification preferences"""
        return {
            'email_notifications': True,
            'email_payments': True,
            'email_contracts': True,
            'email_messages': True,
            'email_applications': True,
            'email_reviews': True,
            'email_verifications': True,
            'email_security': True,
            'email_promotions': False,
            'sms_notifications': True,
            'sms_payments': True,
            'sms_contracts': True,
            'sms_verifications': True,
            'sms_security': True,
            'push_notifications': True,
            'push_payments': True,
            'push_contracts': True,
            'push_messages': True,
            'push_applications': True,
            'push_reviews': True,
        }
    
    @action(detail=False, methods=['get', 'put'])
    def quiet_hours(self, request):
        """Get or set quiet hours"""
        preferences = self.get_object()
        
        if request.method == 'GET':
            return Response({
                "quiet_hours_start": preferences.quiet_hours_start,
                "quiet_hours_end": preferences.quiet_hours_end
            })
        
        elif request.method == 'PUT':
            serializer = QuietHoursSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            
            preferences.quiet_hours_start = data.get('start')
            preferences.quiet_hours_end = data.get('end')
            preferences.save()
            
            return Response({
                "status": "updated",
                "quiet_hours_start": preferences.quiet_hours_start,
                "quiet_hours_end": preferences.quiet_hours_end
            })
    
    @action(detail=False, methods=['post'])
    def test_notification(self, request):
        """Send a test notification"""
        notification_type = request.data.get('type', 'system')
        channel = request.data.get('channel', 'all')  # all, email, sms, push
        
        notification_service = NotificationService()
        
        # Send test notification
        success = notification_service.send_notification(
            user=request.user,
            notification_type=notification_type,
            title="Test Notification",
            message="This is a test notification from WorkConnect Uganda",
            data={"test": True, "timestamp": timezone.now().isoformat()}
        )
        
        if success:
            return Response({
                "status": "sent",
                "message": "Test notification sent successfully"
            })
        else:
            return Response(
                {"error": "Failed to send test notification"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
