# messaging/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from messaging.models import Conversation, Message
from messaging.serializers import (
    ConversationSerializer, MessageSerializer,
    CreateConversationSerializer
)
from users.permissions import IsAdmin


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for conversations"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['admin', 'super_admin']:
            return Conversation.objects.all()
        
        # Users can see conversations they're part of
        return Conversation.objects.filter(
            Q(participant_1=user) | Q(participant_2=user)
        ).distinct()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start a new conversation"""
        serializer = CreateConversationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        participant = data['participant']
        contract = data.get('contract')
        
        # Check if conversation already exists
        conversation = Conversation.objects.filter(
            Q(participant_1=request.user, participant_2=participant) |
            Q(participant_1=participant, participant_2=request.user)
        ).first()
        
        if not conversation:
            # Create new conversation
            conversation = Conversation.objects.create(
                participant_1=request.user,
                participant_2=participant,
                contract=contract
            )
        
        # Send initial message
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            receiver=participant,
            message_text=data['initial_message']
        )
        
        return Response({
            "conversation_id": str(conversation.id),
            "message": "Conversation started successfully"
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a conversation"""
        conversation = self.get_object()
        
        # Determine which participant is archiving
        if conversation.participant_1 == request.user:
            conversation.is_archived_1 = True
        else:
            conversation.is_archived_2 = True
        
        conversation.save()
        
        return Response({"status": "archived", "message": "Conversation archived"})
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a conversation"""
        conversation = self.get_object()
        
        # Determine which participant is unarchiving
        if conversation.participant_1 == request.user:
            conversation.is_archived_1 = False
        else:
            conversation.is_archived_2 = False
        
        conversation.save()
        
        return Response({"status": "unarchived", "message": "Conversation unarchived"})
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block a conversation"""
        conversation = self.get_object()
        
        if conversation.is_blocked:
            return Response(
                {"error": "Conversation is already blocked"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.is_blocked = True
        conversation.blocked_by = request.user
        conversation.save()
        
        return Response({"status": "blocked", "message": "Conversation blocked"})
    
    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        """Unblock a conversation"""
        conversation = self.get_object()
        
        if not conversation.is_blocked:
            return Response(
                {"error": "Conversation is not blocked"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Only the user who blocked can unblock, or admin
        if conversation.blocked_by != request.user and request.user.role not in ['admin', 'super_admin']:
            return Response(
                {"error": "You don't have permission to unblock this conversation"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversation.is_blocked = False
        conversation.blocked_by = None
        conversation.save()
        
        return Response({"status": "unblocked", "message": "Conversation unblocked"})


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for messages"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        conversation_id = self.kwargs.get('conversation_id')
        
        # Filter by conversation and user participation
        queryset = Message.objects.filter(
            conversation_id=conversation_id
        ).filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('created_at')
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        
        # Get conversation from URL parameter
        conversation_id = self.kwargs.get('conversation_id')
        from messaging.models import Conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            context['conversation'] = conversation
        except Conversation.DoesNotExist:
            pass
        
        return context
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_id')
        
        # Check if conversation is blocked
        from messaging.models import Conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            if conversation.is_blocked:
                raise serializers.ValidationError("This conversation is blocked")
            
            # Check if user is part of conversation
            if self.request.user not in [conversation.participant_1, conversation.participant_2]:
                raise serializers.ValidationError("You are not part of this conversation")
            
        except Conversation.DoesNotExist:
            raise serializers.ValidationError("Conversation not found")
        
        super().perform_create(serializer)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, conversation_id=None, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        
        # Only the receiver can mark as read
        if message.receiver != request.user:
            return Response(
                {"error": "You can only mark your own messages as read"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.mark_as_read()
        
        return Response({
            "status": "read",
            "message_id": str(message.id),
            "read_at": message.read_at
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request, conversation_id=None):
        """Mark all messages in conversation as read"""
        from messaging.models import Conversation
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Check if user is part of conversation
            if request.user not in [conversation.participant_1, conversation.participant_2]:
                return Response(
                    {"error": "You are not part of this conversation"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Mark all messages where user is receiver as read
            updated_count = Message.objects.filter(
                conversation=conversation,
                receiver=request.user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            
            return Response({
                "status": "all_read",
                "updated_count": updated_count
            })
            
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
