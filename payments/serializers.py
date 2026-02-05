# payments/serializers.py
from rest_framework import serializers
from payments.models import (
    EmployerInvoice, WorkerPayment, ServiceFeeConfig,
    WorkerPaymentMethod, PayrollCycle
)
from contracts.serializers import ContractSerializer
from users.serializers import EmployerProfileSerializer, WorkerProfileSerializer


class ServiceFeeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeeConfig
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class WorkerPaymentMethodSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    
    class Meta:
        model = WorkerPaymentMethod
        fields = '__all__'
        read_only_fields = ['worker', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate that only one default method exists per worker
        if data.get('is_default', False):
            worker = self.context['request'].user.workerprofile
            if WorkerPaymentMethod.objects.filter(
                worker=worker, is_default=True
            ).exists() and not self.instance:
                raise serializers.ValidationError(
                    "A default payment method already exists"
                )
        return data


class EmployerInvoiceSerializer(serializers.ModelSerializer):
    employer = EmployerProfileSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    payroll_cycle = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = EmployerInvoice
        fields = '__all__'
        read_only_fields = [
            'invoice_number', 'created_at', 'updated_at',
            'paid_date', 'transaction'
        ]


class WorkerPaymentSerializer(serializers.ModelSerializer):
    worker = WorkerProfileSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    invoice = EmployerInvoiceSerializer(read_only=True)
    payroll_cycle = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = WorkerPayment
        fields = '__all__'
        read_only_fields = [
            'payment_reference', 'created_at', 'updated_at',
            'disbursement_date'
        ]


class PayrollCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollCycle
        fields = '__all__'
        read_only_fields = [
            'created_at', 'invoice_generation_date',
            'payment_processing_date', 'closed_at'
        ]


class PaymentMethodSetupSerializer(serializers.Serializer):
    """Serializer for setting up payment method"""
    method_type = serializers.ChoiceField(
        choices=WorkerPaymentMethod.PaymentMethodType.choices
    )
    provider_name = serializers.CharField(max_length=100)
    account_number = serializers.CharField(max_length=100)
    account_name = serializers.CharField(max_length=255, required=False)
    bank_name = serializers.CharField(max_length=100, required=False)
    branch_name = serializers.CharField(max_length=100, required=False)
    swift_code = serializers.CharField(max_length=50, required=False)
    is_default = serializers.BooleanField(default=False)
    
    def validate(self, data):
        method_type = data.get('method_type')
        
        # Validate required fields based on method type
        if method_type in ['mobile_money_mtn', 'mobile_money_airtel']:
            if not data.get('account_number'):
                raise serializers.ValidationError(
                    "Account number (phone number) is required for mobile money"
                )
        elif method_type == 'bank_transfer':
            if not all([data.get('bank_name'), data.get('account_number')]):
                raise serializers.ValidationError(
                    "Bank name and account number are required for bank transfers"
                )
        
        return data