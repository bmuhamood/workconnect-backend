# job_postings/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from job_postings.models import JobApplication
from notifications.tasks import send_application_notification


@receiver(post_save, sender=JobApplication)
def handle_application_status_change(sender, instance, created, **kwargs):
    """Handle job application status changes"""
    if not created:
        try:
            old_instance = JobApplication.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Notify worker about status change
                send_application_notification.delay(
                    application_id=str(instance.id),
                    status=instance.status,
                    employer_id=str(instance.job_posting.employer.user.id) if instance.job_posting.employer else None
                )
        except JobApplication.DoesNotExist:
            pass
    
    elif created:
        # New application created
        # Notify employer
        from notifications.tasks import send_notification_task
        send_notification_task.delay(
            user_id=str(instance.job_posting.employer.user.id),
            notification_type='application',
            title='New Job Application',
            message=f'{instance.worker.full_name} applied for "{instance.job_posting.title}"',
            action_url=f'/applications/{instance.id}',
            action_text='View Application',
            data={
                'application_id': str(instance.id),
                'worker_id': str(instance.worker.id),
                'job_posting_id': str(instance.job_posting.id)
            }
        )
        
        # Notify worker
        send_application_notification.delay(
            application_id=str(instance.id),
            status='submitted',
            employer_id=None
        )