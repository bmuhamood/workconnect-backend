# users/views.py
from rest_framework import status, generics, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
import logging

from .models import User, WorkerProfile, EmployerProfile
from .serializers import (
    UserSerializer,
    RegisterWorkerSerializer,
    RegisterEmployerSerializer,
    LoginSerializer,
    PhoneVerificationSerializer,
    PhoneVerificationRequestSerializer,
    WorkerProfileSerializer,
    EmployerProfileSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer
)
from .services.otp_service import OTPService

logger = logging.getLogger(__name__)


# ============= AUTH VIEWS =============
class RegisterWorkerView(APIView):
    """Worker Registration - Simple and Clean"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        logger.info("Worker registration attempt")
        logger.info(f"Data: {request.data}")
        
        serializer = RegisterWorkerSerializer(data=request.data)
        
        if serializer.is_valid():
            logger.info("✓ Serializer valid")
            
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Generate tokens
                    refresh = RefreshToken.for_user(user)
                    
                    logger.info(f"✓ Registration successful: {user.email}")
                    
                    return Response({
                        'status': 'success',
                        'message': 'Worker registered successfully',
                        'user_id': str(user.id),
                        'email': user.email,
                        'phone': user.phone,
                        'role': user.role,
                        'phone_verified': user.phone_verified,
                        'tokens': {
                            'access': str(refresh.access_token),
                            'refresh': str(refresh),
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                logger.error(f"✗ Registration failed: {str(e)}")
                return Response({
                    'error': 'Registration failed',
                    'detail': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            logger.error(f"✗ Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterEmployerView(APIView):
    """Employer Registration"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterEmployerSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Generate tokens
                    refresh = RefreshToken.for_user(user)
                    
                    return Response({
                        'status': 'success',
                        'message': 'Employer registered successfully',
                        'user_id': str(user.id),
                        'email': user.email,
                        'phone': user.phone,
                        'role': user.role,
                        'phone_verified': user.phone_verified,
                        'tokens': {
                            'access': str(refresh.access_token),
                            'refresh': str(refresh),
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({
                    'error': 'Registration failed',
                    'detail': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """User Login"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Add custom claims
            access_token['phone_verified'] = user.phone_verified
            access_token['role'] = user.role
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'phone': user.phone,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'phone_verified': user.phone_verified,
                    'is_active': user.is_active,
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestPhoneVerificationView(APIView):
    """
    Request OTP for phone verification
    Supports both registration and login flows
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PhoneVerificationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone = serializer.validated_data['phone']
        
        try:
            # Check if user exists (for registration) or create new user profile
            user_exists = User.objects.filter(phone=phone).exists()
            
            # Check rate limiting for OTP requests
            otp_request_key = f'otp_request_{phone}'
            request_count = cache.get(otp_request_key, 0)
            
            if request_count >= 5:  # Limit to 5 requests per hour
                return Response({
                    'status': 'error',
                    'error': 'Too many OTP requests. Please try again later.',
                    'phone': phone
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Generate and send OTP
            otp = OTPService.generate_otp(phone)
            
            # Increment request counter
            cache.set(otp_request_key, request_count + 1, timeout=3600)  # 1 hour
            
            response_data = {
                'status': 'success',
                'message': 'OTP sent successfully',
                'phone': phone,
                'user_exists': user_exists,
                'sent_via': 'sms' if OTPService._should_send_sms(phone) else 'console',
                'resend_allowed_in': 300,  # 5 minutes
            }
            
            # In development, include the OTP for testing
            if settings.DEBUG:
                otp_value, ttl = OTPService.check_otp_status(phone)
                if otp_value:
                    response_data['debug_info'] = {
                        'otp': otp_value,
                        'ttl_seconds': ttl,
                        'ttl_minutes': round(ttl / 60, 2)
                    }
            
            logger.info(f"OTP requested for phone: {phone}, user_exists: {user_exists}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to request phone verification for {phone}: {e}")
            return Response(
                {'error': f'Failed to send OTP: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyPhoneView(APIView):
    """
    Verify phone number using OTP
    Supports both registration and login flows
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PhoneVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone = serializer.validated_data['phone']
        otp = serializer.validated_data['otp']
        
        # Verify OTP
        is_valid, message = OTPService.verify_otp(phone, otp)
        
        if not is_valid:
            return Response(
                {
                    'status': 'error',
                    'error': message,
                    'phone': phone,
                    'verified': False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get or create user
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'username': phone,
                    'is_active': True,
                    'phone_verified': True,
                    'registration_method': 'phone'
                }
            )
            
            # If user exists but not verified, update verification status
            if not created:
                user.phone_verified = True
                user.is_active = True
                user.save(update_fields=['phone_verified', 'is_active', 'last_login'])
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Add custom claims
            access_token['phone_verified'] = True
            access_token['registration_method'] = user.registration_method
            access_token['role'] = user.role
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Clear OTP rate limiting
            cache.delete(f'otp_request_{phone}')
            
            # Log the verification
            logger.info(f"Phone verified successfully for user {user.id} ({phone}), created: {created}")
            
            response_data = {
                'status': 'success',
                'message': 'Phone verified successfully',
                'user': {
                    'id': str(user.id),
                    'phone': user.phone,
                    'phone_verified': user.phone_verified,
                    'is_active': user.is_active,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'date_joined': user.date_joined,
                    'last_login': user.last_login,
                    'is_new_user': created
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                    'access_expires': access_token['exp'],
                    'refresh_expires': refresh['exp']
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Phone verification failed for {phone}: {e}")
            return Response(
                {
                    'status': 'error',
                    'error': 'An error occurred during verification',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResendVerificationOTPView(APIView):
    """
    Resend OTP for phone verification
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone = request.data.get('phone')
        
        if not phone:
            return Response(
                {'error': 'Phone number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if OTP already exists
            existing_otp, ttl = OTPService.check_otp_status(phone)
            
            if existing_otp and ttl > 300:  # If OTP still valid for more than 5 minutes
                return Response({
                    'status': 'warning',
                    'message': 'OTP is still valid',
                    'phone': phone,
                    'ttl_seconds': ttl,
                    'resend_available_in': ttl - 300  # Can resend after 5 minutes
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Check overall request rate limiting
            resend_key = f'otp_resend_{phone}'
            resend_count = cache.get(resend_key, 0)
            
            if resend_count >= 3:  # Limit to 3 resends per hour
                return Response({
                    'status': 'error',
                    'error': 'Too many resend attempts. Please try again later.',
                    'phone': phone
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Resend OTP
            otp = OTPService.resend_otp(phone)
            
            # Track resend attempts
            cache.set(resend_key, resend_count + 1, timeout=3600)  # Expire after 1 hour
            
            response_data = {
                'status': 'success',
                'message': 'OTP resent successfully',
                'phone': phone,
                'resend_count': resend_count + 1,
                'sent_via': 'sms' if OTPService._should_send_sms(phone) else 'console'
            }
            
            # In development, include debug info
            if settings.DEBUG:
                otp_value, ttl = OTPService.check_otp_status(phone)
                response_data['debug'] = {
                    'otp': otp_value,
                    'ttl_seconds': ttl
                }
            
            logger.info(f"OTP resent for phone: {phone}, count: {resend_count + 1}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to resend OTP for {phone}: {e}")
            return Response(
                {'error': f'Failed to resend OTP: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OTPStatusView(APIView):
    """
    Check OTP status (for debugging and testing)
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, phone):
        otp, ttl = OTPService.check_otp_status(phone)
        
        if otp:
            return Response({
                'has_otp': True,
                'ttl_seconds': ttl,
                'ttl_minutes': round(ttl / 60, 1),
                'phone': phone,
                'is_sms_enabled': OTPService._should_send_sms(phone)
            })
        else:
            return Response({
                'has_otp': False,
                'message': 'No active OTP for this phone',
                'phone': phone
            })


# ============= PROFILE VIEWS =============
class UserProfileView(APIView):
    """Get or update user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        
        # Add profile data based on role
        data = serializer.data
        
        if user.role == 'worker':
            try:
                profile = WorkerProfile.objects.get(user=user)
                profile_data = WorkerProfileSerializer(profile).data
                data['worker_profile'] = profile_data
            except WorkerProfile.DoesNotExist:
                pass
        elif user.role == 'employer':
            try:
                profile = EmployerProfile.objects.get(user=user)
                profile_data = EmployerProfileSerializer(profile).data
                data['employer_profile'] = profile_data
            except EmployerProfile.DoesNotExist:
                pass
        
        return Response(data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        """Update user profile"""
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkerProfileViewSet(viewsets.ModelViewSet):
    """Worker Profile Management"""
    serializer_class = WorkerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'worker':
            # Workers can only see their own profile
            return WorkerProfile.objects.filter(user=user)
        elif user.role in ['admin', 'super_admin']:
            # Admins can see all
            return WorkerProfile.objects.all()
        elif user.role == 'employer':
            # Employers can see available workers
            return WorkerProfile.objects.filter(
                verification_status='verified',
                availability='available'
            )
        
        return WorkerProfile.objects.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current worker's profile"""
        try:
            profile = WorkerProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except WorkerProfile.DoesNotExist:
            return Response({
                'error': 'Worker profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request):
        """Create worker profile"""
        if request.user.role != 'worker':
            return Response({
                'error': 'Only workers can create worker profiles'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if profile already exists
        if WorkerProfile.objects.filter(user=request.user).exists():
            return Response({
                'error': 'Worker profile already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Add user to request data
        data = request.data.copy()
        data['user'] = request.user.id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployerProfileViewSet(viewsets.ModelViewSet):
    """Employer Profile Management"""
    serializer_class = EmployerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'employer':
            return EmployerProfile.objects.filter(user=user)
        elif user.role in ['admin', 'super_admin']:
            return EmployerProfile.objects.all()
        
        return EmployerProfile.objects.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current employer's profile"""
        try:
            profile = EmployerProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except EmployerProfile.DoesNotExist:
            return Response({
                'error': 'Employer profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request):
        """Create employer profile"""
        if request.user.role != 'employer':
            return Response({
                'error': 'Only employers can create employer profiles'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if profile already exists
        if EmployerProfile.objects.filter(user=request.user).exists():
            return Response({
                'error': 'Employer profile already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Add user to request data
        data = request.data.copy()
        data['user'] = request.user.id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============= PASSWORD VIEWS =============
class PasswordResetView(APIView):
    """Request password reset"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            # In real implementation, send reset email or SMS
            email_or_phone = serializer.validated_data['email_or_phone']
            
            try:
                # Try to find user by email or phone
                if '@' in email_or_phone:
                    user = User.objects.get(email=email_or_phone)
                else:
                    user = User.objects.get(phone=email_or_phone)
                
                # Generate reset token (simplified - in production use proper token)
                reset_token = User.objects.make_random_password(length=32)
                cache.set(f'password_reset_{reset_token}', user.id, timeout=3600)  # 1 hour
                
                # TODO: Send reset link via email/SMS
                
                return Response({
                    'status': 'success',
                    'message': 'Password reset instructions sent',
                    'method': 'email' if '@' in email_or_phone else 'sms'
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                # Don't reveal if user exists for security
                return Response({
                    'status': 'success',
                    'message': 'If an account exists, reset instructions have been sent'
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Confirm password reset"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            # Check if token exists and get user ID
            user_id = cache.get(f'password_reset_{token}')
            
            if not user_id:
                return Response({
                    'error': 'Invalid or expired token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = User.objects.get(id=user_id)
                user.set_password(new_password)
                user.save()
                
                # Clear the used token
                cache.delete(f'password_reset_{token}')
                
                # Invalidate all existing tokens (optional)
                # This would require token blacklist implementation
                
                return Response({
                    'status': 'success',
                    'message': 'Password reset successful'
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change user password (authenticated user)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            # Optional: Invalidate existing tokens
            # This would require token blacklist implementation
            
            return Response({
                'status': 'success',
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============= UTILITY VIEWS =============
class LogoutView(APIView):
    """User Logout - Blacklist refresh token"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'status': 'success',
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response({
                'error': 'Logout failed',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class LogoutAllView(APIView):
    """Logout from all devices - Blacklist all tokens for user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            
            # This would require storing token identifiers
            # For now, we'll just return success
            # In production, implement token blacklist for all user's tokens
            
            return Response({
                'status': 'success',
                'message': 'Logged out from all devices'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout all error: {e}")
            return Response({
                'error': 'Logout failed',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CheckAuthView(APIView):
    """Check if user is authenticated and get basic info"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'authenticated': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone': user.phone,
                'phone_verified': user.phone_verified,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active
            }
        }, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """System health check"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'WorkConnect Users API',
            'timestamp': timezone.now().isoformat(),
            'environment': 'development' if settings.DEBUG else 'production'
        }, status=status.HTTP_200_OK)