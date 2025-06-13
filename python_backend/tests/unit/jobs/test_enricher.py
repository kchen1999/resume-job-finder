import pytest
from unittest.mock import patch, AsyncMock
from freezegun import freeze_time

from jobs.enricher import set_default_work_model, infer_experience_level_from_title, override_experience_level_with_title, normalize_experience_level, get_relative_posted_time, enrich_job_data, enrich_job

@freeze_time("2024-05-08")
def test_get_relative_posted_time():
    assert get_relative_posted_time({"posted_date": "08/05/2024"}) == "Today"
    assert get_relative_posted_time({"posted_date": "07/05/2024"}) == "Yesterday"
    assert get_relative_posted_time({"posted_date": "06/05/2024"}) == "2 days ago"
    assert get_relative_posted_time({"posted_date": "24/04/2024"}) == "14 days ago"
    assert get_relative_posted_time({"posted_date": "23/04/2024"}) == "15 days ago" 
    assert get_relative_posted_time({"posted_date": "2024-05-08"}) is None
    assert get_relative_posted_time({"posted_date": ""}) is None
    assert get_relative_posted_time({}) is None

def test_sets_work_model_to_onsite_if_none():
    job = {"title": "Software Engineer", "work_model": None}
    job = set_default_work_model(job)
    assert job["work_model"] == "On-site"

def test_does_not_override_existing_work_model():
    job = {"title": "Software Engineer", "work_model": "Remote"}
    job = set_default_work_model(job)
    assert job["work_model"] == "Remote"

@pytest.mark.parametrize("title, expected", [
    ("Software Engineering Intern", "intern"),
    ("Internship for Penultimate Students", "intern"),
    ("Junior Data Analyst", "junior"),
    ("Graduate Engineer", "junior"),
    ("Entry Level Engineer", "junior"),
    ("Lead Engineer", "lead+"),
    ("VP of Engineering", "lead+"),
    ("Chief Technical Officer", "lead+"),
    ("Principal ML Engineer", "lead+"),
    ("Regular Software Developer", ""),
])
def test_infer_experience_level_from_title(title, expected):
    assert infer_experience_level_from_title(title) == expected

@pytest.mark.parametrize("input_job, expected_level, should_override", [
    ({"title": "Software Engineering Intern"}, "intern", True),
    ({"title": "Junior Backend Developer"}, "junior", True),
    ({"title": "Senior Frontend Engineer"}, "", False),
    ({"title": "Lead Data Scientist"}, "lead+", True),
    ({"title": ""}, "", False),
    ({}, "", False),
    ({"title": "Senior Engineering Manager", "experience_level": "mid_or_senior"}, "lead+", True),
    ({"title": "Lead Backend Developer", "experience_level": "mid_or_senior"}, "lead+", True),
    ({"title": "Senior Software Engineer", "experience_level": "mid_or_senior"}, "mid_or_senior", False),
])
def test_override_experience_level_with_title(input_job, expected_level, should_override):
    original = input_job.get("experience_level")
    result = override_experience_level_with_title(input_job)
    if should_override:
        assert result["experience_level"] == expected_level
    else:
        if original is not None:
            assert result["experience_level"] == original
        else:
            assert "experience_level" not in result

@pytest.mark.parametrize("input_job, expected_level", [
    ({"experience_level": "mid"}, "mid_or_senior"),
    ({"experience_level": "senior"}, "mid_or_senior"),
    ({"experience_level": "MID"}, "mid_or_senior"), 
    ({"experience_level": "junior"}, "junior"),
    ({"experience_level": "entry"}, "entry"),
    ({}, ""), 
])
def test_normalize_experience_level(input_job, expected_level):
    result = normalize_experience_level(input_job)  
    assert result.get("experience_level", "") == expected_level

@patch("jobs.enricher.normalize_experience_level")
@patch("jobs.enricher.override_experience_level_with_title")
@patch("jobs.enricher.set_default_work_model")
@patch("jobs.enricher.get_relative_posted_time")
def test_enrich_job_data(
    mock_get_relative_posted_time,
    mock_set_default_work_model,
    mock_override_experience_level_with_title,
    mock_normalize_experience_level
):
    job_data = {
        "description": "This is a job description.",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
    }
    location_search = "Sydney"
    job_url = "https://www.seek.com.au/job/12345678"
    quick_apply_url = "https://www.seek.com.au/job/12345678/apply"
    job_metadata = {
        "posted_date": "01/05/2024",
        "logo_src": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "location": "Sydney NSW",
        "classification": "Software Design and Development",
        "work_type": "Remote",
        "salary": "$100,000 - $120,000",
        "title": "Software Engineer",
        "company": "Example Corp"
    }
    mock_get_relative_posted_time.return_value = "7 days ago"

    base_job = job_data.copy()
    base_job["job_url"] = job_url
    base_job["quick_apply_url"] = quick_apply_url
    base_job["location_search"] = location_search
    base_job["posted_date"] = "01/05/2024"
    base_job["posted_within"] = "7 days ago"
    base_job["logo_link"] = "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f"
    base_job["location"] = "Sydney NSW"
    base_job["classification"] = "Software Design and Development"
    base_job["work_type"] = "Remote"
    base_job["salary"] = "$100,000 - $120,000"
    base_job["title"] = "Software Engineer"
    base_job["company"] = "Example Corp"

    job_after_work_model = base_job.copy()
    job_after_work_model["work_model"] = "Remote"

    job_after_experience_override = job_after_work_model.copy()
    job_after_experience_override["experience_level"] = "Mid-level"

    job_after_normalization = job_after_experience_override.copy()
    job_after_normalization["experience_level"] = "mid"

    mock_set_default_work_model.return_value = job_after_work_model
    mock_override_experience_level_with_title.return_value = job_after_experience_override
    mock_normalize_experience_level.return_value = job_after_normalization

    result = enrich_job_data(job_data, location_search, job_url, quick_apply_url, job_metadata)
    assert result == job_after_normalization

    mock_get_relative_posted_time.assert_called_once()
    mock_set_default_work_model.assert_called_once_with(base_job)
    mock_override_experience_level_with_title.assert_called_once_with(job_after_work_model)
    mock_normalize_experience_level.assert_called_once_with(job_after_experience_override)

@pytest.mark.asyncio
@patch("jobs.enricher.enrich_job_data")
@patch("jobs.enricher.get_job_urls")
async def test_enrich_job(mock_get_job_urls, mock_enrich_job_data):
    job_data = {
        "description": "Job desc",
        "requirements": ["Req A"],
        "responsibilities": ["Resp A"]
    }
    location_search = "Sydney"
    job_url = "https://www.seek.com.au/job/1111"
    quick_apply_url = "https://www.seek.com.au/job/1111/apply"
    job_metadata = {
        "posted_date": "01/05/2024",
        "title": "Backend Developer",
        "company": "Example Corp"
    }

    expected_job_data = {
        **job_data,
        "job_url": job_url,
        "quick_apply_url": quick_apply_url,
        "location_search": location_search,
        "posted_date": "01/05/2024",
        "title": "Backend Developer",
        "company": "Example Corp"
    }

    mock_get_job_urls.return_value = (job_url, quick_apply_url)
    mock_enrich_job_data.return_value = expected_job_data

    result = await enrich_job(job_data, job_url, location_search, job_metadata)

    assert result == expected_job_data
    mock_get_job_urls.assert_called_once_with(job_url)
    mock_enrich_job_data.assert_called_once_with(
        job_data,
        location_search,
        job_url,
        quick_apply_url,
        job_metadata
    )
