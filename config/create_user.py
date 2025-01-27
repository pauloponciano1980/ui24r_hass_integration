import requests
import json

url = "http://localhost:8123/api/onboarding/users"

payload = json.dumps({
  "client_id": "http://localhost:8123/",
  "name": "admin",
  "username": "admin",
  "password": "12345",
  "language": "en"
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)