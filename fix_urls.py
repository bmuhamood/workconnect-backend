# #!/usr/bin/env python
# """
# Script to fix URL configuration
# """
# import os
# import shutil

# def main():
#     project_root = os.getcwd()
    
#     # 1. Delete the problematic __init__.py if it exists
#     init_file = os.path.join(project_root, 'users', 'urls', '__init__.py')
#     if os.path.exists(init_file):
#         os.remove(init_file)
#         print("Removed users/urls/__init__.py")
    
#     # 2. Move URL files from users/urls/ to users/
#     urls_dir = os.path.join(project_root, 'users', 'urls')
#     users_dir = os.path.join(project_root, 'users')
    
#     if os.path.exists(urls_dir):
#         for filename in os.listdir(urls_dir):
#             if filename.endswith('.py') and filename != '__init__.py':
#                 src = os.path.join(urls_dir, filename)
#                 dst = os.path.join(users_dir, filename)
#                 shutil.move(src, dst)
#                 print(f"Moved {filename} to users/")
        
#         # Remove empty directory
#         try:
#             os.rmdir(urls_dir)
#             print("Removed empty users/urls directory")
#         except OSError:
#             print("Could not remove users/urls directory (not empty)")
    
#     # 3. Create consolidated urls.py
#     consolidated_content = '''
# """
# Consolidated users URLs
# """
# from django.urls import path
# from rest_framework.routers import SimpleRouter

# # Import all views
# from users.views.auth_views import (
#     RegisterEmployerView, RegisterWorkerView, VerifyPhoneView,
#     ResendOTPView, LoginView, LogoutView, PasswordResetView,
#     PasswordResetConfirmView, ChangePasswordView
# )
# from users.views.admin_views import (
#     AdminUserViewSet, AdminWorkerViewSet,
#     AdminVerificationViewSet, AdminAuditLogViewSet
# )
# from users.views.employer_views import EmployerProfileViewSet
# from users.views.worker_views import (
#     WorkerProfileViewSet, WorkerSkillViewSet,
#     WorkerDocumentViewSet, WorkerReferenceViewSet
# )
# from users.views.user_views import UserProfileView, UserDashboardView

# # Create router
# router = SimpleRouter()

# # Register all ViewSets
# router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
# router.register(r'admin/workers', AdminWorkerViewSet, basename='admin-workers')
# router.register(r'admin/verifications', AdminVerificationViewSet, basename='admin-verifications')
# router.register(r'admin/audit-logs', AdminAuditLogViewSet, basename='admin-audit-logs')
# router.register(r'employers/profile', EmployerProfileViewSet, basename='employer-profile')
# router.register(r'workers/profile', WorkerProfileViewSet, basename='worker-profile')
# router.register(r'workers/skills', WorkerSkillViewSet, basename='worker-skills')
# router.register(r'workers/documents', WorkerDocumentViewSet, basename='worker-documents')
# router.register(r'workers/references', WorkerReferenceViewSet, basename='worker-references')

# app_name = 'users'

# urlpatterns = [
#     # Router URLs
#     *router.urls,
    
#     # Authentication
#     path('auth/register/employer/', RegisterEmployerView.as_view(), name='register-employer'),
#     path('auth/register/worker/', RegisterWorkerView.as_view(), name='register-worker'),
#     path('auth/verify-phone/', VerifyPhoneView.as_view(), name='verify-phone'),
#     path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
#     path('auth/login/', LoginView.as_view(), name='login'),
#     path('auth/logout/', LogoutView.as_view(), name='logout'),
#     path('auth/password-reset/', PasswordResetView.as_view(), name='password-reset'),
#     path('auth/password-reset/confirm/<str:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
#     path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    
#     # User profile
#     path('profile/', UserProfileView.as_view(), name='user-profile'),
    
#     # Dashboards
#     path('employers/dashboard/', UserDashboardView.as_view(), name='employer-dashboard'),
#     path('workers/dashboard/', UserDashboardView.as_view(), name='worker-dashboard'),
# ]
# '''
    
#     # Write consolidated urls.py
#     urls_file = os.path.join(users_dir, 'urls.py')
#     with open(urls_file, 'w') as f:
#         f.write(consolidated_content)
#     print("Created consolidated users/urls.py")
    
#     # 4. Create simplified workconnect/urls.py
#     workconnect_urls = '''
# """
# Simplified URL configuration
# """
# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     # Admin
#     path('admin/', admin.site.urls),
    
#     # API endpoints
#     path('api/v1/', include('users.urls')),
# ]

# # Serve media files
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# '''
    
#     workconnect_file = os.path.join(project_root, 'workconnect', 'urls.py')
#     with open(workconnect_file, 'w') as f:
#         f.write(workconnect_urls)
#     print("Created simplified workconnect/urls.py")
    
#     print("\n✅ Fix completed! Run: python manage.py check")

# if __name__ == '__main__':
#     main()  