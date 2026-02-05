import uuid
import json
from django.db import models
from django.utils import timezone
from datetime import timedelta, date

from users.models import User, EmployerProfile, WorkerProfile, JobCategory


class Contract(models.Model):
    """Contract between employer and worker"""
    
    class ContractType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full Time'
        PART_TIME = 'part_time', 'Part Time'
        TEMPORARY = 'temporary', 'Temporary'
        ON_DEMAND = 'on_demand', 'On Demand'
    
    class ContractStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        TRIAL = 'trial', 'Trial'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        TERMINATED = 'terminated', 'Terminated'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(EmployerProfile, on_delete=models.SET_NULL, null=True, related_name='contracts')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, related_name='contracts')
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, related_name='contracts')
    
    # Contract details
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.FULL_TIME)
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
    job_title = models.CharField(max_length=255)
    job_description = models.TextField()
    
    # Financial terms
    worker_salary_amount = models.IntegerField()  # Full salary amount
    service_fee_amount = models.IntegerField()  # WorkConnect's fee
    total_monthly_cost = models.IntegerField()  # salary + service_fee
    payment_frequency = models.CharField(max_length=50, default='monthly')
    
    # Contract dates
    start_date = models.DateField()
    trial_end_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Work details
    work_location = models.TextField(blank=True, null=True)
    work_hours_per_week = models.IntegerField(default=40)
    work_schedule = models.JSONField(default=dict)  # {"monday": "8am-5pm"}
    
    # Trial period
    is_trial = models.BooleanField(default=True)
    trial_duration_days = models.IntegerField(default=14)
    trial_passed = models.BooleanField(null=True, blank=True)
    trial_feedback = models.TextField(blank=True, null=True)
    
    # Contract document
    contract_document_url = models.URLField(blank=True, null=True)
    signed_by_employer = models.BooleanField(default=False)
    signed_by_worker = models.BooleanField(default=False)
    employer_signature_date = models.DateTimeField(null=True, blank=True)
    worker_signature_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contracts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Termination
    termination_reason = models.TextField(blank=True, null=True)
    termination_initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                                related_name='terminated_contracts')
    
    # Signature data (encrypted)
    signature_data_employer = models.TextField(blank=True, null=True)
    signature_data_worker = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'contracts'
        indexes = [
            models.Index(fields=['employer']),
            models.Index(fields=['worker']),
            models.Index(fields=['status']),
            models.Index(fields=['trial_end_date']),
            models.Index(fields=['start_date']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        employer_name = self.employer.get_full_name() if self.employer else "Unknown"
        worker_name = f"{self.worker.first_name} {self.worker.last_name}" if self.worker else "Unknown"
        return f"{self.job_title} - {employer_name} & {worker_name}"
    
    def save(self, *args, **kwargs):
        # Calculate trial end date
        if self.start_date and self.trial_duration_days and not self.trial_end_date:
            self.trial_end_date = self.start_date + timedelta(days=self.trial_duration_days)
        
        # Calculate total monthly cost
        if self.worker_salary_amount and self.service_fee_amount:
            self.total_monthly_cost = self.worker_salary_amount + self.service_fee_amount
        
        # Update status based on trial
        if self.is_trial and self.status == self.ContractStatus.ACTIVE:
            self.status = self.ContractStatus.TRIAL
        
        # Auto-activate if both parties have signed and start date has arrived
        if (self.signed_by_employer and self.signed_by_worker and 
            self.status == self.ContractStatus.DRAFT and 
            self.start_date <= date.today()):
            self.status = self.ContractStatus.TRIAL
            if not self.activated_at:
                self.activated_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_active_trial(self):
        """Check if contract is in active trial period"""
        if not self.is_trial or self.status != self.ContractStatus.TRIAL:
            return False
        
        today = date.today()
        return self.start_date <= today <= self.trial_end_date
    
    @property
    def days_until_trial_end(self):
        """Days remaining until trial ends"""
        if not self.is_active_trial:
            return None
        
        today = date.today()
        return (self.trial_end_date - today).days
    
    @property
    def can_request_replacement(self):
        """Check if replacement can be requested"""
        return self.is_active_trial and self.days_until_trial_end > 0
    
    def get_work_schedule_display(self):
        """Format work schedule for display"""
        if not self.work_schedule:
            return "Not specified"
        
        try:
            schedule = json.loads(self.work_schedule) if isinstance(self.work_schedule, str) else self.work_schedule
            return ", ".join([f"{day}: {time}" for day, time in schedule.items()])
        except:
            return str(self.work_schedule)


class ContractReplacement(models.Model):
    """Replacement requests for contracts during trial"""
    
    class ReplacementStatus(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Original contract details
    original_contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='replacements')
    original_worker = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, 
                                       related_name='original_replacements')
    
    # Replacement details
    replacement_worker = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='replacement_contracts')
    new_contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='replacement_from')
    
    # Request details
    reason = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='replacement_requests')
    
    # Status
    status = models.CharField(max_length=20, choices=ReplacementStatus.choices, default=ReplacementStatus.REQUESTED)
    
    # Financial
    is_free_replacement = models.BooleanField(default=True)  # Free during trial
    replacement_fee = models.IntegerField(default=0)  # 50,000 UGX after trial
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'contract_replacements'
        indexes = [
            models.Index(fields=['original_contract']),
            models.Index(fields=['status']),
            models.Index(fields=['requested_at']),
        ]
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Replacement for Contract {self.original_contract.id}"
    
    @property
    def replacement_cost(self):
        """Calculate replacement cost"""
        if self.is_free_replacement:
            return 0
        return self.replacement_fee


class ContractDocument(models.Model):
    """Additional documents related to contracts"""
    
    class DocumentType(models.TextChoices):
        CONTRACT = 'contract', 'Contract'
        AMENDMENT = 'amendment', 'Amendment'
        TERMINATION = 'termination', 'Termination'
        OTHER = 'other', 'Other'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='additional_documents')
    
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_url = models.URLField()
    document_name = models.CharField(max_length=255)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'contract_documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.document_name} - {self.contract}"