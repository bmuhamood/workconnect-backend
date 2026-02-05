# documents/models.py
import uuid
import os
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.conf import settings
from users.models import User, WorkerProfile


class WorkerDocument(models.Model):
    """Model for worker documents"""
    
    class DocumentType(models.TextChoices):
        NATIONAL_ID = 'national_id', 'National ID'
        PASSPORT = 'passport', 'Passport'
        POLICE_CHECK = 'police_check', 'Police Check Certificate'
        REFERENCE_LETTER = 'reference_letter', 'Reference Letter'
        CERTIFICATE = 'certificate', 'Professional Certificate'
        MEDICAL_REPORT = 'medical_report', 'Medical Report'
        PASSPORT_PHOTO = 'passport_photo', 'Passport Photo'
        EDUCATIONAL_CERTIFICATE = 'educational_certificate', 'Educational Certificate'
        OTHER = 'other', 'Other'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Verification'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Expired'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices
    )
    
    # File storage
    document_file = models.FileField(
        upload_to='worker_documents/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
            )
        ]
    )
    
    # Document metadata
    document_number = models.CharField(max_length=100, blank=True, null=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    issuing_authority = models.CharField(max_length=255, blank=True, null=True)
    
    # Verification status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # AI OCR results
    ai_ocr_result = models.JSONField(null=True, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    ai_extracted_data = models.JSONField(null=True, blank=True)
    
    # Verification details
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    verification_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Audit trail
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['worker', 'status']),
            models.Index(fields=['document_type']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['status', 'expiry_date']),
        ]
        unique_together = ['worker', 'document_type', 'document_number']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.worker.full_name}"
    
    def save(self, *args, **kwargs):
        # Check if document is expired
        if self.expiry_date and self.expiry_date < timezone.now().date():
            self.status = self.Status.EXPIRED
        
        super().save(*args, **kwargs)
    
    def get_file_url(self):
        """Get signed URL for the document file"""
        if not self.document_file:
            return None
        
        # For S3 storage, generate signed URL
        if hasattr(self.document_file.storage, 'url'):
            return self.document_file.url
        
        return self.document_file.url
    
    def is_expiring_soon(self, days=30):
        """Check if document is expiring soon"""
        if not self.expiry_date:
            return False
        
        days_until_expiry = (self.expiry_date - timezone.now().date()).days
        return 0 <= days_until_expiry <= days
    
    def verify(self, user, notes=None):
        """Verify document"""
        self.status = self.Status.VERIFIED
        self.verified_by = user
        self.verification_notes = notes
        self.verified_at = timezone.now()
        self.save()
    
    def reject(self, user, notes):
        """Reject document"""
        self.status = self.Status.REJECTED
        self.verified_by = user
        self.verification_notes = notes
        self.verified_at = timezone.now()
        self.save()
    
    def get_file_extension(self):
        """Get file extension"""
        if self.document_file:
            return os.path.splitext(self.document_file.name)[1].lower()
        return None
    
    def get_file_size(self):
        """Get file size in MB"""
        if self.document_file and hasattr(self.document_file, 'size'):
            return round(self.document_file.size / (1024 * 1024), 2)  # MB
        return None


class DocumentVerificationRequest(models.Model):
    """Model for document verification requests"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        WorkerDocument,
        on_delete=models.CASCADE,
        related_name='verification_requests'
    )
    
    # AI verification details
    ai_service_used = models.CharField(max_length=100, blank=True, null=True)
    ai_request_id = models.CharField(max_length=255, blank=True, null=True)
    ai_response = models.JSONField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Results
    verification_result = models.JSONField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    requested_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['document', 'status']),
            models.Index(fields=['requested_at']),
        ]
    
    def __str__(self):
        return f"Verification for {self.document}"
    
    def mark_processing(self):
        """Mark request as processing"""
        self.status = self.Status.PROCESSING
        self.processed_at = timezone.now()
        self.save()
    
    def mark_completed(self, result=None, confidence=None):
        """Mark request as completed"""
        self.status = self.Status.COMPLETED
        self.verification_result = result
        self.confidence_score = confidence
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """Mark request as failed"""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save()


class DocumentTypeConfig(models.Model):
    """Configuration for document types"""
    
    document_type = models.CharField(
        max_length=50,
        choices=WorkerDocument.DocumentType.choices,
        unique=True
    )
    
    # Requirements
    is_required = models.BooleanField(default=True)
    requires_expiry_date = models.BooleanField(default=True)
    requires_document_number = models.BooleanField(default=True)
    requires_issuing_authority = models.BooleanField(default=False)
    
    # Validation
    allowed_file_types = models.JSONField(
        default=list,
        help_text="List of allowed file extensions"
    )
    max_file_size_mb = models.IntegerField(
        default=10,
        help_text="Maximum file size in MB"
    )
    
    # AI settings
    use_ai_verification = models.BooleanField(default=True)
    ai_service = models.CharField(
        max_length=50,
        choices=[
            ('google_vision', 'Google Vision API'),
            ('aws_rekognition', 'AWS Rekognition'),
            ('manual', 'Manual Review')
        ],
        default='google_vision'
    )
    
    # Display
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    help_text = models.TextField(blank=True, null=True)
    
    # Ordering
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'document_type']
        verbose_name = "Document Type Configuration"
        verbose_name_plural = "Document Type Configurations"
    
    def __str__(self):
        return self.display_name
    
    def get_allowed_extensions(self):
        """Get allowed file extensions"""
        if isinstance(self.allowed_file_types, list):
            return self.allowed_file_types
        return []