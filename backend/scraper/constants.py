DAY_RANGE_LIMIT = 7
TOTAL_JOBS_PER_PAGE = 22
MAX_RETRIES = 3
SUCCESS = "success"
TERMINATE = "terminate" 
SKIPPED = "skipped"
ERROR = "error"
CONCURRENT_JOBS_NUM = 4
POSTED_TIME_SELECTOR = "x3iy8f0 o3fpgs4z _1i66rlw0 _1i66rlw1 _1i66rlw22 _1g0tbpc4 _1i66rlw7"
JOB_METADATA_FIELDS = {
    "location": "job-detail-location",
    "classification": "job-detail-classifications",
    "work_type": "job-detail-work-type",
    "salary": "job-detail-salary",
    "title": "job-detail-title",
    "company": "advertiser-name"
}
BROWSER_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36" 
}
LOGO_SELECTOR = 'div[data-testid="bx-logo-image"] img'
REQUIRED_FIELDS = ["title", "company", "classification", "posted_date", "posted_within", "work_type", "work_model"]
NON_REQUIRED_FIELDS = ["description", "logo_link", "location", "location_search", "experience_level", "salary", "quick_apply_url", "job_url"]
ALLOWED_WORK_MODEL_VALUES = {"Remote", "Hybrid", "On-site"}
ALLOWED_EXPERIENCE_LEVEL_VALUES = ["intern", "junior", "mid_or_senior", "lead+"]
URL_FIELDS = ["quick_apply_url", "job_url"]
LIST_FIELDS = ["responsibilities", "requirements", "other"]
OPTIONAL_FIELDS = ["logo_link", "salary"]
REQUIRED_JOB_METADATA_FIELDS = ["location", "classification", "work_type", "title", "company", "posted_date"]
FALLBACK_WORK_MODEL = "On-site"
FALLBACK_EXPERIENCE_LEVEL = "mid_or_senior"
FALLBACK_POSTED_WITHIN = "Today"

