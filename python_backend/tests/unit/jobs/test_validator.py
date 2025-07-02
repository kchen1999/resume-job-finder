from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from jobs.validator import validate_job, validate_jobs
from tzlocal import get_localzone


@pytest.mark.asyncio
@patch("jobs.validator.validate_job", new_callable=AsyncMock)
async def test_validate_jobs_happy_path(mock_validate_job: AsyncMock) -> None:
    job1 = {"title": "Dev 1"}
    job2 = {"title": "Dev 2"}
    job3 = {"title": "Dev 3"}
    mock_validate_job.side_effect = [job1, job2, job3]
    page_job_data = [job1, job2, job3]

    job_result = await validate_jobs(page_job_data)
    assert len(job_result) == len(page_job_data)
    assert mock_validate_job.await_count == len(page_job_data)


@pytest.mark.asyncio
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_valid_no_inference(mock_infer_exp: AsyncMock, mock_infer_work_model: AsyncMock) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "experience_level": "mid_or_senior",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    await validate_job(job)
    mock_infer_exp.assert_not_awaited()
    mock_infer_work_model.assert_not_awaited()

@pytest.mark.asyncio
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_infer_invalid_work_model_success(
    mock_infer_exp: AsyncMock,
    mock_infer_work_model: AsyncMock
) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_model": "Flexible",
        "work_type": "Full-time",
        "experience_level": "mid_or_senior",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    mock_infer_work_model.return_value = "Remote"
    job_result = await validate_job(job)
    assert job_result["work_model"] == "Remote"
    mock_infer_work_model.assert_awaited_once()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_infer_missing_experience_level_success(
    mock_infer_exp: AsyncMock,
    mock_infer_work_model: AsyncMock
) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    mock_infer_exp.return_value = "mid_or_senior"
    job_result = await validate_job(job)
    assert job_result["experience_level"] == "mid_or_senior"
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_awaited_once()

@pytest.mark.asyncio
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_infer_invalid_experience_level_success(
    mock_infer_exp: AsyncMock,
    mock_infer_work_model: AsyncMock
) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "experience_level": "experienced",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    mock_infer_exp.return_value = "mid_or_senior"
    job_result = await validate_job(job)
    assert job_result["experience_level"] == "mid_or_senior"
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_awaited_once()

@pytest.mark.asyncio
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_missing_posted_date(mock_infer_work_model: AsyncMock, mock_infer_exp: AsyncMock) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "experience_level": "mid_or_senior",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    job_result = await validate_job(job)
    local_tz = get_localzone()
    today_str = datetime.now(local_tz).strftime("%d/%m/%Y")
    assert job_result["posted_date"] == today_str
    assert job_result["posted_within"] == "Today"
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_missing_required_field(mock_infer_work_model: AsyncMock, mock_infer_exp: AsyncMock) -> None:
    job = {
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "experience_level": "mid_or_senior",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    job_result = await validate_job(job)
    assert job_result["title"] == ""
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_invalid_url(mock_infer_work_model: AsyncMock, mock_infer_exp: AsyncMock) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "experience_level": "mid_or_senior",
        "job_url": "wttps://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": ["Responsibility 1", "Responsibility 2"],
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }

    job_result = await validate_job(job)
    assert job_result["job_url"] == ""
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("jobs.validator.infer_experience_level", new_callable=AsyncMock)
@patch("jobs.validator.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_field_not_list(mock_infer_work_model: AsyncMock, mock_infer_exp: AsyncMock) -> None:
    job = {
        "title": "Software Engineer",
        "company": "Example Corp",
        "classification": "Software Design and Development",
        "description": "This is a job description.",
        "logo_link": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "experience_level": "mid_or_senior",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": "$100,000 - $120,000",
        "responsibilities": "Responsibility 1",
        "requirements": ["Requirement 1", "Requirement 2"],
        "other": ["Be cool"]
    }
    job_result = await validate_job(job)
    assert isinstance(job_result["responsibilities"], list)
    assert job_result["responsibilities"] == ["Responsibility 1"]
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
async def test_validate_job_coerce_non_string_and_non_list_fields() -> None:
    job = {
        "title": ["Software", "Engineer"],
        "company": {"name": "Example Corp"},
        "classification": "Software",
        "description": "desc",
        "logo_link": "https://cdn.com/logo",
        "posted_date": "09/05/2024",
        "posted_within": "7 days",
        "location_search": "Sydney",
        "location": "Sydney NSW",
        "work_type": "Full-time",
        "work_model": "Hybrid",
        "experience_level": "mid_or_senior",
        "job_url": "https://www.seek.com.au/job/12345678",
        "quick_apply_url": "https://www.seek.com.au/job/12345678/apply",
        "salary": 123456,
        "responsibilities": ["Build stuff"],
        "requirements": ["Know Python"],
        "other": None
    }
    job_result = await validate_job(job)
    assert job_result["title"] == "Software, Engineer"
    assert job_result["company"] == "{'name': 'Example Corp'}"
    assert job_result["salary"] == "123456"
    assert job_result["other"] == []


