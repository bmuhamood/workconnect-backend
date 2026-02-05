# fix_worker_document_imports.py
import os
import re

def fix_worker_serializers():
    """Fix users/serializers/worker_serializers.py"""
    filepath = 'users/serializers/worker_serializers.py'
    
    if not os.path.exists(filepath):
        print(f"❌ {filepath} not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    print(f"Fixing {filepath}...")
    
    # Replace import from users.models to documents.models
    old_import = "from users.models import WorkerProfile, WorkerSkill,  WorkerReference"
from documents.models import WorkerDocument
    new_import = """from users.models import WorkerProfile, WorkerSkill, WorkerReference
from documents.models import WorkerDocument"""
    
    content = content.replace(old_import, new_import)
    
    # Also handle other variations
    content = re.sub(
        r'from users\.models import.*WorkerDocument.*',
        'from documents.models import WorkerDocument',
        content
    )
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {filepath}")
    return True

def find_all_imports():
    """Find all files importing WorkerDocument from users"""
    print("\nSearching for other imports...")
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'from users.models import' in content and 'WorkerDocument' in content:
                            print(f"⚠️  {filepath} imports WorkerDocument from users.models")
                except:
                    pass
    
    print("\n✅ Import search complete")

def main():
    print("=" * 60)
    print("Fixing WorkerDocument import errors")
    print("=" * 60)
    
    if fix_worker_serializers():
        find_all_imports()
        
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("1. Check other serializer files")
        print("2. Check view files")
        print("3. Run: python manage.py check")
        print("=" * 60)

if __name__ == '__main__':
    main()