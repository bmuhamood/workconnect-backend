# messaging/models.py
import uuid
from django.db import models
from django.utils import timezone
from users.models import User


class Conversation(models.Model):
    """Model for conversations between users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant_1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_as_participant_1'
    )
    participant_2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_as_participant_2'
    )
    
    # Contract reference (if conversation is about a contract)
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    
    # Metadata
    is_archived_1 = models.BooleanField(default=False)
    is_archived_2 = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    blocked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_conversations'
    )
    
    last_message_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_message_at']
        unique_together = ['participant_1', 'participant_2']
        indexes = [
            models.Index(fields=['participant_1', 'last_message_at']),
            models.Index(fields=['participant_2', 'last_message_at']),
        ]
    
    def __str__(self):
        return f"Conversation: {self.participant_1.email} & {self.participant_2.email}"
    
    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        if user == self.participant_1:
            return self.participant_2
        return self.participant_1
    
    def get_unread_count(self, user):
        """Get unread message count for a user"""
        return self.messages.filter(
            sender=self.get_other_participant(user),
            is_read=False
        ).count()


class Message(models.Model):
    """Model for individual messages"""
    
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    
    # Message content
    message_text = models.TextField()
    attachment_url = models.URLField(blank=True, null=True)
    attachment_type = models.CharField(max_length=50, blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Message type
    is_system_message = models.BooleanField(default=False)
    system_message_type = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['receiver', 'created_at']),
            models.Index(fields=['is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.email} at {self.created_at}"
    
    def save(self, *args, **kwargs):
        # Update conversation's last message timestamp
        if not self.pk:  # Only for new messages
            self.conversation.last_message_at = timezone.now()
            self.conversation.save()
        
        super().save(*args, **kwargs)
        
        # Send notification for new messages
        if not self.is_system_message:
            self.send_notification()
    
    def send_notification(self):
        """Send push notification for new message"""
        from notifications.services import NotificationService
        
        notification_service = NotificationService()
        notification_service.send_message_notification(
            receiver=self.receiver,
            sender=self.sender,
            message_preview=self.message_text[:100]
        )
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.status = Message.Status.READ
            self.save()
