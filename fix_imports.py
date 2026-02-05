# fix_imports.py
import os
import re

def fix_admin_py(file_path):
    """Fix imports in admin.py file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if there are serializer imports in admin.py
    if "from users.serializers.admin_serializers import" in content:
        print(f"Fixing {file_path}...")
        
        # Remove the problematic import lines
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Skip the problematic import lines
            if line.strip().startswith("from users.serializers.admin_serializers import"):
                continue
            if line.strip().startswith("from users.serializers import"):
                continue
            new_lines.append(line)
        
        # Write back the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"  Fixed: Removed serializer imports from admin.py")
        return True
    
    # Check if serializers are defined in admin.py (need to add serializers import)
    if "class AdminUserSerializer" in content and "from rest_framework import serializers" not in content:
        print(f"Fixing {file_path}...")
        
        # Add serializers import at the top
        lines = content.split('\n')
        new_lines = []
        added_import = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Add serializers import after django imports
            if not added_import and "from django" in line and i+1 < len(lines) and "from rest_framework" not in lines[i+1]:
                new_lines.append("from rest_framework import serializers")
                added_import = True
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"  Fixed: Added serializers import to admin.py")
        return True
    
    return False

def fix_admin_views_py(file_path):
    """Fix imports in admin_views.py file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the problematic import
    if "import serializers" in content and "from rest_framework import serializers" not in content:
        print(f"Fixing {file_path}...")
        
        # Replace the problematic import
        content = content.replace("import serializers", "from rest_framework import serializers")
        
        # Check if we need to add admin_serializers import
        if "from users.serializers.admin_serializers import" not in content:
            # Find where to add the import
            lines = content.split('\n')
            new_lines = []
            added_import = False
            
            for line in lines:
                new_lines.append(line)
                
                # Add the import after rest_framework imports
                if not added_import and "from rest_framework import" in line:
                    new_lines.append("\n# Import from your serializers module")
                    new_lines.append("from users.serializers.admin_serializers import (")
                    new_lines.append("    AdminUserSerializer, AdminWorkerSerializer,")
                    new_lines.append("    VerificationSerializer, AuditLogSerializer")
                    new_lines.append(")")
                    added_import = True
            
            content = '\n'.join(new_lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Fixed: Updated imports in admin_views.py")
        return True
    
    return False

def create_admin_serializers_file(serializers_dir):
    """Create the missing admin_serializers.py file"""
    file_path = os.path.join(serializers_dir, "admin_serializers.py")
    
    if not os.path.exists(file_path):
        print(f"Creating {file_path}...")
        
        content = '''# users/serializers/admin_serializers.py
from rest_framework import serializers
from users.models import User, WorkerProfile, EmployerProfile, Verification, AuditLog


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management"""
    
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'last_login']


class AdminWorkerSerializer(serializers.ModelSerializer):
    """Serializer for admin worker management"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    
    class Meta:
        model = WorkerProfile
        fields = '__all__'


class VerificationSerializer(serializers.ModelSerializer):
    """Serializer for verification management"""
    
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    verified_by_email = serializers.EmailField(source='verified_by.email', read_only=True)
    
    class Meta:
        model = Verification
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
'''
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Created: admin_serializers.py")
        return True
    
    return False

def clear_pycache():
    """Clear all .pyc files and __pycache__ directories"""
    print("Clearing cache files...")
    
    for root, dirs, files in os.walk('.'):
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                try:
                    os.remove(os.path.join(root, file))
                    print(f"  Removed: {os.path.join(root, file)}")
                except:
                    pass
        
        # Remove __pycache__ directories
        if '__pycache__' in dirs:
            try:
                import shutil
                shutil.rmtree(os.path.join(root, '__pycache__'))
                print(f"  Removed: {os.path.join(root, '__pycache__')}")
            except:
                pass

def main():
    print("=" * 60)
    print("AUTO FIX FOR IMPORT ERRORS")
    print("=" * 60)
    
    base_dir = os.getcwd()
    
    # 1. Clear cache files
    clear_pycache()
    print()
    
    # 2. Fix admin.py
    admin_py_path = os.path.join(base_dir, 'users', 'admin.py')
    if os.path.exists(admin_py_path):
        fix_admin_py(admin_py_path)
    else:
        print(f"Warning: {admin_py_path} not found")
    print()
    
    # 3. Fix admin_views.py
    admin_views_py_path = os.path.join(base_dir, 'users', 'views', 'admin_views.py')
    if os.path.exists(admin_views_py_path):
        fix_admin_views_py(admin_views_py_path)
    else:
        print(f"Warning: {admin_views_py_path} not found")
    print()
    
    # 4. Create admin_serializers.py if it doesn't exist
    serializers_dir = os.path.join(base_dir, 'users', 'serializers')
    if os.path.exists(serializers_dir):
        create_admin_serializers_file(serializers_dir)
    else:
        print(f"Warning: {serializers_dir} not found")
    print()
    
    # 5. Check for other common issues
    print("Checking for other common issues...")
    
    # Check for circular imports in documents/models.py
    documents_models_path = os.path.join(base_dir, 'documents', 'models.py')
    if os.path.exists(documents_models_path):
        with open(documents_models_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for circular import
        if "from documents.models import" in content:
            print(f"  Warning: Possible circular import in {documents_models_path}")
            print(f"  You may need to manually remove: 'from documents.models import ...'")
    
    print("\n" + "=" * 60)
    print("FIX COMPLETED!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python manage.py makemigrations")
    print("2. Run: python manage.py migrate")
    print("3. Run: python manage.py runserver")
    print("\nIf you still have issues, check:")
    print("- documents/models.py for circular imports")
    print("- All import statements in your views")
    print("- Make sure all required files exist")

if __name__ == "__main__":
    main()