import json
from django.utils import timezone
from users.models import AuditLog


class AuditMiddleware:
    """Middleware to log user actions"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only log for authenticated users on POST, PUT, PATCH, DELETE
        if request.user.is_authenticated and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            self.log_action(request)
        
        return response
    
    def log_action(self, request):
        """Log user action to audit trail"""
        try:
            # Determine action type
            method_map = {
                'POST': AuditLog.Action.CREATE,
                'GET': AuditLog.Action.READ,
                'PUT': AuditLog.Action.UPDATE,
                'PATCH': AuditLog.Action.UPDATE,
                'DELETE': AuditLog.Action.DELETE,
            }
            
            action = method_map.get(request.method)
            
            if action:
                # Try to get entity info from URL or request data
                entity_type = self.get_entity_type(request)
                entity_id = self.get_entity_id(request)
                
                # Get old values (for update)
                old_values = None
                if action in [AuditLog.Action.UPDATE, AuditLog.Action.DELETE]:
                    old_values = self.get_old_values(request, entity_type, entity_id)
                
                # Get new values
                new_values = None
                if request.body and action in [AuditLog.Action.CREATE, AuditLog.Action.UPDATE]:
                    try:
                        new_values = json.loads(request.body.decode('utf-8'))
                    except:
                        new_values = str(request.body)
                
                # Create audit log
                AuditLog.objects.create(
                    user=request.user,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    old_values=old_values,
                    new_values=new_values
                )
                
        except Exception as e:
            # Don't crash the app if audit logging fails
            pass
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_entity_type(self, request):
        """Extract entity type from URL"""
        # Extract entity type from URL pattern
        path = request.path
        if '/api/v1/users/' in path:
            return 'user'
        elif '/api/v1/workers/' in path:
            return 'worker'
        elif '/api/v1/employers/' in path:
            return 'employer'
        elif '/api/v1/contracts/' in path:
            return 'contract'
        elif '/api/v1/payments/' in path:
            return 'payment'
        elif '/api/v1/jobs/' in path:
            return 'job_posting'
        return None
    
    def get_entity_id(self, request):
        """Extract entity ID from URL"""
        # This is a simple implementation
        # In a real app, you'd parse the URL more carefully
        path_parts = request.path.split('/')
        for part in path_parts:
            if len(part) == 36 and '-' in part:  # UUID format
                return part
        return None
    
    def get_old_values(self, request, entity_type, entity_id):
        """Get old values before update/delete"""
        # This would typically query the database for the current state
        # For simplicity, we'll return None
        return None
