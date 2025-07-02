from unittest.mock import AsyncMock

import pytest
from pages.pool import PagePool

MAX_PAGES = 3

@pytest.mark.asyncio
async def test_init_pages() -> None:
    mock_context = AsyncMock()
    fake_page = AsyncMock()
    mock_context.new_page.return_value = fake_page

    pool = PagePool(mock_context, max_pages=MAX_PAGES)
    await pool.init_pages()

    assert pool.pages.qsize() == MAX_PAGES
    assert mock_context.new_page.await_count == MAX_PAGES

@pytest.mark.asyncio
async def test_acquire_and_release() -> None:
    mock_context = AsyncMock()
    fake_pages = [AsyncMock(name=f"Page{i}") for i in range(MAX_PAGES)]
    mock_context.new_page.side_effect = fake_pages

    pool = PagePool(mock_context, max_pages=MAX_PAGES)
    await pool.init_pages()

    # Acquire two pages
    page1 = await pool.acquire()
    page2 = await pool.acquire()

    assert page1 in fake_pages
    assert page2 in fake_pages
    expected_remaining = MAX_PAGES - 2
    assert pool.pages.qsize() == expected_remaining

    # Release a page back
    await pool.release(page1)
    assert pool.pages.qsize() == expected_remaining + 1

@pytest.mark.asyncio
async def test_close_all_pages() -> None:
    mock_context = AsyncMock()
    fake_pages = [AsyncMock(name=f"Page{i}") for i in range(MAX_PAGES)]
    mock_context.new_page.side_effect = fake_pages

    pool = PagePool(mock_context, max_pages=MAX_PAGES)
    await pool.init_pages()

    await pool.close_all()

    for page in fake_pages:
        page.close.assert_awaited_once()

    assert pool.pages.qsize() == 0

@pytest.mark.asyncio
async def test_acquire_release_full_flow() -> None:
    mock_context = AsyncMock()
    page = AsyncMock()
    mock_context.new_page.return_value = page

    pool = PagePool(mock_context, max_pages=1)
    await pool.init_pages()

    acquired_page = await pool.acquire()
    await pool.release(acquired_page)

    second_acquire = await pool.acquire()
    assert second_acquire == page

