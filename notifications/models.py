# notifications/models.py
import uuid
from django.db import models
from django.utils import timezone
from users.models import User


class Notification(models.Model):
    """Model for system notifications"""
    
    class Type(models.TextChoices):
        SYSTEM = 'system', 'System'
        PAYMENT = 'payment', 'Payment'
        CONTRACT = 'contract', 'Contract'
        MESSAGE = 'message', 'Message'
        APPLICATION = 'application', 'Application'
        REVIEW = 'review', 'Review'
        VERIFICATION = 'verification', 'Verification'
        SECURITY = 'security', 'Security'
        REMINDER = 'reminder', 'Reminder'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification details
    type = models.CharField(max_length=20, choices=Type.choices)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Action and data
    action_url = models.URLField(blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)
    
    # Related entity (optional)
    entity_type = models.CharField(max_length=50, blank=True, null=True)
    entity_id = models.UUIDField(null=True, blank=True)
    
    # Delivery status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery channels
    sent_email = models.BooleanField(default=False)
    sent_sms = models.BooleanField(default=False)
    sent_push = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.type} notification for {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(models.Model):
    """Model for user notification preferences"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email preferences
    email_notifications = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    email_contracts = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_applications = models.BooleanField(default=True)
    email_reviews = models.BooleanField(default=True)
    email_verifications = models.BooleanField(default=True)
    email_security = models.BooleanField(default=True)
    email_promotions = models.BooleanField(default=False)
    
    # SMS preferences
    sms_notifications = models.BooleanField(default=True)
    sms_payments = models.BooleanField(default=True)
    sms_contracts = models.BooleanField(default=True)
    sms_verifications = models.BooleanField(default=True)
    sms_security = models.BooleanField(default=True)
    
    # Push notification preferences
    push_notifications = models.BooleanField(default=True)
    push_payments = models.BooleanField(default=True)
    push_contracts = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_applications = models.BooleanField(default=True)
    push_reviews = models.BooleanField(default=True)
    
    # Quiet hours (24-hour format)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"
