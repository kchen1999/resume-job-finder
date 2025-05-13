import pytest
from scraper.groq_utils import extract_missing_experience_level_with_groq, extract_missing_work_model_with_groq

@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_missing_work_model_with_groq_real():
    job_text = (
        "We are looking for a software engineer to join our remote team. "
        "You will work from anywhere and collaborate with teams via Zoom and Slack. "
        "Our company values flexibility and remote-first culture."
    )
    result = await extract_missing_work_model_with_groq(job_text)
    assert result in {"Hybrid", "On-site", "Remote"}, f"Unexpected result: {result}"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_missing_experience_level_with_groq_real():
    job_title = "Senior Backend Engineer"
    job_text = (
        "We're hiring a Senior Backend Engineer with 5+ years of experience in Python and distributed systems. "
        "You will lead backend feature development and mentor junior engineers."
    )
    result = await extract_missing_experience_level_with_groq(job_title, job_text)
    assert result in {"intern", "junior", "mid_or_senior", "lead+"}, f"Unexpected result: {result}"
