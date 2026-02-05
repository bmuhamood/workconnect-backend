import requests
import json

url = "http://127.0.0.1:8000/api/v1/auth/register/worker/"

# Test with different phone formats
test_cases = [
    {
        "name": "Test 1 - Simple phone",
        "data": {
            "email": "test1@example.com",
            "phone": "0712345678",
            "password": "SimplePass1",  # Simple password
            "confirm_password": "SimplePass1",
            "first_name": "Test",
            "last_name": "User",
            "national_id": "CF123456789012XYZ",
            "date_of_birth": "1990-01-01",
            "city": "Kampala"
        }
    },
    {
        "name": "Test 2 - +256 prefix",
        "data": {
            "email": "test2@example.com",
            "phone": "+256712345678",
            "password": "SimplePass1",
            "confirm_password": "SimplePass1",
            "first_name": "Test",
            "last_name": "User",
            "national_id": "CF123456789012XYZ",
            "date_of_birth": "1990-01-01",
            "city": "Kampala"
        }
    },
    {
        "name": "Test 3 - 256 prefix",
        "data": {
            "email": "test3@example.com",
            "phone": "256712345678",
            "password": "SimplePass1",
            "confirm_password": "SimplePass1",
            "first_name": "Test",
            "last_name": "User",
            "national_id": "CF123456789012XYZ",
            "date_of_birth": "1990-01-01",
            "city": "Kampala"
        }
    }
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"Testing: {test['name']}")
    print(f"Phone: {test['data']['phone']}")
    
    try:
        response = requests.post(url, json=test['data'], timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print("400 Bad Request - Errors:")
            try:
                errors = response.json()
                print(json.dumps(errors, indent=2))
            except:
                print(f"Raw response: {response.text}")
        elif response.status_code == 201:
            print("201 Created - Success!")
            print(f"Response: {response.text[:200]}")
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Request error: {e}")