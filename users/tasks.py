from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from users.models import User, WorkerProfile
from users.services.otp_service import OTPService


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user"""
    try:
        user = User.objects.get(id=user_id)
        
        subject = 'Welcome to WorkConnect Uganda'
        message = f"""
        Hello {user.first_name},
        
        Welcome to WorkConnect Uganda! We're excited to have you join our platform.
        
        Your account has been created successfully. Please verify your phone number to start using all features.
        
        If you have any questions, please contact our support team.
        
        Best regards,
        The WorkConnect Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
    except User.DoesNotExist:
        pass


@shared_task
def send_verification_reminder():
    """Send reminder to users who haven't verified their phone"""
    users = User.objects.filter(
        phone_verified=False,
        created_at__lte=timezone.now() - timedelta(hours=24)
    )
    
    for user in users:
        # Generate new OTP
        otp_service = OTPService()
        otp = otp_service.generate_otp(user.phone)
        
        # Send SMS reminder
        otp_service.send_otp_sms(user.phone, otp)


@shared_task
def update_worker_trust_scores():
    """Update trust scores for workers based on various factors"""
    workers = WorkerProfile.objects.all()
    
    for worker in workers:
        score = 0
        
        # Base score for verification
        if worker.verification_status == 'verified':
            score += 30
        
        # Score for completed contracts
        score += min(worker.total_placements * 5, 30)  # Max 30 points
        
        # Score for ratings
        if worker.rating_average >= 4.0:
            score += 20
        elif worker.rating_average >= 3.0:
            score += 10
        
        # Score for documents
        document_count = worker.documents.count()
        score += min(document_count * 5, 15)  # Max 15 points
        
        # Score for references
        reference_count = worker.references.filter(is_verified=True).count()
        score += min(reference_count * 5, 10)  # Max 10 points
        
        # Cap at 100
        score = min(score, 100)
        
        # Update if changed
        if worker.trust_score != score:
            worker.trust_score = score
            worker.save(update_fields=['trust_score'])
