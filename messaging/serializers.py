# messaging/serializers.py
from rest_framework import serializers
from messaging.models import Conversation, Message
from users.serializers import UserSerializer
from contracts.serializers import ContractSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = [
            'sender', 'receiver', 'status', 'is_read',
            'read_at', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        # Check that receiver is not the same as sender
        request = self.context['request']
        receiver_id = self.context.get('receiver_id')
        
        if receiver_id and str(receiver_id) == str(request.user.id):
            raise serializers.ValidationError("You cannot send a message to yourself")
        
        return data
    
    def create(self, validated_data):
        conversation = self.context['conversation']
        request = self.context['request']
        
        validated_data['sender'] = request.user
        validated_data['receiver'] = conversation.get_other_participant(request.user)
        validated_data['conversation'] = conversation
        
        return super().create(validated_data)


class ConversationSerializer(serializers.ModelSerializer):
    participant_1 = UserSerializer(read_only=True)
    participant_2 = UserSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = '__all__'
        read_only_fields = [
            'last_message_at', 'created_at', 'updated_at'
        ]
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_participant(request.user)
            return {
                'id': str(other.id),
                'name': other.get_full_name(),
                'email': other.email,
                'role': other.role
            }
        return None
    
    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return {
                'text': last_message.message_text[:100] + '...' if len(last_message.message_text) > 100 else last_message.message_text,
                'sender_id': str(last_message.sender.id),
                'created_at': last_message.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0


class CreateConversationSerializer(serializers.Serializer):
    """Serializer for creating a new conversation"""
    participant_id = serializers.UUIDField()
    contract_id = serializers.UUIDField(required=False)
    initial_message = serializers.CharField(max_length=1000)
    
    def validate(self, data):
        from users.models import User
        from contracts.models import Contract
        
        participant_id = data['participant_id']
        request_user = self.context['request'].user
        
        # Check if participant exists
        try:
            participant = User.objects.get(id=participant_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Participant not found")
        
        # Check if trying to message yourself
        if participant == request_user:
            raise serializers.ValidationError("You cannot message yourself")
        
        # Check contract if provided
        contract_id = data.get('contract_id')
        if contract_id:
            try:
                contract = Contract.objects.get(id=contract_id)
                # Check if both users are part of the contract
                if request_user not in [contract.employer.user, contract.worker.user]:
                    raise serializers.ValidationError(
                        "You are not part of this contract"
                    )
                if participant not in [contract.employer.user, contract.worker.user]:
                    raise serializers.ValidationError(
                        "Participant is not part of this contract"
                    )
                
                data['contract'] = contract
            except Contract.DoesNotExist:
                raise serializers.ValidationError("Contract not found")
        
        data['participant'] = participant
        return data
