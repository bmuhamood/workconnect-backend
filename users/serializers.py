# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from datetime import date
import re
from django.db import transaction
from django.core.validators import RegexValidator

from .models import User, WorkerProfile, EmployerProfile

User = get_user_model()


# ============= USER SERIALIZERS =============
class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for general use"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name',
            'role', 'status', 'is_verified', 'email_verified',
            'phone_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'role', 'status', 'is_verified', 'email_verified',
            'phone_verified', 'created_at', 'updated_at'
        ]


# ============= AUTH SERIALIZERS =============
class RegisterWorkerSerializer(serializers.Serializer):
    """
    Worker Registration Serializer
    Clean and simple - just works
    """
    
    # Required fields
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True, max_length=20)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    national_id = serializers.CharField(required=True, max_length=50)
    date_of_birth = serializers.DateField(required=True)
    city = serializers.CharField(required=True, max_length=100)
    
    # Optional fields
    gender = serializers.CharField(required=False, default='', allow_blank=True)
    profession = serializers.CharField(required=False, default='', allow_blank=True)
    experience_years = serializers.IntegerField(required=False, default=0)
    availability = serializers.CharField(required=False, default='full_time')
    skills = serializers.CharField(required=False, default='', allow_blank=True)
    
    def validate_email(self, value):
        """Validate email"""
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("Email already registered.")
        
        return value.lower().strip()
    
    def validate_phone(self, value):
        """Simple phone validation"""
        phone = value.strip().replace(' ', '').replace('-', '')
        
        # Normalize
        if phone.startswith('0') and len(phone) == 10:
            phone = '+256' + phone[1:]  # 0756123456 → +256756123456
        elif phone.startswith('256') and len(phone) == 12:
            phone = '+' + phone  # 256756123456 → +256756123456
        
        # Basic validation
        if not phone.startswith('+2567'):
            raise serializers.ValidationError(
                "Please enter a valid Ugandan mobile number starting with 07 or +2567"
            )
        
        if len(phone) != 13:
            raise serializers.ValidationError(
                "Phone number should be 10 digits (07XXXXXXXX)"
            )
        
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Phone number already registered.")
        
        return phone
    
    def validate_national_id(self, value):
        """Simple national ID validation"""
        national_id = value.strip().upper()
        
        if not national_id:
            raise serializers.ValidationError("National ID is required.")
        
        if len(national_id) < 5:
            raise serializers.ValidationError("National ID is too short.")
        
        if len(national_id) > 30:
            raise serializers.ValidationError("National ID is too long (max 30 chars).")
        
        if WorkerProfile.objects.filter(national_id=national_id).exists():
            raise serializers.ValidationError("National ID already registered.")
        
        return national_id
    
    def validate(self, data):
        """Validate entire data"""
        # Password match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match'
            })
        
        # Password strength
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({
                'password': 'Password must be at least 8 characters'
            })
        
        # Age check
        dob = data['date_of_birth']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age < 18:
            raise serializers.ValidationError({
                'date_of_birth': 'You must be at least 18 years old'
            })
        
        return data
    
    def create(self, validated_data):
        """Create worker user and profile"""
        with transaction.atomic():
            # Remove confirm_password
            validated_data.pop('confirm_password')
            
            # Extract data
            email = validated_data.pop('email')
            phone = validated_data.pop('phone')
            password = validated_data.pop('password')
            first_name = validated_data.pop('first_name')
            last_name = validated_data.pop('last_name')
            national_id = validated_data.pop('national_id')
            date_of_birth = validated_data.pop('date_of_birth')
            city = validated_data.pop('city')
            
            # Optional fields
            gender = validated_data.pop('gender', '')
            profession = validated_data.pop('profession', '')
            experience_years = validated_data.pop('experience_years', 0)
            skills = validated_data.pop('skills', '')
            availability = validated_data.pop('availability', 'full_time')
            
            # Create user
            user = User.objects.create_user(
                email=email,
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='worker'
            )
            
            # Create worker profile
            WorkerProfile.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                national_id=national_id,
                date_of_birth=date_of_birth,
                city=city,
                gender=gender,
                profession=profession,
                experience_years=experience_years,
                additional_skills=skills,
                availability=availability,
                # Default values
                completion_percentage=20,
                verification_status='pending',
                trust_score=0,
                rating_average=0,
                total_reviews=0,
                total_placements=0,
                subscription_tier='basic'
            )
            
            return user

    skills = serializers.CharField(
        required=False, 
        default='',
        allow_blank=True,
        help_text="Skills as comma-separated string or array"
    )
    
    def validate_skills(self, value):
        """Accept both array and string, convert to string"""
        if isinstance(value, list):
            # Convert array to comma-separated string
            clean_skills = []
            for skill in value:
                if isinstance(skill, str):
                    clean_skills.append(skill.strip())
                elif skill:  # Convert non-string to string
                    clean_skills.append(str(skill).strip())
            return ', '.join(filter(None, clean_skills))
        
        # If it's already a string, clean it
        if isinstance(value, str):
            return value.strip()
        
        # For any other type, convert to string
        return str(value).strip() if value else ''


class RegisterEmployerSerializer(serializers.Serializer):
    """Employer Registration Serializer"""
    
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True, max_length=20)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    company_name = serializers.CharField(required=False, default='', allow_blank=True)
    address = serializers.CharField(required=False, default='', allow_blank=True)
    city = serializers.CharField(required=False, default='Kampala')
    
    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("Email already registered.")
        
        return value.lower().strip()
    
    def validate_phone(self, value):
        phone = value.strip().replace(' ', '').replace('-', '')
        
        if phone.startswith('0') and len(phone) == 10:
            phone = '+256' + phone[1:]
        elif phone.startswith('256') and len(phone) == 12:
            phone = '+' + phone
        
        if not phone.startswith('+2567'):
            raise serializers.ValidationError(
                "Please enter a valid Ugandan mobile number starting with 07 or +2567"
            )
        
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Phone number already registered.")
        
        return phone
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match'
            })
        
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({
                'password': 'Password must be at least 8 characters'
            })
        
        return data
    
    def create(self, validated_data):
        with transaction.atomic():
            validated_data.pop('confirm_password')
            
            email = validated_data.pop('email')
            phone = validated_data.pop('phone')
            password = validated_data.pop('password')
            first_name = validated_data.pop('first_name')
            last_name = validated_data.pop('last_name')
            company_name = validated_data.pop('company_name', '')
            address = validated_data.pop('address', '')
            city = validated_data.pop('city', 'Kampala')
            
            user = User.objects.create_user(
                email=email,
                phone=phone,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='employer'
            )
            
            EmployerProfile.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                address=address,
                city=city
            )
            
            return user


class LoginSerializer(serializers.Serializer):
    """Login Serializer"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        user = authenticate(email=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        
        data['user'] = user
        return data


class PhoneVerificationSerializer(serializers.Serializer):
    """
    Serializer for phone verification with OTP
    """
    phone = serializers.CharField(
        max_length=15,
        min_length=10,
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{9,14}$',
                message="Phone number must be entered in the format: '+256712345678' or '0712345678'."
            )
        ]
    )
    otp = serializers.CharField(
        max_length=6,
        min_length=6,
        required=True,
        help_text="6-digit OTP code"
    )
    
    def validate_phone(self, value):
        """
        Clean and format phone number
        """
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, value))
        
        # Convert to international format if it's a Ugandan number
        if phone.startswith('0') and len(phone) == 10:
            phone = '256' + phone[1:]
        elif len(phone) == 9 and phone.startswith(('7', '8', '9')):
            phone = '256' + phone
        
        # Add plus sign for consistency
        return '+' + phone
    
    def validate_otp(self, value):
        """
        Validate OTP format
        """
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits")
        
        if len(value) != 6:
            raise serializers.ValidationError("OTP must be exactly 6 digits")
        
        return value


class PhoneVerificationRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP
    """
    phone = serializers.CharField(
        max_length=15,
        min_length=10,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{9,14}$',
                message="Phone number must be entered in the format: '+256712345678' or '0712345678'."
            )
        ]
    )
    
    def validate_phone(self, value):
        """
        Clean and format phone number
        """
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, value))
        
        # Convert to international format if it's a Ugandan number
        if phone.startswith('0') and len(phone) == 10:
            phone = '256' + phone[1:]
        elif len(phone) == 9 and phone.startswith(('7', '8', '9')):
            phone = '256' + phone
        
        # Add plus sign for consistency
        return '+' + phone


# ============= PROFILE SERIALIZERS =============
class WorkerProfileSerializer(serializers.ModelSerializer):
    """Worker Profile Serializer"""
    
    age = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name', 'full_name', 'age',
            'date_of_birth', 'gender', 'national_id', 'city', 'profession',
            'experience_years', 'additional_skills', 'availability', 'hourly_rate',
            'verification_status', 'trust_score', 'rating_average', 'total_reviews',
            'total_placements', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'verification_status', 'trust_score', 'rating_average',
            'total_reviews', 'total_placements', 'created_at', 'updated_at'
        ]
    
    def get_age(self, obj):
        if obj.date_of_birth:
            today = date.today()
            return today.year - obj.date_of_birth.year - (
                (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        return None
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def to_representation(self, instance):
        """Convert skills from string to list for API response"""
        data = super().to_representation(instance)
        
        # Convert skills string to list
        if 'additional_skills' in data and data['additional_skills']:
            skills = data['additional_skills'].split(',')
            data['additional_skills'] = [skill.strip() for skill in skills if skill.strip()]
        else:
            data['additional_skills'] = []
        
        return data
    
    def to_internal_value(self, data):
        """Convert skills list to string for database storage"""
        if 'additional_skills' in data and isinstance(data['additional_skills'], list):
            data['additional_skills'] = ', '.join([str(skill).strip() for skill in data['additional_skills'] if skill])
        return super().to_internal_value(data)


class EmployerProfileSerializer(serializers.ModelSerializer):
    """Employer Profile Serializer"""
    
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    
    class Meta:
        model = EmployerProfile
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name', 'full_name',
            'company_name', 'address', 'city', 'profile_photo_url',
            'id_number', 'id_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


# ============= PASSWORD SERIALIZERS =============
class PasswordResetSerializer(serializers.Serializer):
    """Password Reset Request"""
    
    email_or_phone = serializers.CharField(required=True)
    
    def validate_email_or_phone(self, value):
        """Validate email or phone"""
        value = value.strip()
        
        # Check if it's an email
        if '@' in value:
            try:
                validate_email(value)
                return value.lower()
            except ValidationError:
                raise serializers.ValidationError("Enter a valid email address.")
        
        # Check if it's a phone number
        phone = value.replace(' ', '').replace('-', '')
        
        if phone.startswith('0') and len(phone) == 10:
            phone = '+256' + phone[1:]
        elif phone.startswith('256') and len(phone) == 12:
            phone = '+' + phone
        
        if not phone.startswith('+2567'):
            raise serializers.ValidationError(
                "Please enter a valid Ugandan mobile number starting with 07 or +2567"
            )
        
        return phone


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Password Reset Confirmation"""
    
    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match'
            })
        
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({
                'password': 'Password must be at least 8 characters'
            })
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Change Password"""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        user = self.context['request'].user
        
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({
                'old_password': 'Current password is incorrect'
            })
        
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({
                'confirm_new_password': 'Passwords do not match'
            })
        
        password = data['new_password']
        if len(password) < 8:
            raise serializers.ValidationError({
                'new_password': 'Password must be at least 8 characters'
            })
        
        return data


# ============= UTILITY SERIALIZERS =============
class SimpleUserSerializer(serializers.ModelSerializer):
    """Simple user serializer for lists and basic info"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'first_name', 'last_name', 'role', 'phone_verified']


class BulkRegisterSerializer(serializers.Serializer):
    """Bulk registration serializer (for employers registering multiple workers)"""
    
    workers = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text="List of worker registration data"
    )
    
    def validate_workers(self, value):
        """Validate each worker in the list"""
        if not value:
            raise serializers.ValidationError("Workers list cannot be empty")
        
        if len(value) > 100:
            raise serializers.ValidationError("Cannot register more than 100 workers at once")
        
        # Check for duplicate emails and phones
        emails = set()
        phones = set()
        
        for i, worker in enumerate(value):
            # Validate required fields
            required_fields = ['email', 'phone', 'first_name', 'last_name']
            for field in required_fields:
                if field not in worker:
                    raise serializers.ValidationError(
                        f"Worker {i+1} is missing required field: {field}"
                    )
            
            # Check for duplicates in this batch
            email = worker['email'].lower().strip()
            phone = worker['phone'].strip()
            
            if email in emails:
                raise serializers.ValidationError(f"Duplicate email in batch: {email}")
            if phone in phones:
                raise serializers.ValidationError(f"Duplicate phone in batch: {phone}")
            
            emails.add(email)
            phones.add(phone)
            
            # Check if email/phone already exists in database
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError(
                    f"Email already registered: {email}"
                )
            
            phone_normalized = phone.replace(' ', '').replace('-', '')
            if phone_normalized.startswith('0'):
                phone_normalized = '+256' + phone_normalized[1:]
            
            if User.objects.filter(phone=phone_normalized).exists():
                raise serializers.ValidationError(
                    f"Phone already registered: {phone}"
                )
        
        return value