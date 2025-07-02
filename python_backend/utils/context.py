import asyncio
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler
from pages.pool import PagePool


@dataclass
class ScrapeContext:
    crawler: AsyncWebCrawler
    page_pool: PagePool
    location_search: str
    terminate_event: asyncio.Event
    semaphore: asyncio.Semaphore
    day_range_limit: int
