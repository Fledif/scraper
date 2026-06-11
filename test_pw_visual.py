import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        print("Testing Jooble...")
        await page.goto("https://ua.jooble.org/SearchResult?p=1")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="jooble.png")
        print("Jooble HTML length:", len(await page.content()))
        
        print("Testing Robota...")
        await page.goto("https://robota.ua/zapros/ukraine")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="robota.png")
        print("Robota HTML length:", len(await page.content()))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
