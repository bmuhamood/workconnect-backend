from rest_framework import serializers
from django.utils import timezone
from datetime import date, timedelta
import json

from .models import Contract, ContractReplacement, ContractDocument
from users.serializers.worker_serializers import WorkerProfileSerializer
from users.serializers.employer_serializers import EmployerProfileSerializer
from users.models import JobCategory


class ContractSerializer(serializers.ModelSerializer):
    """Serializer for Contract model"""
    
    worker_details = WorkerProfileSerializer(source='worker', read_only=True)
    employer_details = EmployerProfileSerializer(source='employer', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    # Read-only fields
    days_until_trial_end = serializers.IntegerField(read_only=True)
    is_active_trial = serializers.BooleanField(read_only=True)
    can_request_replacement = serializers.BooleanField(read_only=True)
    work_schedule_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = Contract
        fields = [
            'id', 'employer', 'worker', 'category', 'category_name',
            'contract_type', 'status', 'job_title', 'job_description',
            'worker_salary_amount', 'service_fee_amount', 'total_monthly_cost',
            'payment_frequency', 'start_date', 'trial_end_date', 'end_date',
            'work_location', 'work_hours_per_week', 'work_schedule',
            'work_schedule_display', 'is_trial', 'trial_duration_days',
            'trial_passed', 'trial_feedback', 'contract_document_url',
            'signed_by_employer', 'signed_by_worker', 'employer_signature_date',
            'worker_signature_date', 'created_by', 'created_at', 'updated_at',
            'activated_at', 'completed_at', 'termination_reason',
            'days_until_trial_end', 'is_active_trial', 'can_request_replacement',
            'worker_details', 'employer_details'
        ]
        read_only_fields = [
            'id', 'service_fee_amount', 'total_monthly_cost', 'trial_end_date',
            'contract_document_url', 'status', 'created_at', 'updated_at',
            'activated_at', 'completed_at', 'signed_by_employer', 'signed_by_worker',
            'employer_signature_date', 'worker_signature_date', 'created_by'
        ]
    
    def validate(self, data):
        """Validate contract data"""
        # Ensure worker salary is positive
        if 'worker_salary_amount' in data and data['worker_salary_amount'] <= 0:
            raise serializers.ValidationError({
                'worker_salary_amount': 'Salary must be greater than 0'
            })
        
        # Ensure start date is in the future
        if 'start_date' in data and data['start_date'] < date.today():
            raise serializers.ValidationError({
                'start_date': 'Start date must be today or in the future'
            })
        
        # Validate work schedule JSON
        if 'work_schedule' in data:
            try:
                if isinstance(data['work_schedule'], str):
                    json.loads(data['work_schedule'])
            except json.JSONDecodeError:
                raise serializers.ValidationError({
                    'work_schedule': 'Invalid JSON format for work schedule'
                })
        
        return data
    
    def create(self, validated_data):
        """Create contract with calculated service fee"""
        from .services.fee_calculator import FeeCalculator
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        # Get employer from authenticated user
        if not validated_data.get('employer') and request:
            try:
                employer_profile = request.user.employer_profile
                validated_data['employer'] = employer_profile
            except:
                raise serializers.ValidationError({
                    'employer': 'User is not registered as an employer'
                })
        
        # Calculate service fee
        fee_calculator = FeeCalculator()
        category_id = validated_data.get('category').id if validated_data.get('category') else None
        service_fee = fee_calculator.calculate_service_fee(
            category_id,
            validated_data.get('worker_salary_amount', 0)
        )
        
        validated_data['service_fee_amount'] = service_fee
        validated_data['total_monthly_cost'] = (
            validated_data.get('worker_salary_amount', 0) + service_fee
        )
        
        # Set trial end date
        if validated_data.get('start_date') and validated_data.get('trial_duration_days'):
            validated_data['trial_end_date'] = (
                validated_data['start_date'] + 
                timedelta(days=validated_data['trial_duration_days'])
            )
        
        contract = Contract.objects.create(**validated_data)
        
        # Update worker availability
        if contract.worker:
            contract.worker.availability = 'on_assignment'
            contract.worker.save()
        
        return contract


class ContractCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for contract creation"""
    
    class Meta:
        model = Contract
        fields = [
            'worker', 'category', 'job_title', 'job_description',
            'worker_salary_amount', 'start_date', 'trial_duration_days',
            'work_location', 'work_hours_per_week', 'work_schedule',
            'contract_type'
        ]
    
    def validate(self, data):
        """Validate contract creation"""
        # Check if worker is available
        worker = data.get('worker')
        if worker and worker.availability != 'available':
            raise serializers.ValidationError({
                'worker': 'Worker is not available for new assignments'
            })
        
        return data


class ContractSignSerializer(serializers.Serializer):
    """Serializer for contract signing"""
    
    signature_data = serializers.CharField(required=True)
    agreed_to_terms = serializers.BooleanField(required=True)
    
    def validate_signature_data(self, value):
        """Validate signature data"""
        if not value or len(value) < 10:
            raise serializers.ValidationError('Invalid signature data')
        return value
    
    def validate_agreed_to_terms(self, value):
        """Validate terms agreement"""
        if not value:
            raise serializers.ValidationError('You must agree to the terms')
        return value


class TrialFeedbackSerializer(serializers.Serializer):
    """Serializer for trial period feedback"""
    
    feedback_text = serializers.CharField(required=True, max_length=1000)
    performance_rating = serializers.IntegerField(min_value=1, max_value=5)
    will_continue = serializers.BooleanField(required=True)
    
    def validate_performance_rating(self, value):
        """Validate rating"""
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5')
        return value


class ReplacementRequestSerializer(serializers.ModelSerializer):
    """Serializer for replacement requests"""
    
    class Meta:
        model = ContractReplacement
        fields = ['reason', 'is_free_replacement', 'replacement_fee']
        read_only_fields = ['is_free_replacement', 'replacement_fee']
    
    def validate_reason(self, value):
        """Validate reason"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Please provide a detailed reason')
        return value


class ReplacementSerializer(serializers.ModelSerializer):
    """Serializer for replacement records"""
    
    original_worker_details = WorkerProfileSerializer(source='original_worker', read_only=True)
    replacement_worker_details = WorkerProfileSerializer(source='replacement_worker', read_only=True)
    requested_by_email = serializers.EmailField(source='requested_by.email', read_only=True)
    
    class Meta:
        model = ContractReplacement
        fields = [
            'id', 'original_contract', 'original_worker', 'original_worker_details',
            'replacement_worker', 'replacement_worker_details', 'new_contract',
            'reason', 'requested_by', 'requested_by_email', 'status',
            'is_free_replacement', 'replacement_fee', 'replacement_cost',
            'requested_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'requested_by', 'status', 'requested_at', 'completed_at',
            'replacement_cost'
        ]


class ContractDocumentSerializer(serializers.ModelSerializer):
    """Serializer for contract documents"""
    
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    
    class Meta:
        model = ContractDocument
        fields = [
            'id', 'contract', 'document_type', 'document_url', 'document_name',
            'uploaded_by', 'uploaded_by_email', 'uploaded_at', 'description'
        ]
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at']


class ContractTerminationSerializer(serializers.Serializer):
    """Serializer for contract termination"""
    
    reason = serializers.CharField(required=True, max_length=1000)
    termination_date = serializers.DateField(required=False)
    
    def validate_reason(self, value):
        """Validate termination reason"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Please provide a detailed reason for termination')
        return value
    
    def validate_termination_date(self, value):
        """Validate termination date"""
        if value and value < date.today():
            raise serializers.ValidationError('Termination date cannot be in the past')
        return value
