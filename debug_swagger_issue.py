# debug_swagger_issue.py
import os
import sys
import django
import traceback

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workconnect.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg import openapi
from rest_framework.request import Request
from django.test import RequestFactory

# Mock a request
factory = RequestFactory()
request = factory.get('/swagger/')

# Create generator
generator = OpenAPISchemaGenerator(
    info=openapi.Info(
        title="WorkConnect API",
        default_version='v1',
        description="WorkConnect API Documentation",
    ),
    url='http://localhost:8000',
    patterns=None,
    urlconf='workconnect.urls'
)

try:
    print("Attempting to generate OpenAPI schema...")
    schema = generator.get_schema(request=request, public=True)
    print("✅ Schema generated successfully!")
except Exception as e:
    print(f"❌ Error generating schema: {e}")
    print("\n" + "="*60)
    print("Full traceback:")
    print("="*60)
    traceback.print_exc()
    
    # Try to get more specific info
    if "Field name `city` is not valid for model `User`" in str(e):
        print("\n" + "="*60)
        print("SPECIFIC ISSUE DETECTED:")
        print("="*60)
        print("Some serializer is trying to access 'city' field on User model.")
        print("\nCommon causes:")
        print("1. A serializer with source='user.city'")
        print("2. A ModelSerializer with User model and extra fields")
        print("3. Nested serializer trying to include city")
        
        # Let's check all serializers more carefully
        from django.apps import apps
        import importlib
        
        print("\n" + "="*60)
        print("Checking all serializers for 'city' references:")
        print("="*60)
        
        for app_config in apps.get_app_configs():
            app_name = app_config.name
            try:
                module_name = f"{app_name}.serializers"
                module = importlib.import_module(module_name)
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, '__name__') and 'Serializer' in attr.__name__:
                        # Get the source code
                        import inspect
                        try:
                            source = inspect.getsource(attr)
                            if 'city' in source.lower():
                                print(f"\n🔍 Found 'city' in {attr.__name__}:")
                                # Print relevant lines
                                lines = source.split('\n')
                                for i, line in enumerate(lines):
                                    if 'city' in line.lower():
                                        print(f"   Line {i+1}: {line.strip()}")
                        except:
                            pass
                            
            except ImportError:
                continue