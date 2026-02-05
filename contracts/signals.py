from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Contract
from notifications.tasks import send_contract_status_notification


@receiver(pre_save, sender=Contract)
def update_contract_status(sender, instance, **kwargs):
    """Update contract status and related fields before saving"""
    # Auto-activate if both parties have signed and start date has arrived
    if (instance.signed_by_employer and instance.signed_by_worker and 
        instance.status == Contract.ContractStatus.DRAFT and 
        instance.start_date <= date.today()):
        instance.status = Contract.ContractStatus.TRIAL
        if not instance.activated_at:
            instance.activated_at = timezone.now()


@receiver(post_save, sender=Contract)
def handle_contract_status_change(sender, instance, created, **kwargs):
    """Handle contract status changes"""
    if not created:
        # Check if status changed
        try:
            old_instance = Contract.objects.get(id=instance.id)
            if old_instance.status != instance.status:
                # Send notification for status change
                send_contract_status_notification.delay(
                    instance.id,
                    old_instance.status,
                    instance.status
                )
        except Contract.DoesNotExist:
            pass
    
    # Update worker availability
    if instance.worker:
        if instance.status in [Contract.ContractStatus.ACTIVE, Contract.ContractStatus.TRIAL]:
            instance.worker.availability = 'on_assignment'
        elif instance.status in [Contract.ContractStatus.COMPLETED, Contract.ContractStatus.TERMINATED, 
                                Contract.ContractStatus.CANCELLED]:
            instance.worker.availability = 'available'
        instance.worker.save(update_fields=['availability'])
