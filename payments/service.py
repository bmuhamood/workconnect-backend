# payments/services.py
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from celery import shared_task

from payments.models import (
    PaymentTransaction, EmployerInvoice, WorkerPayment,
    PayrollCycle, ServiceFeeConfig
)
from payments.gateways import MTNMobileMoney, AirtelMoney, FlutterwaveGateway
from contracts.models import Contract
from users.models import User, EmployerProfile, WorkerProfile


class FeeCalculator:
    """Service fee calculation service"""
    
    @staticmethod
    def calculate_service_fee(category_id, worker_salary):
        """
        Calculate WorkConnect service fee based on category configuration
        """
        try:
            config = ServiceFeeConfig.objects.get(
                category_id=category_id,
                is_active=True,
                effective_from__lte=timezone.now().date()
            )
            
            if config.fee_type == "fixed_amount":
                fee = config.fixed_amount
                
            elif config.fee_type == "percentage":
                fee = int(worker_salary * (config.percentage / 100))
                
            elif config.fee_type == "tiered":
                fee = FeeCalculator.calculate_tiered_fee(config.tier_config, worker_salary)
            
            # Apply min/max limits
            if config.minimum_fee and fee < config.minimum_fee:
                fee = config.minimum_fee
            if config.maximum_fee and fee > config.maximum_fee:
                fee = config.maximum_fee
            
            return fee
            
        except ServiceFeeConfig.DoesNotExist:
            # Default fee: 25% of first month's salary
            return int(worker_salary * 0.25)
    
    @staticmethod
    def calculate_tiered_fee(tier_config, salary):
        """Calculate fee based on salary tiers"""
        for tier in tier_config:
            if tier["min"] <= salary <= tier["max"]:
                return tier["fee"]
        
        # If salary exceeds all tiers, use highest tier fee
        return tier_config[-1]["fee"]


class PaymentWorkflow:
    """Handle complete payment workflow"""
    
    def __init__(self):
        self.mtn = MTNMobileMoney()
        self.airtel = AirtelMoney()
        self.flutterwave = FlutterwaveGateway()
    
    def detect_provider(self, phone):
        """Detect mobile money provider based on phone prefix"""
        if phone.startswith('+25677') or phone.startswith('+25676'):
            return "mtn"
        elif phone.startswith('+25670') or phone.startswith('+25671'):
            return "airtel"
        else:
            return "unknown"
    
    @transaction.atomic
    def process_employer_payment(self, invoice):
        """
        Step 1: Collect payment from employer
        """
        employer = invoice.employer.user
        phone = employer.phone
        
        # Determine provider based on phone prefix
        provider = self.detect_provider(phone)
        
        result = None
        if provider == "mtn":
            result = self.mtn.initiate_payment(
                amount=invoice.total_amount,
                phone=phone,
                reference=invoice.invoice_number,
                customer_name=f"{employer.first_name} {employer.last_name}",
                user=employer
            )
        elif provider == "airtel":
            result = self.airtel.initiate_payment(
                amount=invoice.total_amount,
                phone=phone,
                reference=invoice.invoice_number,
                customer_name=f"{employer.first_name} {employer.last_name}",
                user=employer
            )
        elif provider == "unknown" and employer.email:
            # Use Flutterwave for card payments
            result = self.flutterwave.initiate_payment(
                amount=invoice.total_amount,
                email=employer.email,
                reference=invoice.invoice_number,
                phone=phone,
                customer_name=f"{employer.first_name} {employer.last_name}",
                user=employer
            )
        else:
            raise ValueError(f"Unsupported provider for phone: {phone}")
        
        if result.get("success"):
            # Update invoice status
            invoice.status = EmployerInvoice.InvoiceStatus.PENDING
            invoice.payment_method = provider
            invoice.save()
            
            # Link transaction to invoice
            transaction = result.get("transaction")
            if transaction:
                invoice.transaction = transaction
                invoice.save()
            
            return {
                "success": True,
                "payment_id": transaction.id if transaction else result.get("transaction_id"),
                "status": "initiated",
                "payment_link": result.get("payment_link"),
                "message": result.get("message")
            }
        
        return result
    
    @transaction.atomic
    def disburse_worker_salary(self, worker_payment):
        """
        Step 2: Disburse 100% salary to worker
        """
        worker = worker_payment.worker.user
        payment_method = worker_payment.payment_method
        
        result = None
        if payment_method == "mobile_money_mtn":
            result = self.mtn.disburse_payment(
                amount=worker_payment.net_amount,
                phone=worker_payment.account_number,
                reference=worker_payment.payment_reference,
                user=worker
            )
            
        elif payment_method == "mobile_money_airtel":
            result = self.airtel.disburse_payment(
                amount=worker_payment.net_amount,
                phone=worker_payment.account_number,
                reference=worker_payment.payment_reference,
                user=worker
            )
            
        elif payment_method == "bank_transfer":
            # Bank transfer implementation
            result = {
                "success": True,
                "status": "pending",
                "message": "Bank transfer initiated"
            }
            
        elif payment_method == "cash_pickup":
            # Cash pickup implementation
            result = {
                "success": True,
                "status": "pending",
                "message": "Cash pickup voucher generated"
            }
        
        if result.get("success"):
            worker_payment.status = WorkerPayment.PaymentStatus.PROCESSING
            worker_payment.save()
            
            # Create transaction record
            transaction = result.get("transaction")
            if transaction:
                worker_payment.transaction = transaction
                worker_payment.save()
        
        return result


@shared_task
def generate_monthly_invoices():
    """
    Celery task to generate monthly invoices (runs on 15th of each month)
    """
    today = date.today()
    
    if today.day != 15:
        return {"status": "skipped", "reason": "Not invoice generation day"}
    
    # Create payroll cycle
    cycle, created = PayrollCycle.objects.get_or_create(
        month=today.month,
        year=today.year,
        defaults={
            "total_contracts": 0,
            "total_worker_salaries": 0,
            "total_service_fees": 0,
            "total_revenue": 0
        }
    )
    
    # Get all active contracts
    active_contracts = Contract.objects.filter(
        status='active',
        start_date__lte=today
    )
    
    invoices_created = 0
    
    for contract in active_contracts:
        # Check if invoice already exists for this month
        existing_invoice = EmployerInvoice.objects.filter(
            contract=contract,
            payroll_cycle=cycle
        ).first()
        
        if existing_invoice:
            continue
        
        # Calculate service fee
        service_fee = FeeCalculator.calculate_service_fee(
            contract.category_id,
            contract.worker_salary_amount
        )
        
        # Generate invoice number
        invoice_number = f"INV-{today.year}-{today.month:02d}-{contract.id.hex[:8].upper()}"
        
        # Create invoice
        invoice = EmployerInvoice.objects.create(
            invoice_number=invoice_number,
            payroll_cycle=cycle,
            contract=contract,
            employer=contract.employer,
            worker_salary_amount=contract.worker_salary_amount,
            service_fee_amount=service_fee,
            total_amount=contract.worker_salary_amount + service_fee,
            due_date=today + timedelta(days=10)  # Due on 25th
        )
        
        # Update payroll cycle totals
        cycle.total_contracts += 1
        cycle.total_worker_salaries += contract.worker_salary_amount
        cycle.total_service_fees += service_fee
        cycle.total_revenue += service_fee
        
        invoices_created += 1
        
        # TODO: Generate PDF invoice
        # TODO: Send email/SMS notification
    
    cycle.invoices_generated = True
    cycle.invoice_generation_date = timezone.now()
    cycle.save()
    
    return {
        "status": "success",
        "invoices_created": invoices_created,
        "cycle_id": str(cycle.id)
    }


@shared_task
def disburse_worker_salaries():
    """
    Celery task to disburse worker salaries (runs on 28th-30th of each month)
    """
    today = date.today()
    
    if today.day < 28:
        return {"status": "skipped", "reason": "Not disbursement period"}
    
    # Get current payroll cycle
    try:
        cycle = PayrollCycle.objects.get(
            month=today.month,
            year=today.year
        )
    except PayrollCycle.DoesNotExist:
        return {"status": "error", "reason": "Payroll cycle not found"}
    
    # Get all paid invoices for current cycle
    paid_invoices = EmployerInvoice.objects.filter(
        payroll_cycle=cycle,
        status=EmployerInvoice.InvoiceStatus.PAID
    )
    
    payments_processed = 0
    failed_payments = 0
    
    workflow = PaymentWorkflow()
    
    for invoice in paid_invoices:
        contract = invoice.contract
        worker = contract.worker
        
        # Check if payment already exists
        existing_payment = WorkerPayment.objects.filter(
            invoice=invoice,
            contract=contract,
            worker=worker
        ).first()
        
        if existing_payment:
            continue
        
        # Get worker's payment method
        try:
            payment_method = WorkerPaymentMethod.objects.get(
                worker=worker,
                is_default=True
            )
        except WorkerPaymentMethod.DoesNotExist:
            failed_payments += 1
            continue
        
        # Generate payment reference
        payment_reference = f"PAY-{today.year}-{today.month:02d}-{contract.id.hex[:8].upper()}"
        
        # Create payment record
        payment = WorkerPayment.objects.create(
            payment_reference=payment_reference,
            payroll_cycle=cycle,
            contract=contract,
            worker=worker,
            invoice=invoice,
            salary_amount=invoice.worker_salary_amount,
            net_amount=invoice.worker_salary_amount,  # 100% to worker
            payment_method=payment_method.method_type,
            payment_provider=payment_method.provider_name,
            account_number=payment_method.account_number,
            account_name=payment_method.account_name,
            scheduled_date=today
        )
        
        # Process payment
        result = workflow.disburse_worker_salary(payment)
        
        if result.get("success"):
            payments_processed += 1
        else:
            payment.status = WorkerPayment.PaymentStatus.FAILED
            payment.failure_reason = result.get("error")
            payment.save()
            failed_payments += 1
    
    cycle.payments_processed = True
    cycle.payment_processing_date = timezone.now()
    cycle.save()
    
    return {
        "status": "success",
        "payments_processed": payments_processed,
        "failed_payments": failed_payments
    }


@shared_task
def poll_payment_status(transaction_id, provider):
    """
    Poll payment status until confirmed
    """
    max_retries = 10
    retry_delay = 30  # seconds
    
    if provider == "mtn":
        gateway = MTNMobileMoney()
    elif provider == "airtel":
        gateway = AirtelMoney()
    elif provider == "flutterwave":
        gateway = FlutterwaveGateway()
    else:
        return {"success": False, "error": "Unknown provider"}
    
    for attempt in range(max_retries):
        try:
            result = gateway.check_payment_status(transaction_id)
            
            if result.get("status") == "successful":
                # Find and update transaction
                transaction = PaymentTransaction.objects.filter(
                    external_reference=transaction_id
                ).first()
                
                if transaction:
                    transaction.status = PaymentTransaction.TransactionStatus.COMPLETED
                    transaction.save()
                    
                    # Update associated invoice if exists
                    try:
                        invoice = EmployerInvoice.objects.get(transaction=transaction)
                        invoice.status = EmployerInvoice.InvoiceStatus.PAID
                        invoice.paid_date = timezone.now()
                        invoice.save()
                        
                        # Schedule worker payment
                        schedule_worker_payment.apply_async(
                            args=[invoice.id],
                            countdown=300  # 5 minutes delay
                        )
                    except EmployerInvoice.DoesNotExist:
                        pass
                
                return {"success": True, "status": "completed"}
            
            elif result.get("status") == "failed":
                transaction = PaymentTransaction.objects.filter(
                    external_reference=transaction_id
                ).first()
                
                if transaction:
                    transaction.status = PaymentTransaction.TransactionStatus.FAILED
                    transaction.save()
                
                return {"success": False, "status": "failed"}
        
        except Exception as e:
            print(f"Polling attempt {attempt + 1} failed: {str(e)}")
        
        time.sleep(retry_delay)
    
    return {"success": False, "status": "timeout"}


@shared_task
def schedule_worker_payment(invoice_id):
    """
    Schedule worker payment after employer payment is confirmed
    """
    try:
        invoice = EmployerInvoice.objects.get(id=invoice_id)
        contract = invoice.contract
        
        # Check if worker payment already exists
        existing_payment = WorkerPayment.objects.filter(
            invoice=invoice
        ).first()
        
        if existing_payment:
            return {"status": "skipped", "reason": "Payment already exists"}
        
        # This will be processed by the monthly disbursement task
        return {"status": "scheduled", "invoice_id": str(invoice_id)}
        
    except EmployerInvoice.DoesNotExist:
        return {"status": "error", "reason": "Invoice not found"}