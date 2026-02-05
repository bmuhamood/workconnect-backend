# payments/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
import logging

from users.models import User, EmployerProfile, WorkerProfile, Verification
from users.tasks import send_welcome_email

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    REMOVED PROFILE CREATION - Now handled in serializers
    Only sends welcome email when user is created.
    """
    if created:
        # Send welcome email (async)
        try:
            send_welcome_email.delay(str(instance.id))
        except Exception as e:
            logger.error(f"Failed to queue welcome email for user {instance.id}: {str(e)}")


@receiver(post_save, sender=User)
def update_user_profile_on_name_change(sender, instance, **kwargs):
    """
    Update profile names when user names are changed.
    """
    try:
        if instance.role == User.Role.EMPLOYER:
            # Use try-except to handle case where profile might not exist
            try:
                profile = instance.employer_profile
                if profile.first_name != instance.first_name or profile.last_name != instance.last_name:
                    profile.first_name = instance.first_name
                    profile.last_name = instance.last_name
                    profile.save(update_fields=['first_name', 'last_name'])
            except EmployerProfile.DoesNotExist:
                logger.warning(f"No EmployerProfile found for user {instance.id} when updating names")
        
        elif instance.role == User.Role.WORKER:
            # Use try-except to handle case where profile might not exist
            try:
                profile = instance.worker_profile
                if profile.first_name != instance.first_name or profile.last_name != instance.last_name:
                    profile.first_name = instance.first_name
                    profile.last_name = instance.last_name
                    profile.save(update_fields=['first_name', 'last_name'])
            except WorkerProfile.DoesNotExist:
                logger.warning(f"No WorkerProfile found for user {instance.id} when updating names")
    
    except Exception as e:
        logger.error(f"Error updating profile names for user {instance.id}: {str(e)}")


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
        try:
            Verification.objects.create(
                worker=instance,
                verification_type=Verification.VerificationType.IDENTITY,
                status=Verification.Status.PENDING
            )
        except Exception as e:
            logger.error(f"Error creating verification for worker {instance.id}: {str(e)}")


@receiver(post_save, sender=WorkerProfile)
def update_worker_profile_completion(sender, instance, **kwargs):
    """
    Update profile completion percentage when worker profile is updated.
    This helps track how complete the profile is.
    """
    # Avoid infinite recursion
    if kwargs.get('update_fields') is None or 'completion_percentage' not in kwargs.get('update_fields', []):
        try:
            completion_fields = [
                'national_id', 'date_of_birth', 'gender', 'city',
                'experience_years', 'education_level', 'bio'
            ]
            
            completed = 0
            for field in completion_fields:
                field_value = getattr(instance, field, None)
                # Check if field has a value (not None or empty string)
                if field_value not in [None, '']:
                    # For JSONField (languages), check if it's not empty
                    if field == 'languages':
                        if isinstance(field_value, list) and len(field_value) > 0:
                            completed += 1
                    else:
                        completed += 1
            
            completion_percentage = int((completed / len(completion_fields)) * 100)
            
            if instance.completion_percentage != completion_percentage:
                # Use update to avoid recursive signal
                WorkerProfile.objects.filter(pk=instance.pk).update(
                    completion_percentage=completion_percentage
                )
        
        except Exception as e:
            logger.error(f"Error updating completion percentage for worker {instance.id}: {str(e)}")