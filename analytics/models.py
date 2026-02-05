# analytics/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from users.models import User
from contracts.models import Contract
from payments.models import PayrollCycle


class PlatformMetric(models.Model):
    """Daily platform metrics for analytics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_date = models.DateField(unique=True)
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    active_employers = models.PositiveIntegerField(default=0)
    active_workers = models.PositiveIntegerField(default=0)
    
    # Growth metrics
    new_registrations = models.PositiveIntegerField(default=0)
    new_employers = models.PositiveIntegerField(default=0)
    new_workers = models.PositiveIntegerField(default=0)
    
    # Contract metrics
    active_contracts = models.PositiveIntegerField(default=0)
    new_contracts = models.PositiveIntegerField(default=0)
    completed_contracts = models.PositiveIntegerField(default=0)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_fees_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    worker_salaries_disbursed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Engagement metrics
    total_job_postings = models.PositiveIntegerField(default=0)
    total_applications = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    
    # Conversion metrics
    application_to_hire_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    trial_success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-metric_date']
        indexes = [
            models.Index(fields=['metric_date']),
        ]
    
    def __str__(self):
        return f"Metrics for {self.metric_date}"
    
    @classmethod
    def calculate_daily_metrics(cls, date=None):
        """Calculate and save daily metrics"""
        if date is None:
            date = timezone.now().date()
        
        # Check if metrics already exist for this date
        if cls.objects.filter(metric_date=date).exists():
            return cls.objects.get(metric_date=date)
        
        metrics = cls(metric_date=date)
        
        # Calculate user metrics
        from users.models import User, EmployerProfile, WorkerProfile
        
        metrics.total_users = User.objects.filter(is_active=True).count()
        metrics.active_employers = EmployerProfile.objects.filter(
            user__is_active=True
        ).count()
        metrics.active_workers = WorkerProfile.objects.filter(
            user__is_active=True,
            availability='available'
        ).count()
        
        # Calculate growth metrics (last 24 hours)
        yesterday = date - timezone.timedelta(days=1)
        metrics.new_registrations = User.objects.filter(
            date_joined__date=date
        ).count()
        metrics.new_employers = User.objects.filter(
            role='employer',
            date_joined__date=date
        ).count()
        metrics.new_workers = User.objects.filter(
            role='worker',
            date_joined__date=date
        ).count()
        
        # Calculate contract metrics
        metrics.active_contracts = Contract.objects.filter(
            status='active'
        ).count()
        metrics.new_contracts = Contract.objects.filter(
            created_at__date=date
        ).count()
        metrics.completed_contracts = Contract.objects.filter(
            status='completed',
            completed_at__date=date
        ).count()
        
        # Calculate financial metrics (for the day)
        from payments.models import PaymentTransaction, EmployerInvoice
        
        daily_transactions = PaymentTransaction.objects.filter(
            created_at__date=date,
            status='completed'
        )
        
        if daily_transactions.exists():
            metrics.service_fees_collected = daily_transactions.filter(
                transaction_type='service_fee'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            metrics.worker_salaries_disbursed = daily_transactions.filter(
                transaction_type='worker_disbursement'
            ).aggregate(total=Sum('amount'))['total'] or 0
        
        metrics.total_revenue = metrics.service_fees_collected
        
        # Calculate engagement metrics
        from job_postings.models import JobPosting, JobApplication
        from messaging.models import Message
        
        metrics.total_job_postings = JobPosting.objects.filter(
            created_at__date=date
        ).count()
        metrics.total_applications = JobApplication.objects.filter(
            applied_at__date=date
        ).count()
        metrics.total_messages = Message.objects.filter(
            created_at__date=date,
            is_system_message=False
        ).count()
        
        # Calculate conversion metrics
        if metrics.total_applications > 0:
            hired_count = Contract.objects.filter(
                created_at__date=date
            ).count()
            metrics.application_to_hire_rate = (
                hired_count / metrics.total_applications * 100
            )
        
        # Calculate trial success rate
        trials_ended = Contract.objects.filter(
            trial_end_date=date
        )
        if trials_ended.exists():
            successful_trials = trials_ended.filter(trial_passed=True).count()
            metrics.trial_success_rate = (
                successful_trials / trials_ended.count() * 100
            )
        
        metrics.save()
        return metrics


class UserActivityLog(models.Model):
    """Log user activities for analytics"""
    
    class ActionType(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        VIEW_PROFILE = 'view_profile', 'View Profile'
        VIEW_JOB = 'view_job', 'View Job'
        APPLY_JOB = 'apply_job', 'Apply Job'
        SEND_MESSAGE = 'send_message', 'Send Message'
        VIEW_CONTRACT = 'view_contract', 'View Contract'
        MAKE_PAYMENT = 'make_payment', 'Make Payment'
        POST_JOB = 'post_job', 'Post Job'
        UPDATE_PROFILE = 'update_profile', 'Update Profile'
        SEARCH = 'search', 'Search'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    entity_type = models.CharField(max_length=50, blank=True, null=True)
    entity_id = models.UUIDField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.action_type} at {self.created_at}"
