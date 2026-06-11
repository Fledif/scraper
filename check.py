import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await Stealth().apply_stealth_async(page)
        await page.goto("https://jobs.ua/vacancy/search?q=%D0%92%D0%BE%D0%B4%D1%96%D0%B9")
        await asyncio.sleep(8)
        title = await page.title()
        content = await page.content()
        print("TITLE:", title)
        print("CONTENT LEN:", len(content))
        if "just a moment" in title.lower() or "cloudflare" in title.lower():
            print("STILL BLOCKED BY CLOUDFLARE!")
        await browser.close()

asyncio.run(run())
