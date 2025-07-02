import asyncio

from playwright.async_api import BrowserContext, Page


class PagePool:
    def __init__(self, context: BrowserContext, max_pages: int) -> None:
        """Initialize a PagePool instance.

        Args:
            context: The browser context or environment to manage pages in.
            max_pages (int): The maximum number of pages to keep in the pool.

        """
        self.context = context
        self.max_pages = max_pages
        self.semaphore = asyncio.Semaphore(max_pages)
        self.pages = asyncio.Queue()
        self._initialized = False

    async def init_pages(self) -> None:
        for _ in range(self.max_pages):
            page = await self.context.new_page()
            await self.pages.put(page)
        self._initialized = True

    async def acquire(self) -> Page:
        await self.semaphore.acquire()
        return await self.pages.get()

    async def release(self, page: Page) -> None:
        await self.pages.put(page)
        self.semaphore.release()

    async def close_all(self) -> None:
        while not self.pages.empty():
            page = await self.pages.get()
            await page.close()
