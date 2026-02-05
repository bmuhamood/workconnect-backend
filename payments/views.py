# payments/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from payments.models import (
    EmployerInvoice, WorkerPayment, ServiceFeeConfig,
    WorkerPaymentMethod, PayrollCycle
)
from payments.serializers import (
    EmployerInvoiceSerializer, WorkerPaymentSerializer,
    ServiceFeeConfigSerializer, WorkerPaymentMethodSerializer,
    PayrollCycleSerializer, PaymentMethodSetupSerializer
)
from payments.services import PaymentWorkflow, FeeCalculator
from users.permissions import IsEmployer, IsWorker, IsAdmin


class EmployerInvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for employer invoices"""
    serializer_class = EmployerInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payroll_cycle']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin' or user.role == 'super_admin':
            return EmployerInvoice.objects.all()
        
        # Employers can only see their own invoices
        try:
            employer_profile = user.employerprofile
            return EmployerInvoice.objects.filter(employer=employer_profile)
        except:
            return EmployerInvoice.objects.none()
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Initiate payment for an invoice"""
        invoice = self.get_object()
        
        if invoice.status != EmployerInvoice.InvoiceStatus.PENDING:
            return Response(
                {"error": "Invoice cannot be paid at this time"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow = PaymentWorkflow()
        result = workflow.process_employer_payment(invoice)
        
        if result.get("success"):
            return Response(result)
        else:
            return Response(
                {"error": result.get("error")},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Check payment status"""
        invoice = self.get_object()
        
        if not invoice.transaction:
            return Response(
                {"status": "no_transaction"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            "invoice_status": invoice.status,
            "transaction_status": invoice.transaction.status,
            "last_updated": invoice.transaction.updated_at
        })


class WorkerPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for worker payments (read-only)"""
    serializer_class = WorkerPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorker]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'payroll_cycle']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin' or user.role == 'super_admin':
            return WorkerPayment.objects.all()
        
        # Workers can only see their own payments
        try:
            worker_profile = user.workerprofile
            return WorkerPayment.objects.filter(worker=worker_profile)
        except:
            return WorkerPayment.objects.none()
    
    @action(detail=True, methods=['get'])
    def download_payslip(self, request, pk=None):
        """Download payslip PDF"""
        payment = self.get_object()
        
        # TODO: Generate and return payslip PDF
        # For now, return a placeholder
        return Response({
            "message": "Payslip download will be available soon",
            "payment_id": str(payment.id)
        })


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """ViewSet for worker payment methods"""
    serializer_class = WorkerPaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorker]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin' or user.role == 'super_admin':
            return WorkerPaymentMethod.objects.all()
        
        # Workers can only see their own payment methods
        try:
            worker_profile = user.workerprofile
            return WorkerPaymentMethod.objects.filter(worker=worker_profile)
        except:
            return WorkerPaymentMethod.objects.none()
    
    def perform_create(self, serializer):
        user = self.request.user
        worker_profile = user.workerprofile
        serializer.save(worker=worker_profile)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a payment method as default"""
        payment_method = self.get_object()
        
        # Unset all other default methods for this worker
        WorkerPaymentMethod.objects.filter(
            worker=payment_method.worker,
            is_default=True
        ).update(is_default=False)
        
        # Set this one as default
        payment_method.is_default = True
        payment_method.save()
        
        return Response({"status": "default_set"})


class ServiceFeeConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for service fee configuration (Admin only)"""
    serializer_class = ServiceFeeConfigSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = ServiceFeeConfig.objects.all()
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate service fee for given parameters"""
        category_id = request.data.get('category_id')
        salary_amount = request.data.get('salary_amount')
        
        if not category_id or not salary_amount:
            return Response(
                {"error": "category_id and salary_amount are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fee = FeeCalculator.calculate_service_fee(category_id, salary_amount)
            
            return Response({
                "category_id": category_id,
                "salary_amount": salary_amount,
                "service_fee": fee,
                "total_amount": salary_amount + fee
            })
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PayrollCycleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for payroll cycles (Admin only)"""
    serializer_class = PayrollCycleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = PayrollCycle.objects.all().order_by('-year', '-month')
    
    @action(detail=True, methods=['post'])
    def generate_invoices(self, request, pk=None):
        """Generate invoices for payroll cycle"""
        cycle = self.get_object()
        
        if cycle.invoices_generated:
            return Response(
                {"error": "Invoices already generated for this cycle"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Call the invoice generation task
        from payments.services import generate_monthly_invoices
        result = generate_monthly_invoices()
        
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def disburse_salaries(self, request, pk=None):
        """Disburse salaries for payroll cycle"""
        cycle = self.get_object()
        
        if not cycle.invoices_generated:
            return Response(
                {"error": "Invoices not generated for this cycle"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Call the disbursement task
        from payments.services import disburse_worker_salaries
        result = disburse_worker_salaries()
        
        return Response(result)
