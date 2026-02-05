from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from users.models import User, EmployerProfile, WorkerProfile
from users.tasks import send_welcome_email

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create profile when user is created
    REMOVED - Now handled in serializers
    """
    if created:
        # Only send welcome email
        try:
            send_welcome_email.delay(str(instance.id))
        except Exception as e:
            logger.error(f"Failed to queue welcome email for user {instance.id}: {str(e)}")

@receiver(pre_save, sender=User)
def update_user_verification(sender, instance, **kwargs):
    """Update is_verified status when email and phone are verified"""
    if instance.email_verified and instance.phone_verified:
        instance.is_verified = True
        if instance.status == User.Status.PENDING_VERIFICATION:
            instance.status = User.Status.ACTIVE


@receiver(post_save, sender=WorkerProfile)

def create_initial_verification(sender, instance, created, **kwargs):
    """Create initial verification record for new workers"""
    if created:
        from users.models import Verification
        Verification.objects.create(
            worker=instance,
            verification_type=Verification.VerificationType.IDENTITY,
            status='pending'  # Changed from Verification.Status.PENDING
        )
