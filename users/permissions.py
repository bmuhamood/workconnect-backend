# users/permissions.py
from rest_framework import permissions

class IsVerifiedUser(permissions.BasePermission):
    """Only allow verified users"""
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user has is_verified attribute
        if not hasattr(request.user, 'is_verified'):
            return False
        
        return request.user.is_verified

class IsEmployer(permissions.BasePermission):
    """Only allow employers"""
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user has role attribute
        if not hasattr(request.user, 'role'):
            return False
        
        return request.user.role == 'employer'

class IsWorker(permissions.BasePermission):
    """Only allow workers"""
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user has role attribute
        if not hasattr(request.user, 'role'):
            return False
        
        return request.user.role == 'worker'

class IsAdmin(permissions.BasePermission):
    """Only allow admin users"""
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user has role attribute
        if not hasattr(request.user, 'role'):
            return False
        
        return request.user.role in ['admin', 'super_admin']

class IsSuperAdmin(permissions.BasePermission):
    """Only allow super admin"""
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user has role attribute
        if not hasattr(request.user, 'role'):
            return False
        
        return request.user.role == 'super_admin'

class IsContractParty(permissions.BasePermission):
    """Only allow parties involved in contract"""
    def has_object_permission(self, request, view, obj):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        if hasattr(obj, 'employer') and hasattr(obj.employer, 'user') and obj.employer.user == request.user:
            return True
        
        if hasattr(obj, 'worker') and hasattr(obj.worker, 'user') and obj.worker.user == request.user:
            return True
        
        # Allow admin users
        if hasattr(request.user, 'role') and request.user.role in ['admin', 'super_admin']:
            return True
        
        return False

class IsProfileOwner(permissions.BasePermission):
    """Only allow profile owner or admin"""
    def has_object_permission(self, request, view, obj):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Check if user is admin
        if hasattr(request.user, 'role') and request.user.role in ['admin', 'super_admin']:
            return True
        
        return False

class IsDocumentOwner(permissions.BasePermission):
    """Only allow document owner or admin"""
    def has_object_permission(self, request, view, obj):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        if hasattr(obj, 'worker') and hasattr(obj.worker, 'user') and obj.worker.user == request.user:
            return True
        
        # Check if user is admin
        if hasattr(request.user, 'role') and request.user.role in ['admin', 'super_admin']:
            return True
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Others can view it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Write permissions are only allowed to the owner of the object
        # or admin users
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Allow admin users
        if hasattr(request.user, 'role') and request.user.role in ['admin', 'super_admin']:
            return True
        
        return False