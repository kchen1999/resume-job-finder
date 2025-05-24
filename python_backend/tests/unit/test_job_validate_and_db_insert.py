import pytest
import copy
from unittest.mock import AsyncMock, patch
from datetime import datetime
from job_validate_and_db_insert import validate_and_insert_jobs, validate_job

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.validate_job", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_validate_and_insert_jobs_happy_path(mock_send_to_node, mock_validate_job):
    job1 = {"title": "Dev 1"}
    job2 = {"title": "Dev 2"}
    job3 = {"title": "Invalid"}
    mock_validate_job.side_effect = [
        (job1, False, ()),
        (job2, False, ()),
        (job3, True, ("title",))
    ]
    page_job_data = [job1, job2, job3]

    job_count, invalid_jobs, all_errors = await validate_and_insert_jobs(page_job_data, page_num=1, job_count=0)
    assert job_count == 3
    assert invalid_jobs == [{"title": "Invalid", "invalid_fields": ["title"]}]
    assert all_errors == []
    mock_send_to_node.assert_awaited_once_with([job1, job2, job3])
    assert mock_validate_job.await_count == 3

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.validate_job", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_validate_and_insert_jobs_all_invalid(mock_send_to_node, mock_validate_job):
    job1 = {"title": "Invalid 1"}
    job2 = {"title": "Invalid 2"}
    job3 = {"title": "Invalid 3"}
    mock_validate_job.side_effect = [
        (job1, True, ("title",)),
        (job2, True, ("title",)),
        (job3, True, ("title",))
    ]
    page_job_data = [job1, job2, job3]
    job_count, invalid_jobs, all_errors = await validate_and_insert_jobs(page_job_data, page_num=2, job_count=0)
    expected_invalid_jobs = []
    for job in page_job_data:
        copy_job = job.copy()
        copy_job["invalid_fields"] = ["title"]
        expected_invalid_jobs.append(copy_job)
    assert invalid_jobs == expected_invalid_jobs
    assert job_count == 3
    assert all_errors == []
    assert mock_validate_job.await_count == 3
    mock_send_to_node.assert_awaited_once_with([job1, job2, job3])

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.validate_job", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_validate_and_insert_jobs_db_insert_exception(mock_send_to_node, mock_validate_job):
    job1 = {"title": "Dev 1"}
    job2 = {"title": "Dev 2"}
    mock_validate_job.side_effect = [(job1, False, ()), (job2, False, ())]
    mock_send_to_node.side_effect = Exception("DB connection failed")
    all_errors = []

    job_count, invalid_jobs, all_errors = await validate_and_insert_jobs([job1, job2], page_num=3, job_count=5)
    assert job_count == 5  
    assert invalid_jobs == []
    assert mock_send_to_node.await_count == 1
    assert len(all_errors) == 1
    assert "DB insert error on page 3: DB connection failed" in all_errors[0]

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.send_page_jobs_to_node", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.validate_job", new_callable=AsyncMock)
async def test_invalid_jobs_are_original_versions(mock_validate_job, mock_send_jobs):
    original_job = {"title": "Original Title", "job_url": "http://example.com"}
    job_to_return = copy.deepcopy(original_job)
    job_to_return["title"] = "Modified Title"
    mock_validate_job.return_value = (job_to_return, True, ("title",))
    job_count, invalid_jobs, all_errors = await validate_and_insert_jobs(
        [original_job], page_num=1, job_count=0
    )
    mock_send_jobs.assert_awaited_once()
    # Assert that the invalid job is not the mutated version
    assert invalid_jobs == [{"title": "Original Title", "job_url": "http://example.com", "invalid_fields": ["title"]}]
    assert all_errors == []

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_valid_no_inference(mock_infer_exp, mock_infer_work_model):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert was_invalid is False
    mock_infer_exp.assert_not_awaited()
    mock_infer_work_model.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_infer_invalid_work_model_success(mock_infer_exp, mock_infer_work_model):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert was_invalid is True
    assert job_result["work_model"] == "Remote"
    mock_infer_work_model.assert_awaited_once()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_infer_missing_experience_level_success(mock_infer_exp, mock_infer_work_model):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert was_invalid is True
    assert job_result["experience_level"] == "mid_or_senior"
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_awaited_once()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_infer_invalid_experience_level_success(mock_infer_exp, mock_infer_work_model):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert was_invalid is True
    assert job_result["experience_level"] == "mid_or_senior"
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_awaited_once()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_missing_posted_date(mock_infer_work_model, mock_infer_exp):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    today_str = datetime.today().strftime('%d/%m/%Y')
    assert job_result["posted_date"] == today_str
    assert job_result["posted_within"] == "Today"
    assert was_invalid is True
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_missing_required_field(mock_infer_work_model, mock_infer_exp):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert job_result["title"] == ""
    assert was_invalid is True
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_invalid_url(mock_infer_work_model, mock_infer_exp):
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

    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert job_result["job_url"] == ""
    assert was_invalid is True
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
async def test_validate_job_field_not_list(mock_infer_work_model, mock_infer_exp):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert was_invalid is True
    assert isinstance(job_result["responsibilities"], list)
    assert job_result["responsibilities"] == ["Responsibility 1"]
    mock_infer_work_model.assert_not_awaited()
    mock_infer_exp.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_validate_and_db_insert.infer_work_model", new_callable=AsyncMock)
@patch("job_validate_and_db_insert.infer_experience_level", new_callable=AsyncMock)
async def test_validate_job_coerce_non_string_and_non_list_fields(mock_infer_exp, mock_infer_work_model):
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
    job_result, was_invalid, invalid_fields = await validate_job(job)
    assert job_result["title"] == "Software, Engineer"
    assert job_result["company"] == "{'name': 'Example Corp'}"
    assert job_result["salary"] == "123456"
    assert job_result["other"] == []
    assert was_invalid is True

    



