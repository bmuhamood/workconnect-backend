# debug_serializers.py
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workconnect.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Now import your models and check for serializers
from django.apps import apps
import importlib

# Find all serializer files
for app_config in apps.get_app_configs():
    app_name = app_config.name
    try:
        # Try to import serializers module
        module_name = f"{app_name}.serializers"
        module = importlib.import_module(module_name)
        
        print(f"\n=== Checking {app_name}.serializers ===")
        
        # Look for all serializer classes in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, '__name__') and 'Serializer' in attr.__name__:
                try:
                    # Try to instantiate the serializer
                    serializer = attr()
                    print(f"  ✓ {attr.__name__}: OK")
                except Exception as e:
                    print(f"  ✗ {attr.__name__}: ERROR - {e}")
                    
    except ImportError:
        continue
    except Exception as e:
        print(f"Error checking {app_name}: {e}")