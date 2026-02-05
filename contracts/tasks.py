from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
from .models import Contract
from .services.contract_manager import ContractManager
from notifications.tasks import send_trial_reminder_notification


@shared_task
def check_trial_expirations():
    """Check and handle expired trial periods"""
    contract_manager = ContractManager()
    contract_manager.check_trial_expirations()


@shared_task
def send_trial_reminders():
    """Send reminders for trials ending soon"""
    today = date.today()
    reminder_date = today + timedelta(days=2)  # 2 days before trial ends
    
    # Find contracts with trials ending in 2 days
    expiring_trials = Contract.objects.filter(
        status=Contract.ContractStatus.TRIAL,
        trial_end_date=reminder_date,
        trial_passed__isnull=True
    )
    
    for contract in expiring_trials:
        # Send reminder to employer
        send_trial_reminder_notification.delay(
            contract.employer.user.id,
            contract.id,
            'employer',
            2  # days remaining
        )
        
        # Send reminder to worker
        send_trial_reminder_notification.delay(
            contract.worker.user.id,
            contract.id,
            'worker',
            2  # days remaining
        )


@shared_task
def generate_contract_document(contract_id):
    """Generate contract document asynchronously"""
    try:
        contract = Contract.objects.get(id=contract_id)
        generator = ContractDocumentGenerator(contract)
        generator.generate()
    except Contract.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error generating contract document: {e}")
