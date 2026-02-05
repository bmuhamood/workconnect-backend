# find_problematic_serializer.py
import os
import re
import ast

def analyze_serializers():
    """Find serializers that might be trying to access User fields incorrectly."""
    
    print("Searching for problematic serializers...")
    
    # Common fields that exist in profiles but not in User
    profile_fields = ['city', 'address', 'district', 'location_lat', 'location_lng', 
                      'company_name', 'bio', 'experience_years', 'national_id']
    
    for root, dirs, files in os.walk('.'):
        if 'venv' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('serializers.py'):
                filepath = os.path.join(root, file)
                
                print(f"\n🔍 Checking: {filepath}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file
                try:
                    tree = ast.parse(content)
                    
                    # Find all serializer classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and 'Serializer' in node.name:
                            
                            # Check if it uses User model
                            for item in node.body:
                                if isinstance(item, ast.ClassDef) and item.name == 'Meta':
                                    for meta_item in item.body:
                                        if isinstance(meta_item, ast.Assign):
                                            if len(meta_item.targets) == 1:
                                                target_name = meta_item.targets[0].id
                                                
                                                # Check model
                                                if target_name == 'model':
                                                    if isinstance(meta_item.value, ast.Name):
                                                        model_name = meta_item.value.id
                                                        if model_name == 'User':
                                                            print(f"  ⚠️ Found serializer for User model: {node.name}")
                                                            
                                                            # Check fields
                                                            for meta_item2 in item.body:
                                                                if isinstance(meta_item2, ast.Assign):
                                                                    if len(meta_item2.targets) == 1:
                                                                        if meta_item2.targets[0].id == 'fields':
                                                                            # Check if fields = '__all__'
                                                                            if isinstance(meta_item2.value, ast.Constant):
                                                                                if meta_item2.value.value == '__all__':
                                                                                    print(f"    ❗ Uses fields = '__all__' - This is likely the problem!")
                                                                            
                                                                            # Check for field list
                                                                            elif isinstance(meta_item2.value, ast.List):
                                                                                for elt in meta_item2.value.elts:
                                                                                    if isinstance(elt, ast.Constant):
                                                                                        field_name = elt.value
                                                                                        if field_name in profile_fields:
                                                                                            print(f"    ❗ Includes profile field: {field_name}")
                                                
                                                # Check extra_kwargs
                                                elif target_name == 'extra_kwargs':
                                                    print(f"    Has extra_kwargs")
                                    
                            # Check for field definitions in the class body
                            for item in node.body:
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name):
                                            field_name = target.id
                                            if field_name in profile_fields:
                                                print(f"  ⚠️ Has field definition for: {field_name}")
                                                
                                                # Try to find source
                                                if isinstance(item.value, ast.Call):
                                                    for keyword in item.value.keywords:
                                                        if keyword.arg == 'source':
                                                            if isinstance(keyword.value, ast.Constant):
                                                                source = keyword.value.value
                                                                print(f"    Source: {source}")
                                                                if source.startswith('user.') or source == 'user':
                                                                    print(f"    ❗ Problem: Trying to get {field_name} from user")
                            
                except Exception as e:
                    print(f"  Error parsing: {e}")

if __name__ == '__main__':
    analyze_serializers()