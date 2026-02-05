from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date

from .models import Contract, ContractReplacement, ContractDocument
from .serializers import (
    ContractSerializer, ContractCreateSerializer, ContractSignSerializer,
    TrialFeedbackSerializer, ReplacementRequestSerializer, ReplacementSerializer,
    ContractDocumentSerializer, ContractTerminationSerializer
)
from .services.contract_manager import ContractManager
from .services.document_generator import ContractDocumentGenerator
from users.permissions import IsEmployer, IsWorker, IsContractParty, IsAdmin, IsVerifiedUser


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ContractViewSet(viewsets.ModelViewSet):
    """ViewSet for Contract model"""
    
    serializer_class = ContractSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'contract_type', 'is_trial']
    search_fields = ['job_title', 'job_description', 'worker__first_name', 'employer__first_name']
    ordering_fields = ['start_date', 'created_at', 'worker_salary_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        
        if user.role == 'employer':
            # Employers can see their own contracts
            employer_profile = user.employer_profile
            return Contract.objects.filter(employer=employer_profile)
        
        elif user.role == 'worker':
            # Workers can see their own contracts
            worker_profile = user.worker_profile
            return Contract.objects.filter(worker=worker_profile)
        
        elif user.role in ['admin', 'super_admin']:
            # Admins can see all contracts
            return Contract.objects.all()
        
        return Contract.objects.none()
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'create':
            return ContractCreateSerializer
        elif self.action == 'sign':
            return ContractSignSerializer
        elif self.action == 'trial_feedback':
            return TrialFeedbackSerializer
        elif self.action == 'request_replacement':
            return ReplacementRequestSerializer
        elif self.action == 'terminate':
            return ContractTerminationSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'request_replacement', 'trial_feedback']:
            return [permissions.IsAuthenticated(), IsVerifiedUser(), IsEmployer()]
        elif self.action == 'sign':
            return [permissions.IsAuthenticated(), IsVerifiedUser(), IsContractParty()]
        elif self.action == 'terminate':
            return [permissions.IsAuthenticated(), IsVerifiedUser(), IsContractParty()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsVerifiedUser(), IsAdmin()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Create contract with employer as creator"""
        # The serializer will handle employer assignment
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def generate_document(self, request, pk=None):
        """Generate PDF contract document"""
        contract = self.get_object()
        
        # Check permissions
        if not (request.user == contract.employer.user or 
                request.user.role in ['admin', 'super_admin']):
            return Response(
                {'error': 'You do not have permission to generate documents for this contract'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if contract is in draft state
        if contract.status != Contract.ContractStatus.DRAFT:
            return Response(
                {'error': 'Contract document can only be generated for draft contracts'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Generate PDF document
            generator = ContractDocumentGenerator(contract)
            pdf_url = generator.generate()
            
            return Response({
                'contract_document_url': pdf_url,
                'message': 'Contract document generated successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def document_url(self, request, pk=None):
        """Get signed URL for contract document"""
        contract = self.get_object()
        
        if not contract.contract_document_url:
            return Response(
                {'error': 'Contract document not generated yet'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate signed URL (expires in 1 hour)
        generator = ContractDocumentGenerator(contract)
        signed_url = generator.get_signed_url(expires_in=3600)
        
        if not signed_url:
            return Response(
                {'error': 'Unable to generate signed URL'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'signed_url': signed_url,
            'expires_in': 3600
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """Sign contract by employer or worker"""
        contract = self.get_object()
        user = request.user
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is allowed to sign
        if user.role == 'employer' and contract.employer.user == user:
            contract.signed_by_employer = True
            contract.employer_signature_date = timezone.now()
            contract.signature_data_employer = serializer.validated_data['signature_data']
        
        elif user.role == 'worker' and contract.worker.user == user:
            contract.signed_by_worker = True
            contract.worker_signature_date = timezone.now()
            contract.signature_data_worker = serializer.validated_data['signature_data']
        
        else:
            return Response(
                {'error': 'You are not authorized to sign this contract'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if both parties have signed
        if contract.signed_by_employer and contract.signed_by_worker:
            contract.status = Contract.ContractStatus.TRIAL
            contract.activated_at = timezone.now()
            
            # Send notifications
            from notifications.tasks import send_contract_signed_notification
            send_contract_signed_notification.delay(contract.id)
        
        contract.save()
        
        return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate contract (admin or after start date)"""
        contract = self.get_object()
        
        # Check permissions (admin only)
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only administrators can manually activate contracts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if contract can be activated
        if contract.status != Contract.ContractStatus.DRAFT:
            return Response(
                {'error': 'Only draft contracts can be activated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not contract.signed_by_employer or not contract.signed_by_worker:
            return Response(
                {'error': 'Both parties must sign the contract before activation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contract_manager = ContractManager()
            contract_manager.activate_contract(contract)
            
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def trial_feedback(self, request, pk=None):
        """Submit feedback during trial period"""
        contract = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if contract is in trial
        if not contract.is_trial or contract.status != Contract.ContractStatus.TRIAL:
            return Response(
                {'error': 'Can only submit feedback during trial period'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is the employer
        if request.user != contract.employer.user:
            return Response(
                {'error': 'Only the employer can submit trial feedback'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        contract.trial_feedback = serializer.validated_data['feedback_text']
        contract.save()
        
        # Notify worker about feedback
        from notifications.tasks import send_trial_feedback_notification
        send_trial_feedback_notification.delay(
            contract.worker.user.id,
            contract.id,
            serializer.validated_data['performance_rating']
        )
        
        return Response({
            'message': 'Feedback submitted successfully',
            'will_continue': serializer.validated_data['will_continue']
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def request_replacement(self, request, pk=None):
        """Request worker replacement during trial"""
        contract = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is the employer
        if request.user != contract.employer.user:
            return Response(
                {'error': 'Only the employer can request replacement'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            contract_manager = ContractManager()
            replacement = contract_manager.request_replacement(
                contract,
                serializer.validated_data['reason'],
                request.user
            )
            
            # Find suggested replacements
            from matching.services.smart_matching import SmartMatching
            matcher = SmartMatching()
            suggestions = matcher.find_replacements(contract)
            
            return Response({
                'replacement_id': str(replacement.id),
                'is_free': replacement.is_free_replacement,
                'suggestions': suggestions,
                'message': 'Replacement request submitted successfully'
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def complete_trial(self, request, pk=None):
        """Complete trial period successfully"""
        contract = self.get_object()
        
        # Check if user is the employer
        if request.user != contract.employer.user:
            return Response(
                {'error': 'Only the employer can complete trial'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if trial period has ended
        if not contract.is_trial or contract.status != Contract.ContractStatus.TRIAL:
            return Response(
                {'error': 'Can only complete trial for contracts in trial period'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if contract.trial_end_date > date.today():
            return Response(
                {'error': 'Trial period has not ended yet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contract_manager = ContractManager()
            feedback = request.data.get('feedback', '')
            contract_manager.complete_trial(contract, passed=True, feedback=feedback)
            
            # Create review from employer if rating provided
            rating = request.data.get('rating')
            comment = request.data.get('comment', '')
            
            if rating:
                from reviews.models import Review
                Review.objects.create(
                    contract=contract,
                    reviewer=contract.employer.user,
                    reviewee=contract.worker.user,
                    rating=rating,
                    comment=comment,
                    is_verified=True
                )
            
            # Send completion notifications
            from notifications.tasks import send_trial_completion_notification
            send_trial_completion_notification.delay(contract.id, True)
            
            return Response({
                'message': 'Trial completed successfully',
                'contract_status': contract.status
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate contract"""
        contract = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            contract_manager = ContractManager()
            contract_manager.terminate_contract(
                contract,
                serializer.validated_data['reason'],
                request.user
            )
            
            # Send termination notifications
            from notifications.tasks import send_contract_termination_notification
            send_contract_termination_notification.delay(
                contract.id,
                serializer.validated_data['reason']
            )
            
            return Response({
                'message': 'Contract terminated successfully',
                'contract_status': contract.status
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active contracts for current user"""
        queryset = self.filter_queryset(self.get_queryset())
        active_contracts = queryset.filter(
            status__in=[Contract.ContractStatus.ACTIVE, Contract.ContractStatus.TRIAL]
        )
        
        page = self.paginate_queryset(active_contracts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_contracts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get completed/terminated contracts for current user"""
        queryset = self.filter_queryset(self.get_queryset())
        history_contracts = queryset.filter(
            status__in=[Contract.ContractStatus.COMPLETED, Contract.ContractStatus.TERMINATED]
        )
        
        page = self.paginate_queryset(history_contracts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(history_contracts, many=True)
        return Response(serializer.data)


class ReplacementViewSet(viewsets.ModelViewSet):
    """ViewSet for Contract Replacement requests"""
    
    serializer_class = ReplacementSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        
        if user.role == 'employer':
            # Employers can see their replacement requests
            employer_profile = user.employer_profile
            return ContractReplacement.objects.filter(
                original_contract__employer=employer_profile
            )
        
        elif user.role in ['admin', 'super_admin']:
            # Admins can see all replacement requests
            return ContractReplacement.objects.all()
        
        return ContractReplacement.objects.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['approve_replacement']:
            return [permissions.IsAuthenticated(), IsVerifiedUser(), IsAdmin()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def approve_replacement(self, request, pk=None):
        """Approve a replacement with new worker"""
        replacement = self.get_object()
        
        if replacement.status != ContractReplacement.ReplacementStatus.REQUESTED:
            return Response(
                {'error': 'Only requested replacements can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        worker_id = request.data.get('replacement_worker_id')
        if not worker_id:
            return Response(
                {'error': 'Replacement worker ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the new worker
        from users.models import WorkerProfile
        try:
            new_worker = WorkerProfile.objects.get(id=worker_id)
        except WorkerProfile.DoesNotExist:
            return Response(
                {'error': 'Worker not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if worker is available
        if new_worker.availability != 'available':
            return Response(
                {'error': 'Worker is not available for new assignments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            contract_manager = ContractManager()
            new_contract = contract_manager.approve_replacement(replacement, new_worker)
            
            return Response({
                'message': 'Replacement approved successfully',
                'new_contract_id': str(new_contract.id),
                'replacement_status': 'completed'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContractDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Contract Documents"""
    
    serializer_class = ContractDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser, IsContractParty]
    
    def get_queryset(self):
        """Filter documents based on user's contracts"""
        user = self.request.user
        
        if user.role == 'employer':
            employer_profile = user.employer_profile
            return ContractDocument.objects.filter(
                contract__employer=employer_profile
            )
        
        elif user.role == 'worker':
            worker_profile = user.worker_profile
            return ContractDocument.objects.filter(
                contract__worker=worker_profile
            )
        
        elif user.role in ['admin', 'super_admin']:
            return ContractDocument.objects.all()
        
        return ContractDocument.objects.none()
    
    def perform_create(self, serializer):
        """Assign uploaded by user"""
        serializer.save(uploaded_by=self.request.user)
