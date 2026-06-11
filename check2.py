import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto("https://jobs.ua/vacancy/search?q=%D0%92%D0%BE%D0%B4%D1%96%D0%B9")
        await asyncio.sleep(5)
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for li tags with class
        for li in soup.find_all('li')[:20]:
            cls = li.get('class', [])
            if cls:
                print("LI CLASS:", cls)
        
        await browser.close()

asyncio.run(run())
