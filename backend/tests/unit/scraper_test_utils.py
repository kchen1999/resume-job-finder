import pytest
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from freezegun import freeze_time
from scraper.utils import extract_total_job_count, extract_job_urls, parse_job_json_from_markdown, is_job_within_date_range, get_relative_posted_time, flatten_field, extract_job_metadata_fields, pause_briefly
from scraper.utils import extract_job_links, process_markdown_to_job_links, extract_json_from_response, clean_string, get_posted_date, enrich_job_json, extract_posted_date_by_class, extract_logo_src
from scraper.utils import LOGO_SELECTOR
from tests.data.sample_job_json_strings import VALID_JSON_STRING, MALFORMED_JSON_STRING

@pytest.mark.asyncio
@patch("scraper.utils.asyncio.sleep", new_callable=AsyncMock)
@patch("scraper.utils.random.uniform", return_value=0.3)
async def test_pause_briefly_default(mock_uniform, mock_sleep):
    await pause_briefly() 
    mock_uniform.assert_called_once_with(0.2, 0.6)
    mock_sleep.assert_awaited_once_with(0.3)

@pytest.mark.asyncio
@patch("scraper.utils.asyncio.sleep", new_callable=AsyncMock)
@patch("scraper.utils.random.uniform", return_value=1.5)
async def test_pause_briefly_with_range(mock_uniform, mock_sleep):
    await pause_briefly(1, 2.5) 
    mock_uniform.assert_called_once_with(1, 2.5)
    mock_sleep.assert_awaited_once_with(1.5)

@freeze_time("2024-05-08")
def test_get_posted_date():
    assert get_posted_date(0) == "08/05/2024"
    assert get_posted_date(1) == "07/05/2024"
    assert get_posted_date(7) == "01/05/2024"
    assert get_posted_date(30) == "08/04/2024"

@pytest.mark.asyncio
@patch("scraper.utils.asyncio.sleep", new_callable=AsyncMock)
async def test_extract_logo_src_found(mock_sleep):
    mock_logo_element = MagicMock()
    mock_logo_element.get_attribute = AsyncMock(return_value="https://image-service-cdn.seek.com.au/1a2b3c4d5e6f")
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=mock_logo_element)

    result = await extract_logo_src(mock_page)

    assert result == "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f"
    mock_page.query_selector.assert_awaited_once_with(LOGO_SELECTOR)
    mock_logo_element.get_attribute.assert_awaited_once_with('src')
    mock_sleep.assert_awaited() 

@pytest.mark.asyncio
@patch("scraper.utils.asyncio.sleep", new_callable=AsyncMock)
async def test_extract_logo_src_not_found(mock_sleep):
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=None)
    result = await extract_logo_src(mock_page)

    assert result == ""
    mock_page.query_selector.assert_awaited_once_with(LOGO_SELECTOR)
    mock_sleep.assert_awaited()

@pytest.mark.asyncio
@patch("scraper.utils.random.random", return_value=0.9)
async def test_extract_job_metadata_fields_success(mock_random):
    mock_page = MagicMock()
    mock_elem_1 = MagicMock()
    mock_elem_1.inner_text = AsyncMock(return_value=" Software Engineer ")
    mock_elem_2 = MagicMock()
    mock_elem_2.inner_text = AsyncMock(return_value=" Google ")
    mock_page.query_selector = AsyncMock(side_effect=[mock_elem_1, mock_elem_2])

    job_metadata_fields = {
        "job_title": "job-detail-title",
        "company": "advertiser-name"
    }
    result = await extract_job_metadata_fields(mock_page, job_metadata_fields)
    assert result == {
        "job_title": "Software Engineer",
        "company": "Google"
    }

@pytest.mark.asyncio
@patch("scraper.utils.random.random", return_value=0.9)
async def test_extract_job_metadata_fields_element_missing(mock_random):
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=None) 
    job_metadata_fields = {"location": "job-detail-location"}

    result = await extract_job_metadata_fields(mock_page, job_metadata_fields)
    assert result == {"location": ""}

@pytest.mark.asyncio
@patch("scraper.utils.random.random", return_value=0.9)
async def test_extract_job_metadata_fields_with_exception(mock_random):
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(side_effect=Exception("query error"))
    job_metadata_fields = {"location": "job-detail-location"}

    result = await extract_job_metadata_fields(mock_page, job_metadata_fields)
    assert result == {"location": ""}

@pytest.mark.asyncio
@patch("scraper.utils.get_posted_date", return_value="05/05/2024")  
@patch("scraper.utils.random.random", return_value=0.9)   
async def test_extract_posted_date_by_class_with_days(mock_random, mock_get_posted_date):
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Posted 3d ago")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted-time")
    assert result == "05/05/2024"
    mock_get_posted_date.assert_called_once_with(3)

@pytest.mark.asyncio
@patch("scraper.utils.get_posted_date", return_value="04/04/2024")  
@patch("scraper.utils.random.random", return_value=0.9)   
async def test_extract_posted_date_by_class_with_hours(mock_random, mock_get_posted_date):
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Posted 5h ago")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted-time")
    assert result == "04/04/2024"
    mock_get_posted_date.assert_called_once_with(0)

@pytest.mark.asyncio
@patch("scraper.utils.get_posted_date", return_value="03/03/2024")  
@patch("scraper.utils.random.random", return_value=0.9)   
async def test_extract_posted_date_by_class_with_minutes(mock_random, mock_get_posted_date):
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Posted 42m ago")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted-time")
    assert result == "03/03/2024"
    mock_get_posted_date.assert_called_once_with(0)
  
@pytest.mark.parametrize("markdown, expected", [ 
    ("# 23 jobs listed", 23),
    ("#1,234 jobs found", 1234),
    ("# 1 job available", 1),
    ("# 1 jobs available", 1),
    ("# 0 jobs", 0),
    ("# no jobs here", 0),  
    ("#5job listings", 0),
    ("Totally unrelated text", 0),  
])
def test_extract_total_job_count(markdown, expected):
    assert extract_total_job_count(markdown) == expected

def test_extract_total_job_count_from_file():
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_first_page_markdown.md")
    with open(file_path, "r", encoding="utf-8") as f:
        markdown = f.read()
    expected = 758
    assert extract_total_job_count(markdown) == expected

def test_extract_job_links_from_file():
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_first_page_markdown.md")
    with open(file_path, "r", encoding="utf-8") as f:
        markdown = f.read()
    links = extract_job_links([markdown])
    assert isinstance(links, list)
    assert all(link.startswith("https://www.seek.com.au/job/") for link in links)
    assert all("origin=cardTitle" in link for link in links)
    assert len(links) == 22  

def test_extract_job_links_no_links():
    sample_markdown = "This is just some random text."
    result = extract_job_links(sample_markdown)
    assert result == []

def test_extract_job_urls():
    job_link = "https://www.seek.com.au/job/12345678?type=standard&ref=search-standalone&origin=cardTitle"
    expected_job_url = "https://www.seek.com.au/job/12345678"
    expected_quick_apply_url = "https://www.seek.com.au/job/12345678/apply"
    result = extract_job_urls(job_link)
    assert result == [expected_job_url, expected_quick_apply_url]

@patch("scraper.utils.extract_job_links", return_value=[])
def test_process_markdown_returns_none_on_empty_links(mock_extract):
    fake_markdown = "Markdown with no links"
    result = process_markdown_to_job_links(fake_markdown)
    assert result is None

def test_extract_json_from_response_valid_json():
    assert isinstance(VALID_JSON_STRING, str)
    result = extract_json_from_response(VALID_JSON_STRING)
    assert result == {
        "description": "This is an amazing opportunity for someone looking to take the next step in their product development career within a well-loved retail brand.",
        "responsibilities": [
        "Support the development of Dymocks’ exclusive gifting range, from concept to launch.",
        "Work with suppliers to manage production timelines, negotiate terms, and maintain quality control.",
        "Research trends and contribute to seasonal product collections.",
        "Assist with sample reviews, providing feedback and ensuring final products meet expectations.",
        "Ensure all products comply with relevant safety and quality standards.",
        "Conduct store visits and competitor analysis to identify opportunities for innovation."
        ],
        "requirements": [
        "3+ years’ experience in product development, ideally within gifting or a related category.",
        "Strong organisational skills with the ability to manage multiple projects and meet deadlines.",
        "An eye for great design, quality, and commercially viable products.",
        "Strong communication and relationship-building skills, particularly with suppliers.",
        "Experience working with overseas suppliers (a plus, but not essential)"
        ],
        "experience_level": "mid",
        "work_model": "On-site",
        "other": [
        "Must have Australian Working Rights",
        "Notice period with your current employer will be requested",
        "Base salary/hourly rate expectations will be requested"
        ]
    }
    assert isinstance(result, dict)

def test_extract_json_from_response_invalid_json():
    assert isinstance(MALFORMED_JSON_STRING, str)
    result = extract_json_from_response(MALFORMED_JSON_STRING)
    assert result == MALFORMED_JSON_STRING
    assert isinstance(result, str)

@pytest.mark.asyncio
@patch("scraper.utils.extract_fields_from_job_link_with_groq", new_callable=AsyncMock)
@patch("scraper.utils.extract_json_from_response")
async def test_parse_job_json_from_markdown(mock_extract_json, mock_extract_fields):
    job_md = "mock job markdown"
    count = 1    
    job_json = {
        "description": "This is an amazing opportunity for someone looking to take the next step in their product development career within a well-loved retail brand.",
        "responsibilities": [
        "Support the development of Dymocks’ exclusive gifting range, from concept to launch.",
        "Work with suppliers to manage production timelines, negotiate terms, and maintain quality control.",
        "Research trends and contribute to seasonal product collections.",
        "Assist with sample reviews, providing feedback and ensuring final products meet expectations.",
        "Ensure all products comply with relevant safety and quality standards.",
        "Conduct store visits and competitor analysis to identify opportunities for innovation."
        ],
        "requirements": [
        "3+ years’ experience in product development, ideally within gifting or a related category.",
        "Strong organisational skills with the ability to manage multiple projects and meet deadlines.",
        "An eye for great design, quality, and commercially viable products.",
        "Strong communication and relationship-building skills, particularly with suppliers.",
        "Experience working with overseas suppliers (a plus, but not essential)"
        ],
        "experience_level": "mid",
        "work_model": "On-site",
        "other": [
        "Must have Australian Working Rights",
        "Notice period with your current employer will be requested",
        "Base salary/hourly rate expectations will be requested"
        ]
    }
    mock_extract_fields.return_value = VALID_JSON_STRING
    mock_extract_json.return_value = job_json
    result = await parse_job_json_from_markdown(job_md, count)
    assert result == job_json

@pytest.mark.asyncio
@patch("scraper.utils.repair_json")
@patch("scraper.utils.clean_string")
@patch("scraper.utils.extract_fields_from_job_link_with_groq")
async def test_parse_job_json_from_markdown_with_messy_string_json(mock_extract_fields, mock_clean_string, mock_repair_json):
    job_md = "mock job markdown"
    count = 1
    mock_extract_fields.return_value = MALFORMED_JSON_STRING
    mock_clean_string.return_value = MALFORMED_JSON_STRING
    repaired = """{
        "description": "This innovative tech business is expanding its engineering function and seeking a Site Reliability Engineer to help ensure their world-class platform continues to run like clockwork.", 
        "responsibilities": [
            "Maintain the reliability, availability and performance of the company's software applications", 
            "Resolve incidents swiftly to minimise downtime and ensure a seamless user experience", 
            "Continuously improve system stability and scalability through automation and robust infrastructure tooling", 
            "Dive deep into root cause analysis and propose long-term solutions", 
            "Collaborate with engineers and cross-functional teams to embed DevOps best practices"
        ], 
        "requirements": [
            "Excellent problem-solving skills and a passion for fixing issues at the structural level", 
            "Experience working with cloud-based infrastructure (AWS), Linux, and scripting (Python)", 
            "Familiarity with tooling like Prometheus, Ansible, PostgreSQL, Elasticsearch and Node.js", 
            "Strong communication skills, especially under pressure", 
            "A First or 2:1 degree (Bachelor’s or Master’s) — ideally in a technical field", 
            "Curiosity, collaboration and a desire to make things better!"
        ], 
        "experience_level": "senior", 
        "work_model": "Hybrid", 
        "other": [
            "Competitive Salary | $120,000 - $140,000 + Super", 
            "Join a market leader at the forefront of AI in the legal sector", 
            "Be part of a small, high-calibre SRE team with real ownership", 
            "Solve critical problems in complex systems daily", 
            "Fast-paced scale-up environment with rapid learning & growth", 
            "Inclusive, collaborative, and innovation-focused culture", 
            "Flexible working and attractive package on offer"
            ]
        }"""
    mock_repair_json.return_value = repaired
    result = await parse_job_json_from_markdown(job_md, count)
    repaired_string = mock_repair_json.return_value
    parsed = json.loads(repaired_string)

    assert isinstance(parsed, dict)
    assert result == parsed
    assert result["experience_level"] == "senior"
    assert "responsibilities" in result
    assert isinstance(result["requirements"], list)
    assert result["work_model"] == "Hybrid"

def test_clean_string_removes_backslashes_and_newlines():
    raw_string = """{\n\\"key\\": \\"value\\"\n}"""
    expected = """{"key": "value"}""" 
    result = clean_string(raw_string)
    assert result == expected

@pytest.mark.parametrize(
    "days_ago, within_days, expected",
    [(3, 7, True), (0, 7, True), (7, 7, True), (8, 7, False), (30, 7, False)]
)
def test_is_job_within_date_range_valid_dates(days_ago, within_days, expected):
    posted_date = (datetime.today() - timedelta(days=days_ago)).strftime("%d/%m/%Y")
    job_json = {"posted_date": posted_date}
    assert is_job_within_date_range(job_json, within_days=within_days) is expected

@freeze_time("2024-05-08")
def test_get_relative_posted_time():
    assert get_relative_posted_time({"posted_date": "08/05/2024"}) == "Today"
    assert get_relative_posted_time({"posted_date": "07/05/2024"}) == "Yesterday"
    assert get_relative_posted_time({"posted_date": "06/05/2024"}) == "2 days ago"
    assert get_relative_posted_time({"posted_date": "24/04/2024"}) == "14 days ago"
    assert get_relative_posted_time({"posted_date": "23/04/2024"}) is None  
    assert get_relative_posted_time({"posted_date": "2024-05-08"}) is None
    assert get_relative_posted_time({"posted_date": ""}) is None
    assert get_relative_posted_time({}) is None

@patch("scraper.utils.get_relative_posted_time")
def test_enrich_job_json(mock_get_relative_posted_time):
    job_json = {
        "description": "This is a job description.",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
    }
    location_search = "Sydney"
    job_url = "https://www.seek.com.au/job/12345678"
    quick_apply_url = "https://www.seek.com.au/job/12345678/apply"
    job_data = {
        "posted_time": "01/05/2024",
        "logo_src": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "location": "Sydney NSW",
        "classification": "Testing & Quality Assurance (Information & Communication Technology)",
        "work_type": "Remote",
        "salary": "$100,000 - $120,000",
        "title": "Product Manager",
        "company": "Example Corp"
    }
    mock_get_relative_posted_time.return_value = "7 days ago"
    result = enrich_job_json(job_json, location_search, job_url, quick_apply_url, job_data)
    expected_result = {
        "description": "This is a job description.",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "location_search": "Sydney",
        "posted_date": "01/05/2024",
        "posted_within": "7 days ago",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "location": "Sydney NSW",
        "classification": "Testing & Quality Assurance (Information & Communication Technology)",
        "work_type": "Remote",
        "salary": "$100,000 - $120,000",
        "title": "Product Manager",
        "company": "Example Corp"
    }
    assert result == expected_result

def test_flatten_field_with_list():
    mock_field = [
        "Work with suppliers to manage production timelines.",
        "Support product development from concept to launch.",
        "Ensure quality control standards are met."
    ]

    expected_output = (
        "Work with suppliers to manage production timelines. "
        "Support product development from concept to launch. "
        "Ensure quality control standards are met."
    )
    assert isinstance(mock_field, list)
    result = flatten_field(mock_field)
    assert result == expected_output
    assert isinstance(result, str)

def test_flatten_field_with_string():
    mock_field = "Strong communication and relationship-building skills."
    expected_output = "Strong communication and relationship-building skills."
    result = flatten_field(mock_field)
    assert result == expected_output

def test_flatten_field_with_empty():
    mock_field = []
    expected_output = ""
    result = flatten_field(mock_field)
    assert result == expected_output


