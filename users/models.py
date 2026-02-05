import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
import phonenumbers
from datetime import date


class UserManager(BaseUserManager):
    def create_user(self, email, phone, password=None, **extra_fields):
        """Create and return a regular user with email and phone"""
        if not email:
            raise ValueError('Users must have an email address')
        if not phone:
            raise ValueError('Users must have a phone number')
        
        # Normalize email and phone
        email = self.normalize_email(email)
        phone = self.normalize_phone(phone)
        
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user
    
    def create_superuser(self, email, phone, password, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('phone_verified', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('role', 'super_admin')
        extra_fields.setdefault('status', 'active')
        
        return self.create_user(email, phone, password, **extra_fields)
    
    def normalize_phone(self, phone):
        """Normalize phone number to E.164 format"""
        try:
            parsed = phonenumbers.parse(phone, "UG")
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            # If parsing fails, try to clean it up
            phone = phone.strip().replace(' ', '').replace('-', '')
            if phone.startswith('0'):
                phone = '+256' + phone[1:]
            elif phone.startswith('256'):
                phone = '+' + phone
            elif not phone.startswith('+'):
                phone = '+256' + phone
            return phone


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model for WorkConnect"""
    
    class Role(models.TextChoices):
        EMPLOYER = 'employer', 'Employer'
        WORKER = 'worker', 'Worker'
        ADMIN = 'admin', 'Admin'
        SUPER_ADMIN = 'super_admin', 'Super Admin'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SUSPENDED = 'suspended', 'Suspended'
        PENDING_VERIFICATION = 'pending_verification', 'Pending Verification'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    phone = models.CharField(unique=True, max_length=20)
    
    # Personal information
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Role and status
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING_VERIFICATION)
    
    # Verification flags
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Timestamps
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'first_name', 'last_name', 'role']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['role']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.role})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name
    
    # ADD THESE PROPERTIES TO FIX THE SWAGGER ISSUE
    @property
    def city(self):
        """Get city from the user's profile (employer or worker)."""
        try:
            if hasattr(self, 'employer_profile') and self.employer_profile.city:
                return self.employer_profile.city
            elif hasattr(self, 'worker_profile') and self.worker_profile.city:
                return self.worker_profile.city
        except Exception:
            pass
        return None
    
    @property
    def address(self):
        """Get address from the user's profile (employer only)."""
        try:
            if hasattr(self, 'employer_profile') and self.employer_profile.address:
                return self.employer_profile.address
        except Exception:
            pass
        return None
    
    def save(self, *args, **kwargs):
        # Normalize phone number before saving
        if self.phone:
            self.phone = User.objects.normalize_phone(self.phone)
        
        # Set is_verified based on email and phone verification
        if self.email_verified and self.phone_verified:
            self.is_verified = True
            if self.status == self.Status.PENDING_VERIFICATION:
                self.status = self.Status.ACTIVE
        
        super().save(*args, **kwargs)
        
class EmployerProfile(models.Model):
    """Profile for employers/hiring entities"""
    
    class SubscriptionTier(models.TextChoices):
        BASIC = 'basic', 'Basic'
        PREMIUM = 'premium', 'Premium'
        BUSINESS = 'business', 'Business'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    
    # Personal/Company information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, default='Kampala')
    district = models.CharField(max_length=100, blank=True, null=True)
    
    # Location coordinates
    location_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Profile photo
    profile_photo_url = models.URLField(blank=True, null=True)
    
    # ID verification
    id_number = models.CharField(max_length=50, blank=True, null=True)
    id_verified = models.BooleanField(default=False)
    
    # Subscription
    subscription_tier = models.CharField(
        max_length=50, 
        choices=SubscriptionTier.choices, 
        default=SubscriptionTier.BASIC
    )
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employer_profiles'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['city']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company_name or 'Individual'}"


class WorkerProfile(models.Model):
    """Profile for domestic workers"""
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Expired'
    
    class Availability(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        UNAVAILABLE = 'unavailable', 'Unavailable'
        ON_ASSIGNMENT = 'on_assignment', 'On Assignment'
        FULL_TIME = 'full_time', 'Full Time'
        PART_TIME = 'part_time', 'Part Time'
        FLEXIBLE = 'flexible', 'Flexible'
    
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'

    class SubscriptionTier(models.TextChoices):
        BASIC = 'basic', 'Basic'
        PREMIUM = 'premium', 'Premium'
        PRO = 'pro', 'Pro'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    
    completion_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Profile completion percentage"
    )

    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20, 
        choices=Gender.choices, 
        blank=True, 
        null=True,
        default=''
    )
        
    # Identification
    national_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    profile_photo_url = models.URLField(blank=True, null=True)
    
    # Bio and location
    bio = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, default='Kampala')
    district = models.CharField(max_length=100, blank=True, null=True)
    
    # Location coordinates
    location_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Experience and education
    experience_years = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(50)])
    education_level = models.CharField(max_length=100, blank=True, null=True)
    
    # Languages (stored as JSON)
    languages = models.JSONField(default=list, blank=True)
    
    profession = models.CharField(max_length=255, blank=True, default='')
    additional_skills = models.TextField(blank=True, default='')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Availability
    availability = models.CharField(
        max_length=20, 
        choices=Availability.choices, 
        default=Availability.AVAILABLE
    )
    
    # Salary expectations
    expected_salary_min = models.IntegerField(null=True, blank=True)
    expected_salary_max = models.IntegerField(null=True, blank=True)
    
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    
    # Reputation metrics
    trust_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    total_placements = models.IntegerField(default=0)
    
    # Subscription
    subscription_tier = models.CharField(
        max_length=20, 
        choices=SubscriptionTier.choices, 
        default=SubscriptionTier.BASIC
    )
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'worker_profiles'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['availability']),
            models.Index(fields=['city']),
            models.Index(fields=['rating_average']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def age(self):
        """Calculate age from date of birth"""
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def update_rating(self, new_rating):
        """Update average rating when a new review is added"""
        total_score = self.rating_average * self.total_reviews + new_rating
        self.total_reviews += 1
        self.rating_average = total_score / self.total_reviews
        self.save()

class JobCategory(models.Model):
    """Categories for domestic work (Nanny, Housekeeper, Gardener, etc.)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'job_categories'
        verbose_name_plural = 'Job Categories'
    
    def __str__(self):
        return self.name


class WorkerSkill(models.Model):
    """Skills associated with workers"""
    
    class ProficiencyLevel(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        EXPERT = 'expert', 'Expert'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='skills')
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, related_name='skills')
    
    skill_name = models.CharField(max_length=100)
    proficiency_level = models.CharField(max_length=20, choices=ProficiencyLevel.choices)
    years_of_experience = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_primary = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'worker_skills'
        unique_together = ['worker', 'skill_name']
    
    def __str__(self):
        return f"{self.worker}: {self.skill_name} ({self.proficiency_level})"

class Verification(models.Model):
    """Verification records for workers"""
    
    class VerificationType(models.TextChoices):
        IDENTITY = 'identity', 'Identity'
        BACKGROUND_CHECK = 'background_check', 'Background Check'
        REFERENCE = 'reference', 'Reference'
        SKILLS_CERTIFICATION = 'skills_certification', 'Skills Certification'
        MEDICAL = 'medical', 'Medical'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='verifications')
    
    verification_type = models.CharField(max_length=25, choices=VerificationType.choices)
    status = models.CharField(max_length=20, choices=WorkerProfile.VerificationStatus.choices, 
                             default=WorkerProfile.VerificationStatus.PENDING)
    
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verification_notes = models.TextField(blank=True, null=True)
    
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'verifications'
        indexes = [
            models.Index(fields=['worker']),
            models.Index(fields=['status']),
            models.Index(fields=['verification_type']),
        ]
    
    def __str__(self):
        return f"{self.worker}: {self.get_verification_type_display()} - {self.status}"


class WorkerReference(models.Model):
    """References provided by workers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='references')
    
    referee_name = models.CharField(max_length=255)
    referee_phone = models.CharField(max_length=20)
    referee_email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    
    reference_letter_url = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'worker_references'
    
    def __str__(self):
        return f"{self.worker}: {self.referee_name} ({self.relationship})"


class AuditLog(models.Model):
    """Audit trail for admin actions"""
    
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        READ = 'READ', 'Read'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        PAYMENT = 'PAYMENT', 'Payment'
        VERIFICATION = 'VERIFICATION', 'Verification'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    
    action = models.CharField(max_length=20, choices=Action.choices)
    entity_type = models.CharField(max_length=100, blank=True, null=True)
    entity_id = models.UUIDField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_activity_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.entity_type} - {self.timestamp}"
