import logging

import requests

logger = logging.getLogger(__name__)

response = requests.post(
    "http://localhost:8081/start-scraping",
    json={"job_title": "software engineer", "location": "sydney", "max_pages": "1"},
    timeout=10
)

logger.debug("Triggered: %s", response.status_code)
logger.debug(response.json())
