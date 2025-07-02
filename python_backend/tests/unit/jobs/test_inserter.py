from unittest.mock import AsyncMock, patch

import pytest
from jobs.inserter import insert_jobs_into_database


@pytest.mark.asyncio
@patch("jobs.inserter.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_insert_jobs_into_database_success(mock_send_to_node: AsyncMock) -> None:
    cleaned_jobs = [{"title": "Dev 1"}, {"title": "Dev 2"}]
    page_num = 1
    job_count = 5

    new_count = await insert_jobs_into_database(cleaned_jobs, page_num, job_count)

    assert new_count == job_count + len(cleaned_jobs)
    mock_send_to_node.assert_awaited_once_with(cleaned_jobs)

@pytest.mark.asyncio
@patch("jobs.inserter.send_page_jobs_to_node", new_callable=AsyncMock)
async def test_insert_jobs_into_database_empty_list(mock_send_to_node: AsyncMock) -> None:
    cleaned_jobs = []
    page_num = 2
    job_count = 10

    new_count = await insert_jobs_into_database(cleaned_jobs, page_num, job_count)

    assert new_count == job_count
    mock_send_to_node.assert_not_awaited()



