import asyncio
import logging

logger = logging.getLogger(__name__)

import sentry_sdk
from playwright.async_api import async_playwright
from utils.constants import BROWSER_USER_AGENT, CONCURRENT_JOBS_NUM
from utils.retry import retry_with_backoff

from pages.pool import PagePool


async def create_browser_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
            "--no-zygote"
        ],
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="Australia/Sydney",
        user_agent=BROWSER_USER_AGENT["User-Agent"],
        java_script_enabled=False
    )
    await context.add_init_script(
        """() => {
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        }"""
    )

    await context.route("**/*", lambda route, request: asyncio.create_task(
        route.abort() if request.resource_type in ["image", "font", "stylesheet"] else route.continue_()
    ))

    return playwright, browser, context

async def setup_scraping_context():
    async def create_context_wrapper():
        playwright, browser, context = await create_browser_context()
        page_pool = PagePool(context, max_pages=CONCURRENT_JOBS_NUM)
        await page_pool.init_pages()
        return playwright, browser, page_pool

    result = await retry_with_backoff(
        create_context_wrapper,
        max_retries=3,
        base_delay=1.0,
        label="create_browser_context"
    )

    if result is None:
        logger.error("Failed to create scraping context after retries.")
        return None, None, None

    return result

async def teardown_scraping_context(playwright, browser, page_pool):
    try:
        await page_pool.close_all()
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "teardown_scraping_context")
            scope.set_extra("stage", "page_pool.close_all")
            sentry_sdk.capture_exception(e)

    try:
        await browser.close()
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "teardown_scraping_context")
            scope.set_extra("stage", "browser.close")
            sentry_sdk.capture_exception(e)

    try:
        await playwright.stop()
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "teardown_scraping_context")
            scope.set_extra("stage", "playwright.stop")
            sentry_sdk.capture_exception(e)

