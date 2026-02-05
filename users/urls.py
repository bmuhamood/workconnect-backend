# users/urls.py
"""
Consolidated users URLs - UPDATED WITH ALL VIEWS INCLUDED
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter

# Import ALL views from the views.py file
from users.views import (
    # Auth views
    RegisterWorkerView,
    RegisterEmployerView,
    LoginView,
    RequestPhoneVerificationView,
    VerifyPhoneView,
    ResendVerificationOTPView,
    OTPStatusView,
    LogoutView,
    LogoutAllView,
    PasswordResetView,
    PasswordResetConfirmView,
    ChangePasswordView,
    
    # Profile views
    UserProfileView,
    WorkerProfileViewSet,
    EmployerProfileViewSet,
    
    # Utility views
    CheckAuthView,
    HealthCheckView,
)

# Create router
router = SimpleRouter()

# Register ViewSets
router.register(r'workers/profile', WorkerProfileViewSet, basename='worker-profile')
router.register(r'employers/profile', EmployerProfileViewSet, basename='employer-profile')

app_name = 'users'

urlpatterns = [
    # Health Check
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # Router URLs
    *router.urls,
    
    # Authentication URLs
    path('auth/register/worker/', RegisterWorkerView.as_view(), name='register-worker'),
    path('auth/register/employer/', RegisterEmployerView.as_view(), name='register-employer'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/logout-all/', LogoutAllView.as_view(), name='logout-all'),
    path('auth/check-auth/', CheckAuthView.as_view(), name='check-auth'),
    
    # Phone Verification URLs (THESE ARE MISSING IN YOUR CURRENT FILE)
    path('auth/phone/request-verification/', 
         RequestPhoneVerificationView.as_view(), 
         name='request-phone-verification'),
    path('auth/phone/verify/', 
         VerifyPhoneView.as_view(), 
         name='verify-phone'),
    # This is the endpoint you're trying to access:
    path('auth/phone/resend-otp/', 
         ResendVerificationOTPView.as_view(), 
         name='resend-verification-otp'),
    path('auth/phone/status/<str:phone>/', 
         OTPStatusView.as_view(), 
         name='otp-status'),
    
    # User profile URLs
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Password URLs
    path('auth/password/reset/', PasswordResetView.as_view(), name='password-reset'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/password/change/', ChangePasswordView.as_view(), name='change-password'),
    
    # Compatibility URLs (optional - if you want to support old URLs)
    # path('auth/resend-otp/', ResendVerificationOTPView.as_view(), name='resend-otp-legacy'),
]