# documents/tasks.py
from celery import shared_task
from django.utils import timezone
from documents.models import (
    WorkerDocument, DocumentVerificationRequest
)
from ai.services import OCRService
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def process_document_verification(verification_request_id):
    """Process document verification using AI OCR"""
    try:
        verification_request = DocumentVerificationRequest.objects.get(
            id=verification_request_id
        )
        
        verification_request.mark_processing()
        
        document = verification_request.document
        
        # Read document file
        document_file = document.document_file
        if not document_file:
            verification_request.mark_failed("Document file not found")
            return
        
        # Use OCR service
        ocr_service = OCRService()
        
        # Process based on document type
        if document.document_type == WorkerDocument.DocumentType.NATIONAL_ID:
            result = ocr_service.extract_id_card_data(document_file.read())
        else:
            # Generic OCR for other documents
            # This would need to be implemented based on the specific AI service
            result = {
                "success": False,
                "error": "OCR not implemented for this document type",
                "extracted_data": {}
            }
        
        if result.get('success'):
            # Update document with OCR results
            document.ai_ocr_result = result
            document.ai_confidence_score = result.get('confidence')
            document.ai_extracted_data = result.get('extracted_data')
            document.save()
            
            # Mark verification as completed
            verification_request.mark_completed(
                result=result.get('extracted_data'),
                confidence=result.get('confidence')
            )
            
            logger.info(f"Document verification completed: {document.id}")
            
        else:
            verification_request.mark_failed(
                result.get('error', 'OCR processing failed')
            )
            
            logger.error(f"Document verification failed: {result.get('error')}")
    
    except DocumentVerificationRequest.DoesNotExist:
        logger.error(f"Verification request not found: {verification_request_id}")
    except Exception as e:
        logger.error(f"Error processing document verification: {str(e)}")
        
        try:
            verification_request.mark_failed(str(e))
        except:
            pass


@shared_task
def check_expiring_documents():
    """Check for expiring documents and send notifications"""
    from datetime import timedelta
    from django.utils import timezone
    from notifications.services import NotificationService
    
    # Get documents expiring in the next 30 days
    threshold_date = timezone.now().date() + timedelta(days=30)
    
    expiring_documents = WorkerDocument.objects.filter(
        status=WorkerDocument.Status.VERIFIED,
        expiry_date__lte=threshold_date,
        expiry_date__gte=timezone.now().date()
    )
    
    notification_service = NotificationService()
    
    for document in expiring_documents:
        # Calculate days until expiry
        days_until_expiry = (document.expiry_date - timezone.now().date()).days
        
        # Send notification to worker
        notification_service.send_notification(
            user=document.worker.user,
            notification_type='verification',
            title=f"Document Expiring Soon",
            message=f"Your {document.get_document_type_display()} "
                   f"expires in {days_until_expiry} days. "
                   f"Please upload a renewed document.",
            data={
                'document_id': str(document.id),
                'document_type': document.document_type,
                'expiry_date': document.expiry_date.isoformat(),
                'days_until_expiry': days_until_expiry
            }
        )
        
        # Send notification to admin if expiring in 7 days or less
        if days_until_expiry <= 7:
            from users.models import User
            admins = User.objects.filter(role__in=['admin', 'super_admin'])
            
            for admin in admins:
                notification_service.send_notification(
                    user=admin,
                    notification_type='verification',
                    title=f"Worker Document Expiring",
                    message=f"{document.worker.full_name}'s "
                           f"{document.get_document_type_display()} "
                           f"expires in {days_until_expiry} days.",
                    data={
                        'worker_id': str(document.worker.id),
                        'document_id': str(document.id),
                        'document_type': document.document_type,
                        'expiry_date': document.expiry_date.isoformat()
                    }
                )
    
    return f"Checked {expiring_documents.count()} expiring documents"


@shared_task
def bulk_verify_documents(document_ids, verified_by_id, notes=None):
    """Bulk verify documents"""
    from users.models import User
    
    try:
        verified_by = User.objects.get(id=verified_by_id)
    except User.DoesNotExist:
        return {"error": "User not found"}
    
    verified_count = 0
    failed_count = 0
    
    for document_id in document_ids:
        try:
            document = WorkerDocument.objects.get(id=document_id)
            
            if document.status == WorkerDocument.Status.PENDING:
                document.verify(verified_by, notes)
                verified_count += 1
            else:
                failed_count += 1
                
        except WorkerDocument.DoesNotExist:
            failed_count += 1
    
    return {
        "verified_count": verified_count,
        "failed_count": failed_count,
        "total": len(document_ids)
    }

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