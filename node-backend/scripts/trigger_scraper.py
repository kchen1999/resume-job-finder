import requests

response = requests.post(
    "http://localhost:8000/start-scraping",
    json={"job_title": "software engineer", "location": "sydney", "max_pages": "1"}
)

print("Triggered:", response.status_code)
print(response.json())
