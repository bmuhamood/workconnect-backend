# swagger_fix/generators.py
"""
Custom Swagger generator to handle problematic endpoints
"""
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework.permissions import AllowAny


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    """Custom auto schema to handle problematic endpoints"""
    
    def get_operation(self, operation_keys):
        """Override to handle errors gracefully"""
        try:
            return super().get_operation(operation_keys)
        except Exception as e:
            # Log the error but continue
            print(f"Swagger schema generation error for {operation_keys}: {e}")
            
            # Return a basic operation
            from drf_yasg.openapi import Operation, Parameter
            return Operation(
                operation_id='_'.join(operation_keys),
                description='Endpoint with schema generation issues',
                responses={},
                parameters=[],
                tags=list(operation_keys[:-1])
            )


class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    """Custom generator to skip problematic endpoints"""
    
    def get_schema(self, request=None, public=False):
        """Override to handle errors"""
        schema = super().get_schema(request, public)
        
        # Remove problematic endpoints if needed
        problematic_paths = []
        for path, path_obj in schema.paths.items():
            for method, operation in path_obj.operations.items():
                if hasattr(operation, 'operation_id') and '_error' in operation.operation_id:
                    problematic_paths.append(path)
        
        for path in problematic_paths:
            del schema.paths[path]
        
        return schema
    
    def should_include_endpoint(self, path, method, view, public):
        """Skip problematic endpoints during schema generation"""
        # Skip admin endpoints for schema generation
        if 'admin' in path or 'Admin' in str(view):
            return False
        
        # Skip endpoints that require authentication if user is anonymous
        if hasattr(view, 'permission_classes'):
            permissions = [perm() for perm in view.permission_classes]
            if not any(isinstance(perm, AllowAny) for perm in permissions):
                if not request or not request.user or request.user.is_anonymous:
                    return False
        
        return super().should_include_endpoint(path, method, view, public)
