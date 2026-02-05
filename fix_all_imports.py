#!/usr/bin/env python
"""
Script to fix WorkerDocument imports after moving from users to documents app
"""
import os
import re

def fix_imports_in_file(filepath):
    """Fix WorkerDocument imports in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file imports WorkerDocument from users.models
        if 'from users.models import' in content and 'WorkerDocument' in content:
            print(f"Fixing {filepath}...")
            
            # Pattern to find imports with WorkerDocument
            pattern = r'from users\.models import (.*?WorkerDocument.*?)(\n|$)'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                import_line = match.group(1).strip()
                # Remove WorkerDocument from the import
                new_import = import_line.replace('WorkerDocument,', '').replace(', WorkerDocument', '')
                new_import = new_import.replace('WorkerDocument', '').strip()
                
                # Clean up
                new_import = re.sub(r',\s*,', ',', new_import)  # Remove double commas
                new_import = re.sub(r'\(\s*,', '(', new_import)  # Fix opening parentheses
                new_import = re.sub(r',\s*\)', ')', new_import)  # Fix closing parentheses
                
                # If new_import is empty or just parentheses, remove it
                if new_import in ['', '()']:
                    replacement = 'from documents.models import WorkerDocument'
                else:
                    replacement = f'from users.models import {new_import}\nfrom documents.models import '
from documents.models import WorkerDocument
                
                # Replace in content
                old_text = f'from users.models import {import_line}'
                content = content.replace(old_text, replacement)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Fixed {filepath}")
                return True
    
    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
    
    return False

def main():
    print("Fixing WorkerDocument imports in all files...")
    print("=" * 60)
    
    files_to_check = [
        'users/serializers/worker_serializers.py',
        'users/views/worker_views.py',
        'users/views/admin_views.py',
        'users/serializers/admin_serializers.py',
        'users/urls/consolidated.py',
    ]
    
    # Also search for other Python files
    print("\nSearching for files with WorkerDocument imports...")
    all_py_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                # Skip virtual environment
                if 'venv' not in filepath and '__pycache__' not in filepath:
                    all_py_files.append(filepath)
    
    fixed_count = 0
    checked_count = 0
    
    for filepath in files_to_check + all_py_files[:50]:  # Check first 50 files
        if os.path.exists(filepath):
            checked_count += 1
            if fix_imports_in_file(filepath):
                fixed_count += 1
    
    print(f"\n" + "=" * 60)
    print(f"Checked {checked_count} files")
    print(f"Fixed {fixed_count} files")
    
    if fixed_count > 0:
        print("\n✅ Import fixes applied!")
        print("\nNext steps:")
        print("1. python manage.py check")
        print("2. python manage.py makemigrations")
        print("3. python manage.py migrate")
    else:
        print("\n⚠️  No files needed fixing")
        print("\nManual check needed. Run:")
        print('findstr /S "from users.models import.*WorkerDocument" *.py')

if __name__ == '__main__':
    main()