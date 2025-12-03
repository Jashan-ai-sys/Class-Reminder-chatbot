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
        # Check if we are on Render (or just try default)
        try:
            _browser = await _playwright.chromium.launch(headless=True)
        except Exception:
            print("⚠️ Default launch failed. Trying explicit path for Render...")
            # Render installs browsers in a specific cache location
            import os
            # Try to find the executable
            import glob
            print(f"📂 Listing contents of ~/pw-browsers: {glob.glob(os.path.expanduser('~/pw-browsers/**/*'), recursive=True)}")
            
            possible_paths = [
                "/opt/render/.cache/ms-playwright/chromium-1194/chrome-linux/chrome",
                "/opt/render/.cache/ms-playwright/chromium_headless_shell-1194/chrome-linux/headless_shell",
                os.path.expanduser("~/pw-browsers/chromium-1194/chrome-linux/chrome"),
                os.path.expanduser("~/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell")
            ]
            executable_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    executable_path = path
                    break
            
            if executable_path:
                print(f"✅ Found executable at: {executable_path}")
                _browser = await _playwright.chromium.launch(headless=True, executable_path=executable_path)
            else:
                raise Exception("❌ Could not find Chromium executable on Render.")
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
