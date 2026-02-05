# documents/tasks.py (already created above, adding more tasks)
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_documents():
    """Clean up old rejected and expired documents"""
    # Delete rejected documents older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_rejected = WorkerDocument.objects.filter(
        status=WorkerDocument.Status.REJECTED,
        updated_at__lt=cutoff_date
    )
    
    deleted_count, _ = old_rejected.delete()
    
    logger.info(f"Cleaned up {deleted_count} old rejected documents")
    
    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat()
    }


@shared_task
def generate_verification_report():
    """Generate verification report for admin"""
    from django.db.models import Count, Avg
    from django.utils import timezone
    from datetime import datetime
    
    # Calculate statistics
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # Weekly statistics
    weekly_stats = WorkerDocument.objects.filter(
        uploaded_at__date__gte=last_week
    ).aggregate(
        total=Count('id'),
        verified=Count('id', filter=models.Q(status=WorkerDocument.Status.VERIFIED)),
        pending=Count('id', filter=models.Q(status=WorkerDocument.Status.PENDING)),
        rejected=Count('id', filter=models.Q(status=WorkerDocument.Status.REJECTED))
    )
    
    # Monthly statistics
    monthly_stats = WorkerDocument.objects.filter(
        uploaded_at__date__gte=last_month
    ).aggregate(
        total=Count('id'),
        verified=Count('id', filter=models.Q(status=WorkerDocument.Status.VERIFIED)),
        pending=Count('id', filter=models.Q(status=WorkerDocument.Status.PENDING)),
        rejected=Count('id', filter=models.Q(status=WorkerDocument.Status.REJECTED))
    )
    
    # Average verification time
    avg_verification_time = WorkerDocument.objects.filter(
        status=WorkerDocument.Status.VERIFIED,
        uploaded_at__isnull=False,
        verified_at__isnull=False
    ).aggregate(
        avg_time=Avg(models.F('verified_at') - models.F('uploaded_at'))
    )
    
    # Top verifiers
    from django.db.models import Count
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    top_verifiers = User.objects.filter(
        verified_documents__isnull=False
    ).annotate(
        verification_count=Count('verified_documents')
    ).order_by('-verification_count')[:10]
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "period": {
            "week": last_week.isoformat() + " to " + today.isoformat(),
            "month": last_month.isoformat() + " to " + today.isoformat()
        },
        "weekly_statistics": weekly_stats,
        "monthly_statistics": monthly_stats,
        "average_verification_time_hours": avg_verification_time.get('avg_time', 0),
        "top_verifiers": [
            {
                "id": str(user.id),
                "name": user.get_full_name(),
                "email": user.email,
                "verification_count": user.verification_count
            }
            for user in top_verifiers
        ]
    }
    
    # Store report or send via email
    # This could be sent to admin email or stored in the database
    
    return report