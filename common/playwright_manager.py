# playwright_manager.py
import asyncio
from playwright.async_api import async_playwright

# Global variables
_browser = None
_playwright = None
_semaphore = asyncio.Semaphore(2)  # limit concurrent logins to 2

async def init_browser():
    global _playwright, _browser
    if not _playwright:
        _playwright = await async_playwright().start()
    if not _browser:
        _browser = await _playwright.chromium.launch(headless=True)
    return _browser

async def close_browser():
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None

async def run_in_tab(task_fn, *args, **kwargs):
    """Run Playwright work in a new tab safely (semaphore protected)."""
    browser = await init_browser()
    async with _semaphore:
        context = await browser.new_context()
        page = await context.new_page()
        try:
            return await task_fn(page, *args, **kwargs)
        finally:
            await context.close()
