# documents/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from documents.models import WorkerDocument
from notifications.services import NotificationService


@receiver(post_save, sender=WorkerDocument)
def handle_document_status_change(sender, instance, created, **kwargs):
    """Handle document status changes and send notifications"""
    if not created:
        # Check if status changed
        try:
            old_instance = WorkerDocument.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                notification_service = NotificationService()
                
                # Send notification to worker
                if instance.status == WorkerDocument.Status.VERIFIED:
                    notification_service.send_notification(
                        user=instance.worker.user,
                        notification_type='verification',
                        title='Document Verified',
                        message=f'Your {instance.get_document_type_display()} has been verified.',
                        data={
                            'document_id': str(instance.id),
                            'document_type': instance.document_type,
                            'verified_by': instance.verified_by.get_full_name() if instance.verified_by else 'System'
                        }
                    )
                
                elif instance.status == WorkerDocument.Status.REJECTED:
                    notification_service.send_notification(
                        user=instance.worker.user,
                        notification_type='verification',
                        title='Document Rejected',
                        message=f'Your {instance.get_document_type_display()} has been rejected. '
                               f'Reason: {instance.verification_notes}',
                        data={
                            'document_id': str(instance.id),
                            'document_type': instance.document_type,
                            'rejected_by': instance.verified_by.get_full_name() if instance.verified_by else 'System',
                            'rejection_reason': instance.verification_notes
                        }
                    )
                
                elif instance.status == WorkerDocument.Status.EXPIRED:
                    notification_service.send_notification(
                        user=instance.worker.user,
                        notification_type='verification',
                        title='Document Expired',
                        message=f'Your {instance.get_document_type_display()} has expired. '
                               f'Please upload a renewed document.',
                        data={
                            'document_id': str(instance.id),
                            'document_type': instance.document_type,
                            'expiry_date': instance.expiry_date.isoformat() if instance.expiry_date else None
                        }
                    )
        
        except WorkerDocument.DoesNotExist:
            pass


@receiver(pre_save, sender=WorkerDocument)
def check_worker_verification_status(sender, instance, **kwargs):
    """Update worker verification status based on documents"""
    if instance.status == WorkerDocument.Status.VERIFIED:
        # Check if all required documents are verified
        from documents.models import DocumentTypeConfig
        
        required_types = DocumentTypeConfig.objects.filter(is_required=True)
        worker_documents = WorkerDocument.objects.filter(worker=instance.worker)
        
        all_verified = True
        for doc_type_config in required_types:
            verified_doc = worker_documents.filter(
                document_type=doc_type_config.document_type,
                status=WorkerDocument.Status.VERIFIED
            ).first()
            
            if not verified_doc:
                all_verified = False
                break
        
        # Update worker verification status
        if all_verified:
            instance.worker.verification_status = 'verified'
            instance.worker.save()