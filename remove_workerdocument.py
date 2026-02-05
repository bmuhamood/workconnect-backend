#!/usr/bin/env python
"""
Remove WorkerDocument from users/models.py
"""
import re

def remove_worker_document():
    # Read the file
    with open('users/models.py', 'r') as f:
        content = f.read()
    
    # Find the WorkerDocument class
    start = content.find('class WorkerDocument(models.Model):')
    if start == -1:
        print("WorkerDocument class not found in users/models.py")
        return False
    
    # Find the next class definition after WorkerDocument
    # Look for the next occurrence of "class " after WorkerDocument
    next_class = content.find('\nclass ', start + 1)
    
    if next_class == -1:
        # If no next class, remove everything from WorkerDocument to end
        new_content = content[:start]
    else:
        # Remove from WorkerDocument to next class
        new_content = content[:start] + content[next_class + 1:]  # +1 to keep the newline
    
    # Write back
    with open('users/models.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully removed WorkerDocument from users/models.py")
    return True

if __name__ == '__main__':
    print("Removing duplicate WorkerDocument model...")
    if remove_worker_document():
        print("\n✅ Fix applied successfully!")
        print("\nNext steps:")
        print("1. python manage.py makemigrations")
        print("2. python manage.py migrate")
        print("3. python manage.py check")
    else:
        print("\n❌ Failed to remove WorkerDocument")