#!/usr/bin/env python3
"""
Patch Django REST Framework to fix IPAddressField validator issue with drf-yasg.
This fixes: ValueError: not enough values to unpack (expected 2, got 1)
"""

import os
import sys
import re

def find_drf_path():
    """Find the DRF installation path."""
    try:
        import rest_framework
        return os.path.dirname(rest_framework.__file__)
    except ImportError:
        # Try to find it in site-packages
        for path in sys.path:
            drf_path = os.path.join(path, 'rest_framework')
            if os.path.exists(drf_path):
                return drf_path
    return None

def patch_drf_fields():
    """Patch DRF's fields.py file."""
    drf_path = find_drf_path()
    if not drf_path:
        print("ERROR: Could not find Django REST Framework installation.")
        return False
    
    fields_py = os.path.join(drf_path, 'fields.py')
    
    if not os.path.exists(fields_py):
        print(f"ERROR: Could not find {fields_py}")
        return False
    
    print(f"Found DRF at: {drf_path}")
    print(f"Patching: {fields_py}")
    
    # Read the file
    with open(fields_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    backup_py = fields_py + '.backup'
    with open(backup_py, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created backup: {backup_py}")
    
    # Find the problematic line
    pattern = r'(validators, error_message = ip_address_validators\(protocol, self\.unpack_ipv4\))'
    match = re.search(pattern, content)
    
    if match:
        old_line = match.group(1)
        new_line = """# Fixed: Handle validator return value for drf-yasg compatibility
        validator_result = ip_address_validators(protocol, self.unpack_ipv4)
        if isinstance(validator_result, tuple) and len(validator_result) == 2:
            validators, error_message = validator_result
        else:
            validators = validator_result
            error_message = 'Enter a valid IPv4 or IPv6 address.'"""
        
        # Replace the line
        content = content.replace(old_line, new_line)
        
        # Write the patched file
        with open(fields_py, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Successfully patched DRF fields.py")
        print("Restart your Django server for changes to take effect.")
        return True
    else:
        print("⚠️ Could not find the exact line to patch. Trying alternative search...")
        
        # Alternative search for the function
        func_pattern = r'def __init__\(self.*?ip_address_validators\(.*?\)'
        func_match = re.search(func_pattern, content, re.DOTALL)
        
        if func_match:
            # Try a broader replacement
            old_section = """    def __init__(self, protocol='both', unpack_ipv4=False, **kwargs):
        self.protocol = protocol
        self.unpack_ipv4 = unpack_ipv4
        kwargs.setdefault('allow_blank', False)
        super().__init__(**kwargs)
        validators, error_message = ip_address_validators(protocol, self.unpack_ipv4)
        self.validators.extend(validators)"""
            
            new_section = """    def __init__(self, protocol='both', unpack_ipv4=False, **kwargs):
        self.protocol = protocol
        self.unpack_ipv4 = unpack_ipv4
        kwargs.setdefault('allow_blank', False)
        super().__init__(**kwargs)
        # Fixed: Handle validator return value for drf-yasg compatibility
        validator_result = ip_address_validators(protocol, self.unpack_ipv4)
        if isinstance(validator_result, tuple) and len(validator_result) == 2:
            validators, error_message = validator_result
        else:
            validators = validator_result
            error_message = 'Enter a valid IPv4 or IPv6 address.'
        self.validators.extend(validators)"""
            
            if old_section in content:
                content = content.replace(old_section, new_section)
                
                with open(fields_py, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print("✅ Successfully patched DRF fields.py (alternative method)")
                print("Restart your Django server for changes to take effect.")
                return True
    
    print("❌ Could not patch the file. The code structure might have changed.")
    return False

def create_monkey_patch():
    """Create a monkey patch file to apply at runtime."""
    patch_code = '''"""
Monkey patch for Django REST Framework IPAddressField to fix drf-yasg compatibility.
Add this to your settings.py or wsgi.py/asgi.py file.
"""

import rest_framework.fields

# Save the original __init__ method
original_ipaddress_init = rest_framework.fields.IPAddressField.__init__

def patched_ipaddress_init(self, protocol='both', unpack_ipv4=False, **kwargs):
    """Patched __init__ for IPAddressField that handles validator return value."""
    self.protocol = protocol
    self.unpack_ipv4 = unpack_ipv4
    kwargs.setdefault('allow_blank', False)
    super(rest_framework.fields.IPAddressField, self).__init__(**kwargs)
    
    # Import here to avoid circular imports
    from rest_framework.validators import ip_address_validators
    
    # Handle validator return value
    validator_result = ip_address_validators(protocol, self.unpack_ipv4)
    if isinstance(validator_result, tuple) and len(validator_result) == 2:
        validators, error_message = validator_result
    else:
        validators = validator_result
        error_message = 'Enter a valid IPv4 or IPv6 address.'
    
    self.validators.extend(validators)

# Apply the patch
rest_framework.fields.IPAddressField.__init__ = patched_ipaddress_init

print("✅ Applied DRF IPAddressField monkey patch for drf-yasg compatibility")'''

    with open('drf_ipaddress_patch.py', 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    print("✅ Created monkey patch file: drf_ipaddress_patch.py")
    print("\nTo use it, add this to your settings.py:")
    print("    from .drf_ipaddress_patch import *")
    print("\nOr add it to your wsgi.py/asgi.py file.")

def main():
    print("=" * 60)
    print("DRF IPAddressField Patch Tool")
    print("Fixes: ValueError: not enough values to unpack (expected 2, got 1)")
    print("=" * 60)
    
    print("\nChoose an option:")
    print("1. Patch DRF library directly (requires write permissions)")
    print("2. Create monkey patch file (safer, no library modification)")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        print("\n" + "=" * 60)
        print("Patching DRF library...")
        print("=" * 60)
        if not patch_drf_fields():
            print("Consider using the monkey patch option instead.")
    
    if choice in ['2', '3']:
        print("\n" + "=" * 60)
        print("Creating monkey patch...")
        print("=" * 60)
        create_monkey_patch()
    
    if choice not in ['1', '2', '3']:
        print("Invalid choice. Exiting.")
        return

if __name__ == '__main__':
    main()