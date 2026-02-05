# test_registration_now.py
import requests
import json
import sys

url = "http://127.0.0.1:8000/api/v1/auth/register/worker/"

# Simple test data
data = {
    "email": "testworker123@example.com",
    "phone": "0712345678",  # Simple format
    "password": "TestPass123",
    "confirm_password": "TestPass123",
    "first_name": "Test",
    "last_name": "Worker",
    "national_id": "CF123456789012XYZ",
    "date_of_birth": "1990-01-01",  # Make sure it's string
    "city": "Kampala"
}

print("Testing registration with data:")
print(json.dumps(data, indent=2))
print("\n" + "="*60)

try:
    response = requests.post(url, json=data, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 400:
        print("\n=== 400 BAD REQUEST ===")
        try:
            errors = response.json()
            print("Parsed JSON errors:")
            print(json.dumps(errors, indent=2))
        except json.JSONDecodeError:
            print("Raw response (not JSON):")
            print(response.text)
    
    elif response.status_code == 201:
        print("\n✓ SUCCESS! 201 Created")
        try:
            result = response.json()
            print(json.dumps(result, indent=2))
        except:
            print(response.text)
    
    else:
        print(f"\nResponse ({response.status_code}):")
        print(response.text[:500])
        
except Exception as e:
    print(f"\n✗ Request failed: {e}")
    import traceback
    traceback.print_exc()