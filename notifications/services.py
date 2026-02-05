# notifications/services.py
import logging
from django.conf import settings
from django.utils import timezone
from notifications.models import Notification, NotificationPreference
from users.models import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through multiple channels"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.sms_service = SMSService()
        self.push_service = PushNotificationService()
    
    def send_notification(self, user, notification_type, title, message, **kwargs):
        """Send notification through appropriate channels based on user preferences"""
        try:
            # Get or create notification preferences
            preferences, created = NotificationPreference.objects.get_or_create(
                user=user,
                defaults=self.get_default_preferences()
            )
            
            # Check quiet hours
            if self.is_quiet_hours(preferences):
                logger.info(f"Quiet hours for user {user.id}, notification delayed")
                return False
            
            # Create notification record
            notification = Notification.objects.create(
                user=user,
                type=notification_type,
                title=title,
                message=message,
                action_url=kwargs.get('action_url'),
                action_text=kwargs.get('action_text'),
                data=kwargs.get('data', {}),
                entity_type=kwargs.get('entity_type'),
                entity_id=kwargs.get('entity_id')
            )
            
            # Send via email if enabled
            if self.should_send_email(preferences, notification_type):
                self.send_email_notification(user, notification, preferences)
            
            # Send via SMS if enabled
            if self.should_send_sms(preferences, notification_type):
                self.send_sms_notification(user, notification, preferences)
            
            # Send push notification if enabled
            if self.should_send_push(preferences, notification_type):
                self.send_push_notification(user, notification, preferences)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False
    
    def get_default_preferences(self):
        """Get default notification preferences"""
        return {
            'email_notifications': True,
            'email_payments': True,
            'email_contracts': True,
            'email_messages': True,
            'sms_notifications': True,
            'sms_payments': True,
            'sms_contracts': True,
            'push_notifications': True,
            'push_payments': True,
            'push_contracts': True,
            'push_messages': True,
        }
    
    def is_quiet_hours(self, preferences):
        """Check if current time is within quiet hours"""
        if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False
        
        current_time = timezone.now().time()
        return preferences.quiet_hours_start <= current_time <= preferences.quiet_hours_end
    
    def should_send_email(self, preferences, notification_type):
        """Check if email should be sent for this notification type"""
        if not preferences.email_notifications:
            return False
        
        type_map = {
            'payment': 'email_payments',
            'contract': 'email_contracts',
            'message': 'email_messages',
            'application': 'email_applications',
            'review': 'email_reviews',
            'verification': 'email_verifications',
            'security': 'email_security',
        }
        
        setting_name = type_map.get(notification_type, 'email_notifications')
        return getattr(preferences, setting_name, True)
    
    def should_send_sms(self, preferences, notification_type):
        """Check if SMS should be sent for this notification type"""
        if not preferences.sms_notifications:
            return False
        
        type_map = {
            'payment': 'sms_payments',
            'contract': 'sms_contracts',
            'verification': 'sms_verifications',
            'security': 'sms_security',
        }
        
        setting_name = type_map.get(notification_type, 'sms_notifications')
        return getattr(preferences, setting_name, True)
    
    def should_send_push(self, preferences, notification_type):
        """Check if push notification should be sent for this notification type"""
        if not preferences.push_notifications:
            return False
        
        type_map = {
            'payment': 'push_payments',
            'contract': 'push_contracts',
            'message': 'push_messages',
            'application': 'push_applications',
            'review': 'push_reviews',
        }
        
        setting_name = type_map.get(notification_type, 'push_notifications')
        return getattr(preferences, setting_name, True)
    
    def send_email_notification(self, user, notification, preferences):
        """Send email notification"""
        try:
            self.email_service.send(
                to_email=user.email,
                subject=notification.title,
                template_name=f"notifications/{notification.type}.html",
                context={
                    'user': user,
                    'notification': notification,
                    'site_name': 'WorkConnect Uganda'
                }
            )
            notification.sent_email = True
            notification.save()
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
    
    def send_sms_notification(self, user, notification, preferences):
        """Send SMS notification"""
        try:
            # Truncate message for SMS
            sms_message = notification.message[:160]
            
            self.sms_service.send(
                phone_number=user.phone,
                message=sms_message
            )
            notification.sent_sms = True
            notification.save()
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
    
    def send_push_notification(self, user, notification, preferences):
        """Send push notification"""
        try:
            # Get user's device tokens
            from users.models import DeviceToken
            device_tokens = DeviceToken.objects.filter(user=user, is_active=True)
            
            for device_token in device_tokens:
                self.push_service.send(
                    device_token=device_token.token,
                    title=notification.title,
                    message=notification.message,
                    data={
                        'notification_id': str(notification.id),
                        'action_url': notification.action_url or '',
                        'type': notification.type
                    }
                )
            
            notification.sent_push = True
            notification.save()
            
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
    
    def send_message_notification(self, receiver, sender, message_preview):
        """Send notification for new message"""
        title = f"New message from {sender.first_name} {sender.last_name}"
        message = f"{message_preview}..."
        
        self.send_notification(
            user=receiver,
            notification_type='message',
            title=title,
            message=message,
            action_url=f"/messages/{sender.id}",
            action_text="View Message"
        )
    
    def send_payment_notification(self, user, payment_type, amount, status):
        """Send payment notification"""
        title = f"Payment {status}"
        message = f"Your {payment_type} of UGX {amount:,} has been {status}"
        
        self.send_notification(
            user=user,
            notification_type='payment',
            title=title,
            message=message,
            action_url="/payments/history",
            action_text="View Payment"
        )
    
    def send_contract_notification(self, user, contract, action):
        """Send contract notification"""
        title = f"Contract {action}"
        message = f"Contract {contract.job_title} has been {action}"
        
        self.send_notification(
            user=user,
            notification_type='contract',
            title=title,
            message=message,
            action_url=f"/contracts/{contract.id}",
            action_text="View Contract"
        )