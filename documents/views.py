# documents/views.py
from django.contrib.auth.models import AnonymousUser
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg
from django.utils import timezone

from documents.models import (
    WorkerDocument, DocumentVerificationRequest, DocumentTypeConfig
)
from documents.serializers import (
    WorkerDocumentSerializer, DocumentUploadSerializer,
    DocumentVerificationRequestSerializer, VerifyDocumentSerializer,
    DocumentTypeConfigSerializer, DocumentStatsSerializer
)
from users.permissions import IsWorker, IsAdmin
from users.models import Verification, WorkerReference


class WorkerDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for worker documents"""
    serializer_class = WorkerDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['document_type', 'status']
    search_fields = ['document_number', 'issuing_authority']
    ordering_fields = ['uploaded_at', 'expiry_date', 'verified_at']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return WorkerDocument.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return WorkerDocument.objects.none()
        
        if user.role in ['admin', 'super_admin']:
            return WorkerDocument.objects.all()
        
        elif user.role == 'worker':
            try:
                worker_profile = user.worker_profile
                return WorkerDocument.objects.filter(worker=worker_profile)
            except:
                return WorkerDocument.objects.none()
        
        return WorkerDocument.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        return WorkerDocumentSerializer
    
    def create(self, request, *args, **kwargs):
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                'id': '00000000-0000-0000-0000-000000000000',
                'document_type': 'national_id',
                'status': 'pending'
            }, status=status.HTTP_201_CREATED)
        
        # Use DocumentUploadSerializer for uploads
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Convert to WorkerDocument data
        document_data = serializer.validated_data.copy()
        
        # Use WorkerDocumentSerializer for creation
        document_serializer = WorkerDocumentSerializer(
            data=document_data,
            context={'request': request}
        )
        
        if document_serializer.is_valid():
            document = document_serializer.save()
            return Response(
                WorkerDocumentSerializer(document).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            document_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document file"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "download_url": "swagger-fake-url",
                "filename": "document.pdf",
                "content_type": "application/octet-stream"
            })
        
        document = self.get_object()
        
        # Check permission
        if (document.worker.user != request.user and 
            request.user.role not in ['admin', 'super_admin']):
            return Response(
                {"error": "You don't have permission to download this document"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        file_url = document.get_file_url()
        
        if not file_url:
            return Response(
                {"error": "Document file not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            "download_url": file_url,
            "filename": document.document_file.name.split('/')[-1],
            "content_type": "application/octet-stream"
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def verify(self, request, pk=None):
        """Verify or reject document (admin only)"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "status": "updated",
                "message": "Document verified successfully (swagger fake)",
                "new_status": "verified"
            })
        
        document = self.get_object()
        
        serializer = VerifyDocumentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if data['status'] == WorkerDocument.Status.VERIFIED:
            document.verify(
                user=request.user,
                notes=data.get('verification_notes')
            )
            message = "Document verified successfully"
        else:
            document.reject(
                user=request.user,
                notes=data.get('verification_notes', '')
            )
            message = "Document rejected"
        
        return Response({
            "status": "updated",
            "message": message,
            "new_status": document.status
        })
    
    @action(detail=False, methods=['get'])
    def my_documents(self, request):
        """Get authenticated worker's documents"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response([])
        
        try:
            worker_profile = request.user.worker_profile
            documents = WorkerDocument.objects.filter(worker=worker_profile)
            serializer = self.get_serializer(documents, many=True)
            return Response(serializer.data)
        except:
            return Response(
                {"error": "Worker profile not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get document statistics"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "total_documents": 0,
                "verified_documents": 0,
                "pending_documents": 0,
                "rejected_documents": 0,
                "expired_documents": 0,
                "verification_rate": 0.0,
                "average_verification_time_days": None
            })
        
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total_documents = WorkerDocument.objects.count()
        verified_documents = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.VERIFIED
        ).count()
        pending_documents = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.PENDING
        ).count()
        rejected_documents = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.REJECTED
        ).count()
        expired_documents = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.EXPIRED
        ).count()
        
        verification_rate = 0
        if total_documents > 0:
            verification_rate = (verified_documents / total_documents) * 100
        
        # Calculate average verification time
        verified_docs_with_times = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.VERIFIED,
            uploaded_at__isnull=False,
            verified_at__isnull=False
        )
        
        avg_verification_time = None
        if verified_docs_with_times.exists():
            total_seconds = 0
            for doc in verified_docs_with_times:
                delta = doc.verified_at - doc.uploaded_at
                total_seconds += delta.total_seconds()
            
            avg_seconds = total_seconds / verified_docs_with_times.count()
            avg_verification_time = avg_seconds / (24 * 3600)  # Convert to days
        
        stats = {
            'total_documents': total_documents,
            'verified_documents': verified_documents,
            'pending_documents': pending_documents,
            'rejected_documents': rejected_documents,
            'expired_documents': expired_documents,
            'verification_rate': round(verification_rate, 2),
            'average_verification_time_days': round(avg_verification_time, 2) if avg_verification_time else None
        }
        
        serializer = DocumentStatsSerializer(stats)
        return Response(serializer.data)


class DocumentVerificationRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for document verification requests (Admin only)"""
    serializer_class = DocumentVerificationRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = DocumentVerificationRequest.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'ai_service_used']
    ordering_fields = ['requested_at', 'completed_at']
    ordering = ['-requested_at']
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return DocumentVerificationRequest.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return DocumentVerificationRequest.objects.none()
            
        if user.role in ['admin', 'super_admin']:
            return DocumentVerificationRequest.objects.all()
        
        return DocumentVerificationRequest.objects.none()
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed verification request"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "status": "retrying",
                "message": "Verification request queued for retry"
            })
        
        verification_request = self.get_object()
        
        if verification_request.status != DocumentVerificationRequest.Status.FAILED:
            return Response(
                {"error": "Can only retry failed verification requests"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset and retry
        verification_request.status = DocumentVerificationRequest.Status.PENDING
        verification_request.error_message = None
        verification_request.processed_at = None
        verification_request.completed_at = None
        verification_request.save()
        
        # Trigger processing
        try:
            from documents.tasks import process_document_verification
            process_document_verification.delay(str(verification_request.id))
        except:
            pass  # Task queue might not be set up
        
        return Response({
            "status": "retrying",
            "message": "Verification request queued for retry"
        })


class DocumentTypeConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for document type configuration (Admin only)"""
    serializer_class = DocumentTypeConfigSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = DocumentTypeConfig.objects.all()
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return DocumentTypeConfig.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return DocumentTypeConfig.objects.none()
            
        if user.role in ['admin', 'super_admin']:
            return DocumentTypeConfig.objects.all()
        
        return DocumentTypeConfig.objects.none()
    
    @action(detail=False, methods=['get'])
    def required_types(self, request):
        """Get required document types"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response([])
            
        required_types = DocumentTypeConfig.objects.filter(is_required=True)
        serializer = self.get_serializer(required_types, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_compliance(self, request):
        """Check worker's document compliance"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                'worker_id': 'swagger-fake-id',
                'worker_name': 'Swagger Fake Worker',
                'is_fully_compliant': True,
                'compliance_report': [],
                'required_count': 0,
                'compliant_count': 0
            })
            
        worker_id = request.data.get('worker_id')
        
        if not worker_id:
            return Response(
                {"error": "worker_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from users.models import WorkerProfile
        try:
            worker = WorkerProfile.objects.get(id=worker_id)
        except WorkerProfile.DoesNotExist:
            return Response(
                {"error": "Worker not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        required_types = DocumentTypeConfig.objects.filter(is_required=True)
        worker_documents = WorkerDocument.objects.filter(worker=worker)
        
        compliance_report = []
        all_required_verified = True
        
        for doc_type_config in required_types:
            document = worker_documents.filter(
                document_type=doc_type_config.document_type,
                status=WorkerDocument.Status.VERIFIED
            ).first()
            
            is_compliant = document is not None
            all_required_verified = all_required_verified and is_compliant
            
            compliance_report.append({
                'document_type': doc_type_config.document_type,
                'display_name': doc_type_config.display_name,
                'is_required': doc_type_config.is_required,
                'is_compliant': is_compliant,
                'document_id': str(document.id) if document else None,
                'document_status': document.status if document else 'missing',
                'expiry_date': document.expiry_date if document else None
            })
        
        return Response({
            'worker_id': str(worker.id),
            'worker_name': worker.full_name,
            'is_fully_compliant': all_required_verified,
            'compliance_report': compliance_report,
            'required_count': required_types.count(),
            'compliant_count': sum(1 for item in compliance_report if item['is_compliant'])
        })


class AdminDocumentViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for document management"""
    serializer_class = WorkerDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = WorkerDocument.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['worker', 'document_type', 'status']
    search_fields = ['document_number', 'worker__first_name', 'worker__last_name']
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return WorkerDocument.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return WorkerDocument.objects.none()
            
        if user.role in ['admin', 'super_admin']:
            return WorkerDocument.objects.all()
        
        return WorkerDocument.objects.none()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending documents for verification"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response([])
            
        pending_documents = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.PENDING
        ).order_by('uploaded_at')
        
        serializer = self.get_serializer(pending_documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_verify(self, request):
        """Bulk verify documents"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "task_id": "swagger-fake-task-id",
                "message": "Bulk verification started",
                "document_count": 0
            })
            
        document_ids = request.data.get('document_ids', [])
        notes = request.data.get('verification_notes')
        
        if not document_ids:
            return Response(
                {"error": "document_ids is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process in background
        try:
            from documents.tasks import bulk_verify_documents
            result = bulk_verify_documents.delay(
                document_ids=document_ids,
                verified_by_id=str(request.user.id),
                notes=notes
            )
        except:
            # If task queue not available, process synchronously
            from django.db import transaction
            with transaction.atomic():
                documents = WorkerDocument.objects.filter(id__in=document_ids)
                for doc in documents:
                    doc.verify(user=request.user, notes=notes)
                result = None
        
        return Response({
            "task_id": result.id if result else "processed-synchronously",
            "message": "Bulk verification started",
            "document_count": len(document_ids)
        })
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get documents expiring soon"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "threshold_days": 30,
                "total_count": 0,
                "documents": []
            })
            
        days_threshold = request.query_params.get('days', 30)
        
        try:
            days_threshold = int(days_threshold)
        except ValueError:
            days_threshold = 30
        
        threshold_date = timezone.now().date() + timezone.timedelta(days=days_threshold)
        
        expiring_documents = WorkerDocument.objects.filter(
            status=WorkerDocument.Status.VERIFIED,
            expiry_date__lte=threshold_date,
            expiry_date__gte=timezone.now().date()
        ).order_by('expiry_date')
        
        serializer = self.get_serializer(expiring_documents, many=True)
        
        return Response({
            "threshold_days": days_threshold,
            "total_count": expiring_documents.count(),
            "documents": serializer.data
        })


class VerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for verifications"""
    # ADD THIS LINE - You need to import VerificationSerializer
    from users.serializers import VerificationSerializer
    
    serializer_class = VerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['verification_type', 'status']
    ordering_fields = ['created_at', 'verified_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Verification.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return Verification.objects.none()
        
        if user.role in ['admin', 'super_admin']:
            return Verification.objects.all()
        
        elif user.role == 'worker':
            try:
                worker_profile = user.worker_profile
                return Verification.objects.filter(worker=worker_profile)
            except:
                return Verification.objects.none()
        
        return Verification.objects.none()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def verify(self, request, pk=None):
        """Verify or reject verification (admin only)"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "status": "updated",
                "message": "Verification approved (swagger fake)",
                "new_status": "verified"
            })
        
        verification = self.get_object()
        
        # You need to import VerifyRequestSerializer
        from users.serializers import VerifyRequestSerializer
        
        serializer = VerifyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if data['status'] == Verification.VerificationStatus.VERIFIED:
            verification.verify(
                user=request.user,
                notes=data.get('verification_notes'),
                expires_at=data.get('expires_at')
            )
            message = "Verification approved"
        else:
            verification.reject(
                user=request.user,
                notes=data.get('verification_notes', '')
            )
            message = "Verification rejected"
        
        return Response({
            "status": "updated",
            "message": message,
            "new_status": verification.status
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def pending(self, request):
        """Get pending verifications (admin only)"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response([])
            
        pending_verifications = Verification.objects.filter(
            status=Verification.VerificationStatus.PENDING
        ).order_by('created_at')
        
        serializer = self.get_serializer(pending_verifications, many=True)
        return Response(serializer.data)


class WorkerReferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for worker references"""
    # ADD THIS LINE - You need to import WorkerReferenceSerializer
    from users.serializers import WorkerReferenceSerializer
    
    serializer_class = WorkerReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_verified']
    search_fields = ['referee_name', 'referee_email', 'company_name']
    
    def get_queryset(self):
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return WorkerReference.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return WorkerReference.objects.none()
        
        if user.role in ['admin', 'super_admin']:
            return WorkerReference.objects.all()
        
        elif user.role == 'worker':
            try:
                worker_profile = user.worker_profile
                return WorkerReference.objects.filter(worker=worker_profile)
            except:
                return WorkerReference.objects.none()
        
        return WorkerReference.objects.none()
    
    def perform_create(self, serializer):
        # Set worker from authenticated user
        try:
            worker_profile = self.request.user.worker_profile
            serializer.save(worker=worker_profile)
        except:
            raise serializers.ValidationError("Worker profile not found")
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def verify(self, request, pk=None):
        """Verify reference (admin only)"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({
                "status": "updated",
                "message": "Reference verified (swagger fake)",
                "is_verified": True
            })
        
        reference = self.get_object()
        
        # You need to import ReferenceVerifySerializer
        from users.serializers import ReferenceVerifySerializer
        
        serializer = ReferenceVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if data['is_verified']:
            reference.verify(
                user=request.user,
                notes=data.get('notes')
            )
            message = "Reference verified"
        else:
            reference.is_verified = False
            reference.notes = data.get('notes', '')
            reference.save()
            message = "Reference marked as unverified"
        
        return Response({
            "status": "updated",
            "message": message,
            "is_verified": reference.is_verified
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def unverified(self, request):
        """Get unverified references (admin only)"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Response([])
            
        unverified_references = WorkerReference.objects.filter(
            is_verified=False
        ).order_by('created_at')
        
        serializer = self.get_serializer(unverified_references, many=True)
        return Response(serializer.data)


class VerificationStatsViewSet(viewsets.ViewSet):
    """ViewSet for verification statistics"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def list(self, request):
        """Get verification statistics"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            from users.serializers import VerificationStatsSerializer
            return Response({
                "total_verifications": 0,
                "pending_verifications": 0,
                "verified_verifications": 0,
                "rejected_verifications": 0,
                "expired_verifications": 0,
                "verification_rate": 0.0,
                "total_documents": 0,
                "expired_documents": 0,
                "expiring_soon_documents": 0,
                "total_references": 0,
                "verified_references": 0,
                "pending_references": 0
            })
        
        # Import the serializer here
        from users.serializers import VerificationStatsSerializer
        
        # Verification stats
        total_verifications = Verification.objects.count()
        pending_verifications = Verification.objects.filter(
            status=Verification.VerificationStatus.PENDING
        ).count()
        verified_verifications = Verification.objects.filter(
            status=Verification.VerificationStatus.VERIFIED
        ).count()
        rejected_verifications = Verification.objects.filter(
            status=Verification.VerificationStatus.REJECTED
        ).count()
        expired_verifications = Verification.objects.filter(
            status=Verification.VerificationStatus.EXPIRED
        ).count()
        
        verification_rate = 0
        if total_verifications > 0:
            verification_rate = (verified_verifications / total_verifications) * 100
        
        # Document stats
        total_documents = WorkerDocument.objects.count()
        expired_documents = WorkerDocument.objects.filter(
            expiry_date__lt=timezone.now().date()
        ).count()
        expiring_soon_documents = WorkerDocument.objects.filter(
            expiry_date__gte=timezone.now().date(),
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        ).count()
        
        # Reference stats
        total_references = WorkerReference.objects.count()
        verified_references = WorkerReference.objects.filter(
            is_verified=True
        ).count()
        pending_references = WorkerReference.objects.filter(
            is_verified=False
        ).count()
        
        stats = {
            "total_verifications": total_verifications,
            "pending_verifications": pending_verifications,
            "verified_verifications": verified_verifications,
            "rejected_verifications": rejected_verifications,
            "expired_verifications": expired_verifications,
            "verification_rate": round(verification_rate, 2),
            
            "total_documents": total_documents,
            "expired_documents": expired_documents,
            "expiring_soon_documents": expiring_soon_documents,
            
            "total_references": total_references,
            "verified_references": verified_references,
            "pending_references": pending_references
        }
        
        serializer = VerificationStatsSerializer(stats)
        return Response(serializer.data)