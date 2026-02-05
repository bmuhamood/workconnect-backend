from rest_framework import permissions


class IsVerifiedUser(permissions.BasePermission):
    """Check if user is verified (email and phone verified)"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified


class IsEmployer(permissions.BasePermission):
    """Check if user is an employer"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'employer'


class IsWorker(permissions.BasePermission):
    """Check if user is a worker"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'worker'


class IsAdmin(permissions.BasePermission):
    """Check if user is admin or super admin"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'super_admin']


class IsContractParty(permissions.BasePermission):
    """Check if user is a party in the contract"""
    
    def has_object_permission(self, request, view, obj):
        # Check if user is employer in contract
        if hasattr(obj, 'employer') and obj.employer.user == request.user:
            return True
        
        # Check if user is worker in contract
        if hasattr(obj, 'worker') and obj.worker.user == request.user:
            return True
        
        # Check if user is admin
        if request.user.role in ['admin', 'super_admin']:
            return True
        
        return False
