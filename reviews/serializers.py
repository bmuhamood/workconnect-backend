# reviews/serializers.py
from rest_framework import serializers
from reviews.models import Review
from users.serializers import UserSerializer
from contracts.serializers import ContractSerializer


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)
    reviewee = UserSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    contract_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = [
            'is_verified', 'is_flagged', 'created_at',
            'updated_at', 'responded_at'
        ]
    
    def validate(self, data):
        # Check if review already exists for this contract by this reviewer
        contract_id = data.get('contract_id')
        reviewer = self.context['request'].user
        
        if contract_id and Review.objects.filter(
            contract_id=contract_id,
            reviewer=reviewer
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this contract"
            )
        
        # Check if user is part of the contract
        from contracts.models import Contract
        try:
            contract = Contract.objects.get(id=contract_id)
            if reviewer not in [contract.employer.user, contract.worker.user]:
                raise serializers.ValidationError(
                    "You can only review contracts you're involved in"
                )
            
            # Set reviewee as the other party
            if reviewer == contract.employer.user:
                data['reviewee'] = contract.worker.user
            else:
                data['reviewee'] = contract.employer.user
                
        except Contract.DoesNotExist:
            raise serializers.ValidationError("Contract not found")
        
        return data
    
    def create(self, validated_data):
        validated_data['reviewer'] = self.context['request'].user
        return super().create(validated_data)


class ReviewResponseSerializer(serializers.Serializer):
    """Serializer for responding to reviews"""
    response = serializers.CharField(max_length=1000)
    
    def update(self, instance, validated_data):
        instance.response = validated_data['response']
        instance.responded_at = timezone.now()
        instance.save()
        return instance
