# reviews/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from reviews.models import Review
from notifications.tasks import send_notification_task


@receiver(post_save, sender=Review)
def handle_new_review(sender, instance, created, **kwargs):
    """Handle new reviews"""
    if created:
        # Notify reviewee about new review
        send_notification_task.delay(
            user_id=str(instance.reviewee.id),
            notification_type='review',
            title='New Review Received',
            message=f'You received a {instance.rating} star review from {instance.reviewer.get_full_name()}',
            action_url=f'/reviews/{instance.id}',
            action_text='View Review',
            data={
                'review_id': str(instance.id),
                'rating': instance.rating,
                'reviewer_id': str(instance.reviewer.id)
            }
        )