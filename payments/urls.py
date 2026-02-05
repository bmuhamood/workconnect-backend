# payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments import views
from payments.webhooks import mtn_webhook, airtel_webhook, flutterwave_webhook

router = DefaultRouter()
router.register(r'invoices', views.EmployerInvoiceViewSet, basename='invoice')
router.register(r'worker-payments', views.WorkerPaymentViewSet, basename='worker-payment')
router.register(r'payment-methods', views.PaymentMethodViewSet, basename='payment-method')
router.register(r'service-fees', views.ServiceFeeConfigViewSet, basename='service-fee')
router.register(r'payroll-cycles', views.PayrollCycleViewSet, basename='payroll-cycle')

urlpatterns = [
    path('', include(router.urls)),
    
    # Webhook endpoints
    path('webhooks/mtn-payment/', mtn_webhook, name='mtn-webhook'),
    path('webhooks/airtel-payment/', airtel_webhook, name='airtel-webhook'),
    path('webhooks/flutterwave-payment/', flutterwave_webhook, name='flutterwave-webhook'),
]
