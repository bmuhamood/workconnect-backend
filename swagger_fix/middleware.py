# swagger_fix/middleware.py
"""
Middleware to fix Swagger schema generation issues
"""
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin


class SwaggerFixMiddleware(MiddlewareMixin):
    """Middleware to fix Swagger schema generation"""
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Fix AnonymousUser issues for Swagger"""
        # Check if this is a Swagger request
        if 'swagger' in request.path or 'schema' in request.path:
            # Ensure request.user is properly set for Swagger
            if hasattr(request, 'user') and isinstance(request.user, AnonymousUser):
                # Add a dummy attribute to prevent errors
                if not hasattr(request.user, 'role'):
                    request.user.role = None
                if not hasattr(request.user, 'is_verified'):
                    request.user.is_verified = False
