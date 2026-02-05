import uuid
from django.db import models
from django.utils import timezone
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from users.models import User, EmployerProfile, WorkerProfile
from contracts.models import Contract


class PayrollCycle(models.Model):
    """Monthly billing cycles for payroll"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField()
    
    # Statistics
    total_contracts = models.IntegerField(default=0)
    total_worker_salaries = models.BigIntegerField(default=0)  # Sum of all salaries
    total_service_fees = models.BigIntegerField(default=0)  # WorkConnect revenue
    total_revenue = models.BigIntegerField(default=0)  # Same as service fees
    
    # Status flags
    invoices_generated = models.BooleanField(default=False)
    payments_processed = models.BooleanField(default=False)
    cycle_closed = models.BooleanField(default=False)
    
    # Dates
    invoice_generation_date = models.DateTimeField(null=True, blank=True)
    payment_processing_date = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payroll_cycles'
        unique_together = ['month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"Payroll Cycle {self.month}/{self.year}"
    
    @property
    def cycle_name(self):
        """Get display name for cycle"""
        from datetime import datetime
        try:
            date_obj = datetime(self.year, self.month, 1)
            return date_obj.strftime("%B %Y")
        except:
            return f"Month {self.month}, {self.year}"


class EmployerInvoice(models.Model):
    """Invoices for employers (separate worker salary and service fee)"""
    
    class InvoiceStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # Relationships
    payroll_cycle = models.ForeignKey(PayrollCycle, on_delete=models.CASCADE, related_name='invoices')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='invoices')
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='invoices')
    
    # Amounts
    worker_salary_amount = models.IntegerField()  # Goes 100% to worker
    service_fee_amount = models.IntegerField()  # WorkConnect revenue
    additional_fees = models.IntegerField(default=0)  # Insurance, training, etc.
    total_amount = models.IntegerField()  # Sum of all above
    
    # Payment details
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.PENDING)
    due_date = models.DateField()
    paid_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    transaction_reference = models.CharField(max_length=255, null=True, blank=True)
    
    # Document
    invoice_pdf_url = models.URLField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employer_invoices'
        indexes = [
            models.Index(fields=['employer']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['payroll_cycle']),
            models.Index(fields=['invoice_number']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.employer}"
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status == self.InvoiceStatus.PENDING and self.due_date < date.today():
            return True
        return False
    
    def mark_as_paid(self, payment_method, transaction_reference):
        """Mark invoice as paid"""
        self.status = self.InvoiceStatus.PAID
        self.paid_date = timezone.now()
        self.payment_method = payment_method
        self.transaction_reference = transaction_reference
        self.save()


class WorkerPayment(models.Model):
    """Worker salary payments (100% of Salary)"""
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_reference = models.CharField(max_length=50, unique=True)
    
    # Relationships
    payroll_cycle = models.ForeignKey(PayrollCycle, on_delete=models.CASCADE, related_name='worker_payments')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='worker_payments')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(EmployerInvoice, on_delete=models.CASCADE, related_name='worker_payments')
    
    # Payment Amount (Full Salary)
    salary_amount = models.IntegerField()  # 100% of agreed salary
    deductions = models.IntegerField(default=0)  # PAYE, NSSF (if applicable)
    net_amount = models.IntegerField()  # Amount actually transferred
    
    # Payment Method (Configured by Admin)
    payment_method = models.CharField(max_length=50)
    payment_provider = models.CharField(max_length=50, null=True, blank=True)
    account_number = models.CharField(max_length=100)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    transaction_receipt_url = models.URLField(null=True, blank=True)
    
    # Payslip
    payslip_pdf_url = models.URLField(null=True, blank=True)
    
    # Dates
    scheduled_date = models.DateField()
    disbursement_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Error Handling
    failure_reason = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'worker_payments'
        indexes = [
            models.Index(fields=['worker']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['payment_reference']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.payment_reference} - {self.worker}"
    
    def mark_as_completed(self, transaction_id, receipt_url=None):
        """Mark payment as completed"""
        self.status = self.PaymentStatus.COMPLETED
        self.disbursement_date = timezone.now()
        self.transaction_id = transaction_id
        self.transaction_receipt_url = receipt_url
        self.save()
    
    def mark_as_failed(self, reason):
        """Mark payment as failed"""
        self.status = self.PaymentStatus.FAILED
        self.failure_reason = reason
        self.retry_count += 1
        self.save()


class ServiceFeeTransaction(models.Model):
    """Service Fee Transactions (WorkConnect Revenue)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(EmployerInvoice, on_delete=models.CASCADE, related_name='service_fee_transactions')
    payroll_cycle = models.ForeignKey(PayrollCycle, on_delete=models.CASCADE, related_name='service_fee_transactions')
    
    amount = models.IntegerField()
    transaction_date = models.DateTimeField(default=timezone.now)
    
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'service_fee_transactions'
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"Service Fee: UGX {self.amount:,} - {self.transaction_date.date()}"


class WorkerPaymentMethod(models.Model):
    """Payment methods for workers"""
    
    class PaymentMethodType(models.TextChoices):
        MOBILE_MONEY_MTN = 'mobile_money_mtn', 'Mobile Money (MTN)'
        MOBILE_MONEY_AIRTEL = 'mobile_money_airtel', 'Mobile Money (Airtel)'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CASH_PICKUP = 'cash_pickup', 'Cash Pickup'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='payment_methods')
    
    method_type = models.CharField(max_length=50, choices=PaymentMethodType.choices)
    provider_name = models.CharField(max_length=100, null=True, blank=True)
    
    account_number = models.CharField(max_length=100)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    
    # For Bank Transfers
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    branch_name = models.CharField(max_length=100, null=True, blank=True)
    swift_code = models.CharField(max_length=50, null=True, blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'worker_payment_methods'
        unique_together = ['worker', 'method_type', 'account_number']
        indexes = [
            models.Index(fields=['worker']),
        ]
    
    def __str__(self):
        return f"{self.worker}: {self.get_method_type_display()} - {self.account_number}"
    
    def save(self, *args, **kwargs):
        # If this is set as default, unset other defaults for this worker
        if self.is_default:
            WorkerPaymentMethod.objects.filter(
                worker=self.worker,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)


class ServiceFeeConfig(models.Model):
    """Service Fee Configuration (Admin Settings)"""
    
    class FeeCalculationType(models.TextChoices):
        FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'
        PERCENTAGE = 'percentage', 'Percentage'
        TIERED = 'tiered', 'Tiered'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey('users.JobCategory', on_delete=models.CASCADE, related_name='fee_configs')
    
    fee_type = models.CharField(max_length=20, choices=FeeCalculationType.choices, 
                               default=FeeCalculationType.FIXED_AMOUNT)
    
    # For Fixed Amount
    fixed_amount = models.IntegerField(null=True, blank=True)
    
    # For Percentage
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # For Tiered
    tier_config = models.JSONField(null=True, blank=True)
    
    # Limits
    minimum_fee = models.IntegerField(null=True, blank=True)
    maximum_fee = models.IntegerField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=date.today)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_fee_config'
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
        ordering = ['-effective_from']
    
    def __str__(self):
        return f"Fee Config for {self.category.name} - {self.fee_type}"


class PaymentTransaction(models.Model):
    """Record of all payment transactions"""
    
    class TransactionType(models.TextChoices):
        EMPLOYER_PAYMENT = 'employer_payment', 'Employer Payment'
        WORKER_DISBURSEMENT = 'worker_disbursement', 'Worker Disbursement'
        REFUND = 'refund', 'Refund'
    
    class TransactionStatus(models.TextChoices):
        INITIATED = 'initiated', 'Initiated'
        PENDING = 'pending', 'Pending'
        SUCCESSFUL = 'successful', 'Successful'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction details
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    external_reference = models.CharField(max_length=100, unique=True)
    internal_reference = models.CharField(max_length=100, null=True, blank=True)
    
    # Amount and currency
    amount = models.IntegerField()
    currency = models.CharField(max_length=3, default='UGX')
    
    # Payment method
    payment_method = models.CharField(max_length=50)
    payment_provider = models.CharField(max_length=100)
    
    # Status
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.INITIATED)
    provider_status = models.CharField(max_length=100, null=True, blank=True)
    provider_response = models.JSONField(null=True, blank=True)
    
    # User info
    payer_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='sent_payments')
    payee_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='received_payments')
    
    # Related entities
    invoice = models.ForeignKey(EmployerInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    worker_payment = models.ForeignKey(WorkerPayment, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment_transactions'
        indexes = [
            models.Index(fields=['external_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['initiated_at']),
            models.Index(fields=['payer_user']),
            models.Index(fields=['payee_user']),
        ]
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.external_reference} - UGX {self.amount:,}"
