import pytest
from unittest.mock import patch, AsyncMock

from jobs.inserter import insert_jobs_into_database

@pytest.mark.asyncio
@patch("jobs.inserter.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_insert_jobs_into_database_success(mock_send_to_node):
    cleaned_jobs = [{"title": "Dev 1"}, {"title": "Dev 2"}]
    page_num = 1
    job_count = 5

    new_count = await insert_jobs_into_database(cleaned_jobs, page_num, job_count)

    assert new_count == 7 
    mock_send_to_node.assert_awaited_once_with(cleaned_jobs)

@pytest.mark.asyncio
@patch("jobs.inserter.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_insert_jobs_into_database_empty_list(mock_send_to_node):
    cleaned_jobs = []
    page_num = 2
    job_count = 10

    new_count = await insert_jobs_into_database(cleaned_jobs, page_num, job_count)

    assert new_count == 10
    mock_send_to_node.assert_not_awaited()



