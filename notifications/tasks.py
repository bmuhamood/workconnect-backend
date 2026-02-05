# notifications/tasks.py
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging
from notifications.services import NotificationService
from notifications.models import Notification

logger = logging.getLogger(__name__)


@shared_task
def send_notification_task(user_id, notification_type, title, message, **kwargs):
    """Send notification task"""
    from users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        notification_service = NotificationService()
        
        success = notification_service.send_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
        
        return {
            "success": success,
            "user_id": str(user_id),
            "notification_type": notification_type
        }
        
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        return {"success": False, "error": "User not found"}


@shared_task
def send_contract_status_notification(contract_id, status, user_id):
    """Send contract status notification"""
    from contracts.models import Contract
    from users.models import User
    
    try:
        contract = Contract.objects.get(id=contract_id)
        user = User.objects.get(id=user_id)
        
        notification_service = NotificationService()
        
        title = f"Contract {status.title()}"
        
        if status == 'draft':
            message = f"Contract '{contract.job_title}' has been created as a draft."
        elif status == 'trial':
            message = f"Contract '{contract.job_title}' is now in trial period."
        elif status == 'active':
            message = f"Contract '{contract.job_title}' is now active."
        elif status == 'completed':
            message = f"Contract '{contract.job_title}' has been completed."
        elif status == 'terminated':
            message = f"Contract '{contract.job_title}' has been terminated."
        else:
            message = f"Contract '{contract.job_title}' status updated to {status}."
        
        success = notification_service.send_notification(
            user=user,
            notification_type='contract',
            title=title,
            message=message,
            action_url=f"/contracts/{contract.id}",
            action_text="View Contract",
            data={
                'contract_id': str(contract.id),
                'contract_title': contract.job_title,
                'status': status
            }
        )
        
        return {
            "success": success,
            "contract_id": str(contract_id),
            "status": status,
            "user_id": str(user_id)
        }
        
    except Contract.DoesNotExist:
        logger.error(f"Contract not found: {contract_id}")
        return {"success": False, "error": "Contract not found"}
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        return {"success": False, "error": "User not found"}


@shared_task
def send_payment_notification(payment_type, user_id, amount, status, reference):
    """Send payment notification"""
    from users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        notification_service = NotificationService()
        
        title = f"Payment {status.title()}"
        message = f"Your {payment_type} of UGX {amount:,} has been {status}. Reference: {reference}"
        
        success = notification_service.send_notification(
            user=user,
            notification_type='payment',
            title=title,
            message=message,
            action_url="/payments/history",
            action_text="View Payment",
            data={
                'payment_type': payment_type,
                'amount': amount,
                'status': status,
                'reference': reference
            }
        )
        
        return {
            "success": success,
            "payment_type": payment_type,
            "amount": amount,
            "status": status,
            "user_id": str(user_id)
        }
        
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        return {"success": False, "error": "User not found"}


@shared_task
def send_message_notification(sender_id, receiver_id, message_preview):
    """Send message notification"""
    from users.models import User
    
    try:
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        
        notification_service = NotificationService()
        
        title = f"New Message from {sender.first_name} {sender.last_name}"
        message = f"{message_preview[:100]}..." if len(message_preview) > 100 else message_preview
        
        success = notification_service.send_notification(
            user=receiver,
            notification_type='message',
            title=title,
            message=message,
            action_url=f"/messages/{sender.id}",
            action_text="View Message",
            data={
                'sender_id': str(sender.id),
                'sender_name': sender.get_full_name(),
                'message_preview': message_preview
            }
        )
        
        return {
            "success": success,
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id)
        }
        
    except User.DoesNotExist as e:
        logger.error(f"User not found: {str(e)}")
        return {"success": False, "error": "User not found"}


@shared_task
def send_verification_notification(worker_id, verification_type, status, admin_id=None):
    """Send verification notification"""
    from users.models import User
    from users.models import WorkerProfile
    
    try:
        worker_profile = WorkerProfile.objects.get(id=worker_id)
        worker = worker_profile.user
        
        notification_service = NotificationService()
        
        if status == 'verified':
            title = f"{verification_type.title()} Verified"
            message = f"Your {verification_type} has been verified successfully."
        elif status == 'rejected':
            title = f"{verification_type.title()} Rejected"
            message = f"Your {verification_type} has been rejected. Please check for updates."
        else:
            title = f"{verification_type.title()} Update"
            message = f"Your {verification_type} status has been updated to {status}."
        
        success = notification_service.send_notification(
            user=worker,
            notification_type='verification',
            title=title,
            message=message,
            action_url="/profile/documents",
            action_text="View Documents",
            data={
                'verification_type': verification_type,
                'status': status,
                'worker_id': str(worker_id)
            }
        )
        
        # Also notify admin if verification was done by admin
        if admin_id and status in ['verified', 'rejected']:
            try:
                admin = User.objects.get(id=admin_id)
                admin_message = f"You {status} {verification_type} for {worker.get_full_name()}"
                
                notification_service.send_notification(
                    user=admin,
                    notification_type='verification',
                    title=f"{verification_type.title()} {status.title()}",
                    message=admin_message,
                    action_url=f"/admin/workers/{worker_id}",
                    action_text="View Worker",
                    data={
                        'worker_id': str(worker_id),
                        'worker_name': worker.get_full_name(),
                        'verification_type': verification_type,
                        'status': status
                    }
                )
            except User.DoesNotExist:
                pass
        
        return {
            "success": success,
            "worker_id": str(worker_id),
            "verification_type": verification_type,
            "status": status
        }
        
    except WorkerProfile.DoesNotExist:
        logger.error(f"Worker profile not found: {worker_id}")
        return {"success": False, "error": "Worker profile not found"}


@shared_task
def send_application_notification(application_id, status, employer_id=None):
    """Send job application notification"""
    from job_postings.models import JobApplication
    
    try:
        application = JobApplication.objects.get(id=application_id)
        worker = application.worker.user
        
        notification_service = NotificationService()
        
        if status == 'accepted':
            title = "Application Accepted"
            message = f"Your application for '{application.job_posting.title}' has been accepted!"
        elif status == 'rejected':
            title = "Application Rejected"
            message = f"Your application for '{application.job_posting.title}' has been rejected."
        elif status == 'shortlisted':
            title = "Application Shortlisted"
            message = f"Your application for '{application.job_posting.title}' has been shortlisted!"
        else:
            title = "Application Update"
            message = f"Your application for '{application.job_posting.title}' status updated to {status}."
        
        success = notification_service.send_notification(
            user=worker,
            notification_type='application',
            title=title,
            message=message,
            action_url=f"/applications/{application.id}",
            action_text="View Application",
            data={
                'application_id': str(application.id),
                'job_title': application.job_posting.title,
                'status': status
            }
        )
        
        # Notify employer if they initiated the status change
        if employer_id:
            from users.models import User
            try:
                employer = User.objects.get(id=employer_id)
                
                employer_message = f"You {status} {worker.get_full_name()}'s application for '{application.job_posting.title}'"
                
                notification_service.send_notification(
                    user=employer,
                    notification_type='application',
                    title=f"Application {status.title()}",
                    message=employer_message,
                    action_url=f"/applications/{application.id}",
                    action_text="View Application",
                    data={
                        'application_id': str(application.id),
                        'worker_name': worker.get_full_name(),
                        'job_title': application.job_posting.title,
                        'status': status
                    }
                )
            except User.DoesNotExist:
                pass
        
        return {
            "success": success,
            "application_id": str(application_id),
            "status": status
        }
        
    except JobApplication.DoesNotExist:
        logger.error(f"Application not found: {application_id}")
        return {"success": False, "error": "Application not found"}


@shared_task
def send_trial_period_reminder(contract_id, days_remaining):
    """Send trial period reminder"""
    from contracts.models import Contract
    
    try:
        contract = Contract.objects.get(id=contract_id)
        employer = contract.employer.user
        worker = contract.worker.user
        
        notification_service = NotificationService()
        
        # Notify employer
        employer_title = "Trial Period Ending Soon"
        employer_message = f"Trial period for '{contract.job_title}' ends in {days_remaining} days. Worker: {worker.get_full_name()}"
        
        notification_service.send_notification(
            user=employer,
            notification_type='contract',
            title=employer_title,
            message=employer_message,
            action_url=f"/contracts/{contract.id}",
            action_text="View Contract",
            data={
                'contract_id': str(contract.id),
                'contract_title': contract.job_title,
                'days_remaining': days_remaining,
                'worker_name': worker.get_full_name()
            }
        )
        
        # Notify worker
        worker_title = "Trial Period Ending Soon"
        worker_message = f"Your trial period for '{contract.job_title}' ends in {days_remaining} days."
        
        notification_service.send_notification(
            user=worker,
            notification_type='contract',
            title=worker_title,
            message=worker_message,
            action_url=f"/contracts/{contract.id}",
            action_text="View Contract",
            data={
                'contract_id': str(contract.id),
                'contract_title': contract.job_title,
                'days_remaining': days_remaining,
                'employer_name': employer.get_full_name()
            }
        )
        
        return {
            "success": True,
            "contract_id": str(contract_id),
            "days_remaining": days_remaining,
            "notified_employer": True,
            "notified_worker": True
        }
        
    except Contract.DoesNotExist:
        logger.error(f"Contract not found: {contract_id}")
        return {"success": False, "error": "Contract not found"}


@shared_task
def send_invoice_reminder(invoice_id, days_until_due):
    """Send invoice reminder"""
    from payments.models import EmployerInvoice
    
    try:
        invoice = EmployerInvoice.objects.get(id=invoice_id)
        employer = invoice.employer.user
        
        notification_service = NotificationService()
        
        if days_until_due > 0:
            title = "Invoice Due Soon"
            message = f"Invoice #{invoice.invoice_number} for UGX {invoice.total_amount:,} is due in {days_until_due} days."
        else:
            title = "Invoice Overdue"
            message = f"Invoice #{invoice.invoice_number} for UGX {invoice.total_amount:,} is overdue by {abs(days_until_due)} days."
        
        success = notification_service.send_notification(
            user=employer,
            notification_type='payment',
            title=title,
            message=message,
            action_url=f"/invoices/{invoice.id}",
            action_text="Pay Invoice",
            data={
                'invoice_id': str(invoice.id),
                'invoice_number': invoice.invoice_number,
                'amount': invoice.total_amount,
                'days_until_due': days_until_due,
                'is_overdue': days_until_due <= 0
            }
        )
        
        return {
            "success": success,
            "invoice_id": str(invoice_id),
            "days_until_due": days_until_due
        }
        
    except EmployerInvoice.DoesNotExist:
        logger.error(f"Invoice not found: {invoice_id}")
        return {"success": False, "error": "Invoice not found"}


@shared_task
def send_salary_disbursement_notification(payment_id):
    """Send salary disbursement notification"""
    from payments.models import WorkerPayment
    
    try:
        payment = WorkerPayment.objects.get(id=payment_id)
        worker = payment.worker.user
        
        notification_service = NotificationService()
        
        title = "Salary Disbursed"
        message = f"Your salary of UGX {payment.net_amount:,} has been disbursed to your {payment.payment_method} account."
        
        success = notification_service.send_notification(
            user=worker,
            notification_type='payment',
            title=title,
            message=message,
            action_url=f"/payments/{payment.id}",
            action_text="View Payment",
            data={
                'payment_id': str(payment.id),
                'amount': payment.net_amount,
                'payment_method': payment.payment_method,
                'reference': payment.payment_reference
            }
        )
        
        return {
            "success": success,
            "payment_id": str(payment_id),
            "worker_id": str(worker.id)
        }
        
    except WorkerPayment.DoesNotExist:
        logger.error(f"Payment not found: {payment_id}")
        return {"success": False, "error": "Payment not found"}


@shared_task
def cleanup_old_notifications():
    """Clean up old notifications"""
    cutoff_date = timezone.now() - timezone.timedelta(days=90)  # Keep 90 days
    
    old_notifications = Notification.objects.filter(
        created_at__lt=cutoff_date,
        is_read=True
    )
    
    deleted_count, _ = old_notifications.delete()
    
    logger.info(f"Cleaned up {deleted_count} old notifications")
    
    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat()
    }


@shared_task
def send_bulk_notifications(user_ids, notification_type, title, message, **kwargs):
    """Send bulk notifications to multiple users"""
    from users.models import User
    
    results = []
    success_count = 0
    failure_count = 0
    
    notification_service = NotificationService()
    
    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id)
            
            success = notification_service.send_notification(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                **kwargs
            )
            
            if success:
                success_count += 1
            else:
                failure_count += 1
            
            results.append({
                "user_id": str(user_id),
                "success": success
            })
            
        except User.DoesNotExist:
            failure_count += 1
            results.append({
                "user_id": str(user_id),
                "success": False,
                "error": "User not found"
            })
    
    return {
        "total": len(user_ids),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results
    }
