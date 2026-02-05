# """users/routers.py
"""
Custom router to prevent duplicate converter registration
"""
from rest_framework.routers import SimpleRouter  # Use SimpleRouter instead of DefaultRouter


class WorkConnectRouter(SimpleRouter):
    """Custom router that manages all registrations"""
    def __init__(self):
        super().__init__()
        self.registry = []  # Store all registered routes
    
    def register_all_routes(self):
        """Register all routes from different modules"""
        # Import here to avoid circular imports
        from users.views.admin_views import (
            AdminUserViewSet, AdminWorkerViewSet,
            AdminVerificationViewSet, AdminAuditLogViewSet
        )
        from users.views.employer_views import EmployerProfileViewSet
        from users.views.worker_views import (
            WorkerProfileViewSet, WorkerSkillViewSet,
            WorkerDocumentViewSet, WorkerReferenceViewSet
        )
        
        # Clear any existing registrations
        self.registry.clear()
        
        # Register all routes with unique prefixes
        self.register(r'admin/users', AdminUserViewSet, basename='admin-users')
        self.register(r'admin/workers', AdminWorkerViewSet, basename='admin-workers')
        self.register(r'admin/verifications', AdminVerificationViewSet, basename='admin-verifications')
        self.register(r'admin/audit-logs', AdminAuditLogViewSet, basename='admin-audit-logs')
        self.register(r'employers/profile', EmployerProfileViewSet, basename='employer-profile')
        self.register(r'workers/profile', WorkerProfileViewSet, basename='worker-profile')
        self.register(r'workers/skills', WorkerSkillViewSet, basename='worker-skills')
        self.register(r'workers/documents', WorkerDocumentViewSet, basename='worker-documents')
        self.register(r'workers/references', WorkerReferenceViewSet, basename='worker-references')


# Create singleton instance
shared_router = WorkConnectRouter()