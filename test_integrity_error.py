# test_integrity_error.py
import requests
import json
import sqlite3
import os

# First, let's check the database
db_path = "D:/workconnect-backend/db.sqlite3"
if os.path.exists(db_path):
    print(f"Checking database at: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if test data already exists
        cursor.execute("SELECT email, phone FROM users_user WHERE email LIKE 'test%'")
        existing = cursor.fetchall()
        
        if existing:
            print("Existing test users found:")
            for email, phone in existing:
                print(f"  - {email} ({phone})")
        else:
            print("No existing test users found")
            
        conn.close()
    except Exception as e:
        print(f"Error checking database: {e}")

print("\n" + "="*60)
print("Testing with FRESH email and phone...")
print("="*60)

# Generate unique test data
import uuid
unique_id = str(uuid.uuid4())[:8]
test_email = f"test{unique_id}@example.com"
test_phone = f"071{unique_id[-6:]}"

data = {
    "email": test_email,
    "phone": test_phone,
    "password": "TestPass123",
    "confirm_password": "TestPass123",
    "first_name": "Test",
    "last_name": "User",
    "national_id": f"CF{unique_id.replace('-', '')[:12]}XYZ",
    "date_of_birth": "1990-01-01",
    "city": "Kampala"
}

print(f"Using unique test data:")
print(f"  Email: {test_email}")
print(f"  Phone: {test_phone}")
print(f"  National ID: {data['national_id']}")

url = "http://127.0.0.1:8000/api/v1/auth/register/worker/"

try:
    print(f"\nSending POST request to: {url}")
    response = requests.post(url, json=data, timeout=30)
    
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 201:
        print("✓ SUCCESS! User registered")
        result = response.json()
        print(json.dumps(result, indent=2))
    
    elif response.status_code == 400:
        print("✗ 400 Bad Request")
        try:
            errors = response.json()
            print("Validation Errors:")
            print(json.dumps(errors, indent=2))
        except:
            print(f"Raw: {response.text[:500]}")
    
    elif response.status_code == 500:
        print("✗ 500 Internal Server Error")
        # Try to get HTML error page
        if "<!DOCTYPE html>" in response.text:
            # Extract error info from HTML
            import re
            # Look for error type
            error_match = re.search(r'<title>([^<]+)</title>', response.text)
            if error_match:
                print(f"Error Type: {error_match.group(1)}")
            
            # Look for error value
            value_match = re.search(r'<pre class="exception_value">([^<]+)</pre>', response.text)
            if value_match:
                print(f"Error: {value_match.group(1)}")
        else:
            print(f"Response: {response.text[:500]}")
    
    else:
        print(f"Unexpected Status {response.status_code}:")
        print(response.text[:500])
        
except Exception as e:
    print(f"\n✗ Request failed: {e}")