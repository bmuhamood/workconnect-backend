# job_postings/models.py (already created, but adding the save method)
import uuid
from django.db import models
from django.utils import timezone
from users.models import User, EmployerProfile, WorkerProfile
from contracts.models import JobCategory


class JobPosting(models.Model):
    """Model for job postings by employers"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        FILLED = 'filled', 'Filled'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name='job_postings'
    )
    category = models.ForeignKey(
        JobCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='job_postings'
    )
    
    # Job Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField(blank=True, null=True)
    
    # Salary Range
    salary_min = models.PositiveIntegerField()
    salary_max = models.PositiveIntegerField()
    
    # Location and Schedule
    location = models.TextField()
    work_schedule = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    
    # Status and Metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    is_featured = models.BooleanField(default=False)
    
    # Counters
    views_count = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)
    
    # Dates
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employer']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.employer.company_name}"
    
    def save(self, *args, **kwargs):
        # Set published_at when status changes to ACTIVE
        if self.status == JobPosting.Status.ACTIVE and not self.published_at:
            self.published_at = timezone.now()
        
        # Set expires_at if not set (default: 30 days from publish)
        if self.status == JobPosting.Status.ACTIVE and not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        super().save(*args, **kwargs)
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def increment_applications(self):
        """Increment application count"""
        self.applications_count += 1
        self.save(update_fields=['applications_count'])


class JobApplication(models.Model):
    """Model for job applications by workers"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEWED = 'reviewed', 'Reviewed'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    
    # Application Details
    cover_letter = models.TextField(blank=True, null=True)
    expected_salary = models.PositiveIntegerField(null=True, blank=True)
    availability_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # AI Matching
    ai_match_score = models.PositiveIntegerField(null=True, blank=True)  # 0-100
    ai_recommendation = models.TextField(blank=True, null=True)
    
    # Dates
    applied_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job_posting', 'worker']
        indexes = [
            models.Index(fields=['job_posting']),
            models.Index(fields=['worker']),
            models.Index(fields=['status']),
            models.Index(fields=['applied_at']),
        ]
    
    def __str__(self):
        return f"{self.worker.full_name} - {self.job_posting.title}"
    
    def save(self, *args, **kwargs):
        # Update job posting application count
        if not self.pk:  # New application
            self.job_posting.increment_applications()
        
        # Update reviewed_at when status changes from PENDING
        if self.pk:
            old_status = JobApplication.objects.get(pk=self.pk).status
            if old_status == self.Status.PENDING and self.status != self.Status.PENDING:
                self.reviewed_at = timezone.now()
        
        super().save(*args, **kwargs)