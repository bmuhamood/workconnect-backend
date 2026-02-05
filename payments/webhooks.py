# payments/webhooks.py
import json
import hmac
import hashlib
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings

from payments.models import PaymentTransaction, EmployerInvoice
from payments.gateways import MTNMobileMoney, AirtelMoney, FlutterwaveGateway


@csrf_exempt
@require_POST
def mtn_webhook(request):
    """
    Handle MTN Mobile Money webhook callbacks
    """
    # Verify signature
    signature = request.headers.get("X-Callback-Signature")
    payload = request.body
    
    # In production, verify against your webhook secret
    # For now, accept all in sandbox
    if settings.DEBUG:
        is_valid = True
    else:
        is_valid = True  # Implement actual verification
    
    if not is_valid:
        return HttpResponse(status=403)
    
    try:
        data = json.loads(payload)
        
        # Parse webhook data
        gateway = MTNMobileMoney()
        parsed_data = gateway.parse_webhook(data)
        
        transaction_id = parsed_data.get("transaction_id")
        status = parsed_data.get("status")
        amount = parsed_data.get("amount")
        
        # Find transaction
        transaction = PaymentTransaction.objects.filter(
            external_reference=transaction_id
        ).first()
        
        if not transaction:
            # Try to find by external ID
            transaction = PaymentTransaction.objects.filter(
                internal_reference=transaction_id
            ).first()
        
        if transaction:
            # Update transaction status
            if status == "SUCCESSFUL":
                transaction.status = PaymentTransaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()
                
                # Update invoice if exists
                try:
                    invoice = EmployerInvoice.objects.get(transaction=transaction)
                    invoice.status = EmployerInvoice.InvoiceStatus.PAID
                    invoice.paid_date = timezone.now()
                    invoice.save()
                    
                    # Trigger worker payment scheduling
                    from payments.services import schedule_worker_payment
                    schedule_worker_payment.delay(invoice.id)
                    
                except EmployerInvoice.DoesNotExist:
                    pass
                    
            elif status == "FAILED":
                transaction.status = PaymentTransaction.TransactionStatus.FAILED
            
            transaction.save()
        
        return JsonResponse({"status": "received"})
        
    except json.JSONDecodeError:
        return HttpResponse(status=400)


@csrf_exempt
@require_POST
def airtel_webhook(request):
    """
    Handle Airtel Money webhook callbacks
    """
    # Similar implementation for Airtel
    payload = request.body
    
    try:
        data = json.loads(payload)
        
        gateway = AirtelMoney()
        parsed_data = gateway.parse_webhook(data)
        
        transaction_id = parsed_data.get("transaction_id")
        status = parsed_data.get("status")
        
        # Find and update transaction
        transaction = PaymentTransaction.objects.filter(
            external_reference=transaction_id
        ).first()
        
        if transaction:
            if status == "TS":
                transaction.status = PaymentTransaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()
                
                # Update invoice
                try:
                    invoice = EmployerInvoice.objects.get(transaction=transaction)
                    invoice.status = EmployerInvoice.InvoiceStatus.PAID
                    invoice.paid_date = timezone.now()
                    invoice.save()
                    
                    # Trigger worker payment
                    from payments.services import schedule_worker_payment
                    schedule_worker_payment.delay(invoice.id)
                    
                except EmployerInvoice.DoesNotExist:
                    pass
                    
            elif status == "TF":
                transaction.status = PaymentTransaction.TransactionStatus.FAILED
            
            transaction.save()
        
        return JsonResponse({"status": "received"})
        
    except json.JSONDecodeError:
        return HttpResponse(status=400)


@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    """
    Handle Flutterwave webhook callbacks
    """
    # Verify signature
    signature = request.headers.get("verifi-hash")
    
    if not signature or signature != settings.FLUTTERWAVE_WEBHOOK_HASH:
        return HttpResponse(status=403)
    
    payload = request.body.decode('utf-8')
    
    try:
        data = json.loads(payload)
        
        gateway = FlutterwaveGateway()
        parsed_data = gateway.parse_webhook(data)
        
        transaction_id = parsed_data.get("transaction_id")
        reference = parsed_data.get("reference")
        status = parsed_data.get("status")
        
        # Find transaction by reference
        transaction = PaymentTransaction.objects.filter(
            external_reference=reference
        ).first()
        
        if transaction:
            if status == "successful":
                transaction.status = PaymentTransaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()
                
                # Verify payment
                verification = gateway.verify_payment(transaction_id)
                
                if verification.get("success") and verification.get("status") == "successful":
                    # Update invoice
                    try:
                        invoice = EmployerInvoice.objects.get(transaction=transaction)
                        invoice.status = EmployerInvoice.InvoiceStatus.PAID
                        invoice.paid_date = timezone.now()
                        invoice.save()
                        
                        # Trigger worker payment
                        from payments.services import schedule_worker_payment
                        schedule_worker_payment.delay(invoice.id)
                        
                    except EmployerInvoice.DoesNotExist:
                        pass
                    
            elif status == "failed":
                transaction.status = PaymentTransaction.TransactionStatus.FAILED
            
            transaction.save()
        
        return JsonResponse({"status": "received"})
        
    except json.JSONDecodeError:
        return HttpResponse(status=400)