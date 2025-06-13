import pytest
import asyncio
from unittest.mock import AsyncMock

from python_backend.tests.unit.pages.test_pool import PagePool

@pytest.mark.asyncio
async def test_init_pages():
    mock_context = AsyncMock()
    fake_page = AsyncMock()
    mock_context.new_page.return_value = fake_page

    pool = PagePool(mock_context, max_pages=3)
    await pool.init_pages()

    assert pool._initialized is True
    assert pool.pages.qsize() == 3
    assert mock_context.new_page.await_count == 3

@pytest.mark.asyncio
async def test_acquire_and_release():
    mock_context = AsyncMock()
    fake_pages = [AsyncMock(name=f"Page{i}") for i in range(2)]
    mock_context.new_page.side_effect = fake_pages

    pool = PagePool(mock_context, max_pages=2)
    await pool.init_pages()

    # Acquire two pages
    page1 = await pool.acquire()
    page2 = await pool.acquire()

    assert page1 in fake_pages
    assert page2 in fake_pages
    assert pool.semaphore._value == 0
    assert pool.pages.qsize() == 0

    # Release a page back
    await pool.release(page1)
    assert pool.pages.qsize() == 1
    assert pool.semaphore._value == 1

@pytest.mark.asyncio
async def test_close_all_pages():
    mock_context = AsyncMock()
    fake_pages = [AsyncMock(name=f"Page{i}") for i in range(2)]
    mock_context.new_page.side_effect = fake_pages

    pool = PagePool(mock_context, max_pages=2)
    await pool.init_pages()

    await pool.close_all()

    for page in fake_pages:
        page.close.assert_awaited_once()

    assert pool.pages.qsize() == 0

@pytest.mark.asyncio
async def test_acquire_release_full_flow():
    mock_context = AsyncMock()
    page = AsyncMock()
    mock_context.new_page.return_value = page

    pool = PagePool(mock_context, max_pages=1)
    await pool.init_pages()

    acquired_page = await pool.acquire()
    await pool.release(acquired_page)

    second_acquire = await pool.acquire()
    assert second_acquire == page

