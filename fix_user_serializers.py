# fix_user_serializers.py
import os

def fix_admin_user_serializer():
    """Fix AdminUserSerializer in admin_serializers.py."""
    filepath = 'users/serializers/admin_serializers.py'
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find AdminUserSerializer
    if 'class AdminUserSerializer' in content:
        # Replace fields = '__all__' with explicit fields
        old_meta = '''    class Meta:
        model = User
        fields = '__all__'''
        
        new_meta = '''    class Meta:
        model = User
        # Explicitly list only User model fields
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name',
            'role', 'status', 'is_verified', 'email_verified',
            'phone_verified', 'is_active', 'is_staff', 'is_superuser',
            'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_login', 'created_at', 'updated_at']'''
        
        if old_meta in content:
            content = content.replace(old_meta, new_meta)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed AdminUserSerializer in {filepath}")
            return True
        else:
            print(f"⚠️ Could not find exact pattern in {filepath}")
    
    return False

def create_fixed_serializers():
    """Create fixed versions of the registration serializers."""
    
    fixed_code = '''# Fixed registration serializers to avoid Swagger issues

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User, EmployerProfile, WorkerProfile


class RegisterEmployerSerializer(serializers.ModelSerializer):
    """Serializer for employer registration."""
    
    # Profile fields as write-only
    company_name = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True, default='Kampala')
    district = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'phone', 'password', 'first_name', 'last_name',
            'company_name', 'address', 'city', 'district'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        """Create user and employer profile."""
        # Extract profile data
        profile_data = {
            'company_name': validated_data.pop('company_name', None),
            'address': validated_data.pop('address'),
            'city': validated_data.pop('city', 'Kampala'),
            'district': validated_data.pop('district', None),
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
        }
        
        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            phone=validated_data['phone'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role='employer'
        )
        
        # Create employer profile
        EmployerProfile.objects.create(user=user, **profile_data)
        
        return user


class RegisterWorkerSerializer(serializers.ModelSerializer):
    """Serializer for worker registration."""
    
    # Profile fields as write-only
    national_id = serializers.CharField(write_only=True)
    city = serializers.CharField(write_only=True, default='Kampala')
    district = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'phone', 'password', 'first_name', 'last_name',
            'national_id', 'city', 'district'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        """Create user and worker profile."""
        # Extract profile data
        profile_data = {
            'national_id': validated_data.pop('national_id'),
            'city': validated_data.pop('city', 'Kampala'),
            'district': validated_data.pop('district', None),
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
        }
        
        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            phone=validated_data['phone'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role='worker'
        )
        
        # Create worker profile
        WorkerProfile.objects.create(user=user, **profile_data)
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with related data."""
    
    company_name = serializers.CharField(source='employer_profile.company_name', read_only=True)
    address = serializers.CharField(source='employer_profile.address', read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    national_id = serializers.CharField(source='worker_profile.national_id', read_only=True)
    
    def get_city(self, obj):
        """Get city from appropriate profile."""
        if hasattr(obj, 'employer_profile') and obj.employer_profile.city:
            return obj.employer_profile.city
        elif hasattr(obj, 'worker_profile') and obj.worker_profile.city:
            return obj.worker_profile.city
        return None
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name',
            'role', 'status', 'is_verified', 'company_name',
            'address', 'city', 'national_id', 'created_at'
        ]
        read_only_fields = ['created_at']
'''

    # Save to a new file
    with open('fixed_serializers.py', 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    print("✅ Created fixed serializers in fixed_serializers.py")
    print("\nTo use them:")
    print("1. Replace the registration serializers in your auth_serializers.py")
    print("2. Or import from this file: from fixed_serializers import *")

def main():
    print("="*60)
    print("Fixing User Serializers for Swagger Compatibility")
    print("="*60)
    
    print("\n1. Fixing AdminUserSerializer...")
    fix_admin_user_serializer()
    
    print("\n2. Creating fixed registration serializers...")
    create_fixed_serializers()
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("1. Update your registration serializers in auth_serializers.py")
    print("2. Remove profile fields from User model Meta classes")
    print("3. Restart Django server")
    print("4. Test Swagger: http://localhost:8000/swagger/")
    print("="*60)

if __name__ == '__main__':
    main()