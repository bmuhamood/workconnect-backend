# ai_services/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from users.models import WorkerProfile
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WorkerProfile)
def trigger_ai_processing_on_profile_update(sender, instance, created, **kwargs):
    """Trigger AI processing when worker profile is updated"""
    if instance.documents.exists() and not instance.ai_processed:
        try:
            # Import here to avoid circular imports
            from ai_services.tasks import process_worker_documents_with_ai
            
            # Trigger background task for AI processing
            process_worker_documents_with_ai.delay(str(instance.id))
            
        except Exception as e:
            logger.error(f"Error triggering AI processing: {str(e)}")


@receiver(post_save, sender='job_postings.JobPosting')
def trigger_ai_matching_on_new_job(sender, instance, created, **kwargs):
    """Trigger AI matching when new job posting is created"""
    if created and instance.status == 'active':
        try:
            # Import here to avoid circular imports
            from ai_services.tasks import generate_ai_recommendations_for_job
            
            # Trigger background task for AI recommendations
            generate_ai_recommendations_for_job.delay(str(instance.id))
            
        except Exception as e:
            logger.error(f"Error triggering AI matching: {str(e)}")


@receiver(post_save, sender='contracts.Contract')
def trigger_ai_analysis_on_new_contract(sender, instance, created, **kwargs):
    """Trigger AI analysis when new contract is created"""
    if created:
        try:
            # Import here to avoid circular imports
            from ai_services.tasks import analyze_contract_with_ai
            
            # Trigger background task for AI contract analysis
            analyze_contract_with_ai.delay(str(instance.id))
            
        except Exception as e:
            logger.error(f"Error triggering AI contract analysis: {str(e)}")


@receiver(post_save, sender='reviews.Review')
def trigger_sentiment_analysis_on_review(sender, instance, created, **kwargs):
    """Trigger sentiment analysis when new review is posted"""
    if created:
        try:
            # Import here to avoid circular imports
            from ai_services.tasks import analyze_review_sentiment
            
            # Trigger background task for sentiment analysis
            analyze_review_sentiment.delay(str(instance.id))
            
        except Exception as e:
            logger.error(f"Error triggering sentiment analysis: {str(e)}")