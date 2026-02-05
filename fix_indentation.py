# fix_indentation.py
import os
import re

def fix_admin_py_indentation(file_path):
    """Fix indentation errors in admin.py file"""
    print(f"Fixing indentation in {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and fix the problematic line
    fixed_lines = []
    for i, line in enumerate(lines, 1):
        if i == 5 and "AdminUserSerializer" in line:
            # Check if line starts with whitespace when it shouldn't
            if line.startswith(' ') or line.startswith('\t'):
                print(f"  Found indentation error on line {i}: {line.strip()}")
                # Remove leading whitespace
                line = line.lstrip()
                print(f"  Fixed to: {line}")
        
        fixed_lines.append(line)
    
    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"  Fixed indentation issues")
    return True

def create_clean_admin_py(file_path):
    """Create a clean admin.py file without serializers"""
    print(f"Creating clean {file_path}...")
    
    content = '''# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User, EmployerProfile, WorkerProfile, JobCategory, WorkerSkill,
    Verification, WorkerReference, AuditLog
)


class UserAdmin(BaseUserAdmin):
    """Custom admin interface for User model"""
    
    list_display = ('email', 'phone', 'first_name', 'last_name', 'role', 'status', 'is_verified', 'is_active')
    list_filter = ('role', 'status', 'is_verified', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'phone', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'phone', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name')}),
        (_('Role and Status'), {'fields': ('role', 'status')}),
        (_('Verification'), {'fields': ('is_verified', 'email_verified', 'phone_verified')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important Dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login')


class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'company_name', 'city', 'id_verified', 'subscription_tier')
    list_filter = ('city', 'id_verified', 'subscription_tier')
    search_fields = ('user__email', 'user__phone', 'first_name', 'last_name', 'company_name')
    raw_id_fields = ('user',)


class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'city', 'verification_status', 
                   'availability', 'rating_average', 'trust_score')
    list_filter = ('verification_status', 'availability', 'city', 'subscription_tier')
    search_fields = ('user__email', 'user__phone', 'first_name', 'last_name', 'national_id')
    raw_id_fields = ('user',)


class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


class WorkerSkillAdmin(admin.ModelAdmin):
    list_display = ('worker', 'skill_name', 'proficiency_level', 'years_of_experience', 'is_primary')
    list_filter = ('proficiency_level', 'is_primary', 'category')
    search_fields = ('worker__first_name', 'worker__last_name', 'skill_name')
    raw_id_fields = ('worker', 'category')


class VerificationAdmin(admin.ModelAdmin):
    list_display = ('worker', 'verification_type', 'status', 'verified_by', 'verified_at')
    list_filter = ('verification_type', 'status')
    search_fields = ('worker__first_name', 'worker__last_name', 'verification_notes')
    raw_id_fields = ('worker', 'verified_by')


class WorkerReferenceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'referee_name', 'relationship', 'company_name', 'is_verified')
    list_filter = ('is_verified', 'relationship')
    search_fields = ('worker__first_name', 'worker__last_name', 'referee_name', 'referee_phone')
    raw_id_fields = ('worker', 'verified_by')


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'entity_type', 'timestamp')
    list_filter = ('action', 'entity_type', 'timestamp')
    search_fields = ('user__email', 'user__phone', 'entity_type')
    readonly_fields = ('user', 'action', 'entity_type', 'entity_id', 'ip_address', 
                      'user_agent', 'old_values', 'new_values', 'timestamp')
    date_hierarchy = 'timestamp'


# Register models
admin.site.register(User, UserAdmin)
admin.site.register(EmployerProfile, EmployerProfileAdmin)
admin.site.register(WorkerProfile, WorkerProfileAdmin)
admin.site.register(JobCategory, JobCategoryAdmin)
admin.site.register(WorkerSkill, WorkerSkillAdmin)
admin.site.register(Verification, VerificationAdmin)
admin.site.register(WorkerReference, WorkerReferenceAdmin)
admin.site.register(AuditLog, AuditLogAdmin)
'''
    
    # Backup the original file
    if os.path.exists(file_path):
        backup_path = file_path + '.backup'
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"  Created backup: {backup_path}")
    
    # Write the clean file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  Created clean admin.py")
    return True

def check_file_syntax(file_path):
    """Check if a Python file has syntax errors"""
    import ast
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"  Syntax error in {file_path}:")
        print(f"    Line {e.lineno}: {e.msg}")
        print(f"    Text: {e.text}")
        return False
    except Exception as e:
        print(f"  Error checking {file_path}: {e}")
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
                except:
                    pass
        
        # Remove __pycache__ directories
        if '__pycache__' in dirs:
            try:
                import shutil
                shutil.rmtree(os.path.join(root, '__pycache__'))
            except:
                pass

def main():
    print("=" * 60)
    print("FIXING INDENTATION ERRORS")
    print("=" * 60)
    
    base_dir = os.getcwd()
    admin_py_path = os.path.join(base_dir, 'users', 'admin.py')
    
    if not os.path.exists(admin_py_path):
        print(f"Error: {admin_py_path} not found!")
        return
    
    # 1. Clear cache files
    clear_pycache()
    print()
    
    # 2. Check current file syntax
    print("Checking current file syntax...")
    if not check_file_syntax(admin_py_path):
        print("\nFile has syntax errors. Creating clean version...")
        create_clean_admin_py(admin_py_path)
    else:
        print("File syntax is OK. Trying to fix indentation...")
        fix_admin_py_indentation(admin_py_path)
    
    print()
    
    # 3. Verify the fix worked
    print("Verifying fix...")
    if check_file_syntax(admin_py_path):
        print("✓ File syntax is now correct!")
    else:
        print("✗ Still has syntax errors. Creating clean version...")
        create_clean_admin_py(admin_py_path)
    
    print("\n" + "=" * 60)
    print("FIX COMPLETED!")
    print("=" * 60)
    
    print("\nTo run your server:")
    print("1. python manage.py makemigrations")
    print("2. python manage.py migrate")
    print("3. python manage.py runserver")

if __name__ == "__main__":
    main()