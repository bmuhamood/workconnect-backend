# messaging/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from messaging.models import Message
from notifications.tasks import send_message_notification


@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    """Handle new messages"""
    if created and not instance.is_system_message:
        # Send notification for new message
        send_message_notification.delay(
            sender_id=str(instance.sender.id),
            receiver_id=str(instance.receiver.id),
            message_preview=instance.message_text[:100]
        )