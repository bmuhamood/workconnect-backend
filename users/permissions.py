# users/permissions.py
from rest_framework import permissions

class IsVerifiedUser(permissions.BasePermission):
    """Only allow verified users"""
    def has_permission(self, request, view):
        return request.user.is_verified

class IsEmployer(permissions.BasePermission):
    """Only allow employers"""
    def has_permission(self, request, view):
        return request.user.role == 'employer'

class IsWorker(permissions.BasePermission):
    """Only allow workers"""
    def has_permission(self, request, view):
        return request.user.role == 'worker'

class IsAdmin(permissions.BasePermission):
    """Only allow admin users"""
    def has_permission(self, request, view):
        return request.user.role in ['admin', 'super_admin']

class IsSuperAdmin(permissions.BasePermission):
    """Only allow super admin"""
    def has_permission(self, request, view):
        return request.user.role == 'super_admin'

class IsContractParty(permissions.BasePermission):
    """Only allow parties involved in contract"""
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'employer') and obj.employer.user == request.user:
            return True
        if hasattr(obj, 'worker') and obj.worker.user == request.user:
            return True
        return False

class IsProfileOwner(permissions.BasePermission):
    """Only allow profile owner or admin"""
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if request.user.role in ['admin', 'super_admin']:
            return True
        return False

class IsDocumentOwner(permissions.BasePermission):
    """Only allow document owner or admin"""
    def has_object_permission(self, request, view, obj):
        if obj.worker.user == request.user:
            return True
        if request.user.role in ['admin', 'super_admin']:
            return True
        return False