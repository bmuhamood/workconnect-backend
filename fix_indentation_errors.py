# fix_indentation_errors.py
import os
import re

def fix_file_indentation(file_path):
    """Fix indentation errors in a Python file"""
    print(f"\nChecking {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Track indentation levels
    fixed_lines = []
    issues_found = 0
    
    for i, line in enumerate(lines, 1):
        original_line = line
        
        # Check for common indentation errors
        if line.strip().startswith('swagger_fake_view ='):
            # This should be a class attribute, not at module level
            if not line.startswith('    '):
                print(f"  Line {i}: Fixing indentation for 'swagger_fake_view'")
                line = '    ' + line.lstrip()
                issues_found += 1
        
        # Check for mixed tabs and spaces
        if '\t' in line:
            print(f"  Line {i}: Found tabs, converting to spaces")
            line = line.replace('\t', '    ')
            issues_found += 1
        
        # Check for inconsistent indentation
        if line.strip() and not line.startswith(' ') and not line.startswith('#') and not line.startswith('\n'):
            # This line should be indented if it's inside a class/method
            pass
        
        fixed_lines.append(line)
    
    if issues_found > 0:
        # Write back the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print(f"  Fixed {issues_found} issues in {file_path}")
        return True
    else:
        print(f"  No issues found in {file_path}")
        return False

def create_correct_employer_views():
    """Create a correct version of employer_views.py"""
    content = '''# users/views/employer_views.py
from django.contrib.auth.models import AnonymousUser
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import EmployerProfile, User
from users.serializers.employer_serializers import (
    EmployerProfileSerializer, EmployerProfileUpdateSerializer
)
from users.permissions import IsEmployer, IsVerifiedUser


class EmployerProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for employer profiles"""
    
    queryset = EmployerProfile.objects.all()
    serializer_class = EmployerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    
    # Swagger schema generation fix
    swagger_fake_view = False
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsVerifiedUser()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsVerifiedUser(), IsEmployer()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return EmployerProfile.objects.none()
            
        user = self.request.user
        
        # Handle AnonymousUser (for Swagger/API docs)
        if isinstance(user, AnonymousUser):
            return EmployerProfile.objects.none()
            
        if user.role == User.Role.EMPLOYER:
            # Employers can only see their own profile
            return EmployerProfile.objects.filter(user=user)
        elif user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]:
            # Admins can see all profiles
            return EmployerProfile.objects.all()
        
        return EmployerProfile.objects.none()
    
    def get_serializer_class(self):
        """Use different serializer for update"""
        if self.action in ['update', 'partial_update']:
            return EmployerProfileUpdateSerializer
        return self.serializer_class
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current employer's profile"""
        user = request.user
        try:
            profile = user.employer_profile
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except EmployerProfile.DoesNotExist:
            return Response(
                {'error': 'Employer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
'''
    
    file_path = os.path.join('users', 'views', 'employer_views.py')
    
    # Backup original file
    if os.path.exists(file_path):
        backup_path = file_path + '.backup'
        with open(file_path, 'r', encoding='utf-8') as f:
            original = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original)
        print(f"Created backup: {backup_path}")
    
    # Write correct version
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Created correct employer_views.py")
    return True

def check_all_view_files():
    """Check all view files for indentation issues"""
    print("=" * 60)
    print("CHECKING ALL VIEW FILES FOR INDENTATION ISSUES")
    print("=" * 60)
    
    view_files = []
    
    # Find all view files
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py') and 'views' in root.lower():
                # Skip backup files
                if not file.endswith('.backup'):
                    file_path = os.path.join(root, file)
                    view_files.append(file_path)
    
    total_issues = 0
    for file_path in view_files:
        if fix_file_indentation(file_path):
            total_issues += 1
    
    print(f"\nTotal files with issues: {total_issues}")
    return total_issues

def validate_python_syntax(file_path):
    """Check if a Python file has valid syntax"""
    import ast
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"  Syntax error in {file_path}:")
        print(f"    Line {e.lineno}: {e.msg}")
        if e.text:
            print(f"    Text: {e.text.strip()}")
        return False
    except Exception as e:
        print(f"  Error checking {file_path}: {e}")
        return False

def create_indentation_fix_script():
    """Create a script to automatically fix indentation in all Python files"""
    script_content = '''# auto_fix_indentation.py
import os
import re
import sys

def fix_file(file_path):
    """Fix indentation in a single file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix common indentation patterns
    fixes = []
    
    # Fix 1: swagger_fake_view indentation (should be inside class)
    if 'swagger_fake_view =' in content and 'class' in content:
        # Find class definition
        lines = content.split('\\n')
        in_class = False
        class_indent = ''
        new_lines = []
        
        for line in lines:
            # Check if we're entering a class
            if line.strip().startswith('class ') and line.strip().endswith(':'):
                in_class = True
                # Get class indentation
                match = re.match(r'(\\s*)', line)
                class_indent = match.group(1) if match else ''
            
            # Fix swagger_fake_view if it's at wrong indentation
            if 'swagger_fake_view =' in line and in_class:
                # Should be indented one level more than class
                correct_indent = class_indent + '    '
                if not line.startswith(correct_indent):
                    line = correct_indent + line.lstrip()
                    fixes.append(f"Fixed swagger_fake_view indentation")
            
            new_lines.append(line)
        
        content = '\\n'.join(new_lines)
    
    # Fix 2: Convert tabs to spaces (4 spaces per tab)
    if '\\t' in content:
        old_tabs = content.count('\\t')
        content = content.replace('\\t', '    ')
        fixes.append(f"Converted {old_tabs} tabs to spaces")
    
    # Fix 3: Remove trailing whitespace
    lines = content.split('\\n')
    new_lines = []
    for line in lines:
        new_lines.append(line.rstrip())
    content = '\\n'.join(new_lines)
    
    if fixes:
        print(f"Fixed {file_path}:")
        for fix in fixes:
            print(f"  - {fix}")
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    """Main function"""
    print("Auto-fixing indentation issues...")
    
    # Get all Python files
    python_files = []
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root or '.git' in root:
            continue
        
        for file in files:
            if file.endswith('.py') and not file.endswith('.backup'):
                python_files.append(os.path.join(root, file))
    
    total_fixed = 0
    for file_path in python_files:
        if fix_file(file_path):
            total_fixed += 1
    
    print(f"\\nTotal files fixed: {total_fixed}")
    
    if total_fixed > 0:
        print("\\nPlease restart your Django server.")
    else:
        print("\\nNo files needed fixing.")

if __name__ == "__main__":
    main()
'''
    
    with open('auto_fix_indentation.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("Created auto_fix_indentation.py")
    print("Run: python auto_fix_indentation.py")
    
    return 'auto_fix_indentation.py'

def main():
    """Main function"""
    print("=" * 60)
    print("FIXING INDENTATION ERRORS")
    print("=" * 60)
    
    print("\nOptions:")
    print("1. Fix employer_views.py only (quick fix)")
    print("2. Check all view files")
    print("3. Create auto-fix script")
    print("4. Do all of the above")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice in ['1', '4']:
        print("\n" + "=" * 60)
        print("FIXING employer_views.py")
        print("=" * 60)
        create_correct_employer_views()
        
        # Validate the fix
        file_path = os.path.join('users', 'views', 'employer_views.py')
        if validate_python_syntax(file_path):
            print("✓ employer_views.py syntax is now correct!")
        else:
            print("✗ Still has syntax errors")
    
    if choice in ['2', '4']:
        check_all_view_files()
    
    if choice in ['3', '4']:
        create_indentation_fix_script()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    
    print("\n1. Clear cache files:")
    print("   Windows: del /s *.pyc && rmdir /s /q __pycache__")
    print("   Linux/Mac: find . -name \"*.pyc\" -delete && find . -name \"__pycache__\" -type d -exec rm -rf {} +")
    
    print("\n2. Restart Django server:")
    print("   python manage.py runserver")
    
    print("\n3. If still having issues, check:")
    print("   - All view files for proper indentation")
    print("   - No tabs (use spaces instead)")
    print("   - Consistent 4-space indentation")

if __name__ == "__main__":
    main()