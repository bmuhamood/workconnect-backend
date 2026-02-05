# test_registration.py
import requests
import json

url = "http://127.0.0.1:8000/api/v1/auth/register/worker/"

data = {
    "email": "testworker@example.com",
    "phone": "+256712345678",
    "password": "TestPass123",
    "confirm_password": "TestPass123",
    "first_name": "Test",
    "last_name": "Worker",
    "national_id": "CF123456789012XYZ",
    "date_of_birth": "1990-01-01",
    "city": "Kampala"
}

response = requests.post(url, json=data)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")