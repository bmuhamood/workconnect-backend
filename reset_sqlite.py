# reset_sqlite.py
import os
import shutil
import subprocess
import sys

def reset_database():
    print("=" * 60)
    print("Resetting Django Database (SQLite)")
    print("=" * 60)
    
    # 1. Delete SQLite database
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("✅ Deleted: db.sqlite3")
    else:
        print("ℹ️  No database file found")
    
    # 2. Delete all migration files except __init__.py
    print("\nCleaning migration files...")
    migration_dirs = 0
    for root, dirs, files in os.walk('.'):
        if 'migrations' in dirs:
            migrations_dir = os.path.join(root, 'migrations')
            if os.path.exists(migrations_dir):
                migration_dirs += 1
                for file in os.listdir(migrations_dir):
                    if file.endswith('.py') and file != '__init__.py':
                        filepath = os.path.join(migrations_dir, file)
                        os.remove(filepath)
                        print(f"  Deleted: {filepath}")
    
    print(f"✅ Cleaned {migration_dirs} migration directories")
    
    # 3. Clear Python cache
    print("\nClearing cache...")
    cache_dirs = 0
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(cache_path)
            cache_dirs += 1
    
    print(f"✅ Cleared {cache_dirs} cache directories")
    
    # 4. Create fresh migrations
    print("\n" + "=" * 60)
    print("Creating fresh migrations...")
    print("=" * 60)
    
    try:
        # Make migrations for each app
        apps = ['users', 'documents', 'contracts', 'payments', 'job_postings', 
                'matching', 'ai_services', 'reviews', 'messaging', 
                'notifications', 'analytics']
        
        for app in apps:
            if os.path.exists(app):
                print(f"\nMaking migrations for {app}...")
                result = subprocess.run(
                    ['python', 'manage.py', 'makemigrations', app],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    if "No changes detected" in result.stdout:
                        print(f"  ⚠️  No changes in {app}")
                    else:
                        print(f"  ✅ Created migrations for {app}")
                else:
                    print(f"  ❌ Failed for {app}: {result.stderr}")
        
        # 5. Apply migrations
        print("\n" + "=" * 60)
        print("Applying migrations...")
        print("=" * 60)
        
        result = subprocess.run(
            ['python', 'manage.py', 'migrate'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Migrations applied successfully!")
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
        
        # 6. Create superuser
        print("\n" + "=" * 60)
        print("Create Superuser")
        print("=" * 60)
        print("\nPlease create a superuser:")
        print("python manage.py createsuperuser")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: Please run this script from your Django project root directory")
        sys.exit(1)
    
    print("WARNING: This will delete your database and all migration files.")
    confirmation = input("Are you sure? (yes/no): ")
    
    if confirmation.lower() in ['yes', 'y']:
        if reset_database():
            print("\n" + "=" * 60)
            print("✅ Database reset complete!")
            print("\nNext steps:")
            print("1. Create superuser: python manage.py createsuperuser")
            print("2. Run server: python manage.py runserver")
            print("=" * 60)
        else:
            print("\n❌ Reset failed. Check errors above.")
    else:
        print("Operation cancelled.")