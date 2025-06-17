import asyncio


class PagePool:
    def __init__(self, context, max_pages):
        self.context = context
        self.semaphore = asyncio.Semaphore(max_pages)
        self.pages = asyncio.Queue()
        self._initialized = False

    async def init_pages(self):
        for _ in range(self.semaphore._value):
            page = await self.context.new_page()
            await self.pages.put(page)
        self._initialized = True

    async def acquire(self):
        await self.semaphore.acquire()
        return await self.pages.get()

    async def release(self, page):
        await self.pages.put(page)
        self.semaphore.release()

    async def close_all(self):
        while not self.pages.empty():
            page = await self.pages.get()
            await page.close()
