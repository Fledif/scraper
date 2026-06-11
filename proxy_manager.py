import asyncio
import aiohttp
from curl_cffi.requests import AsyncSession
import logging

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.working_proxies = []

    async def fetch_free_proxies(self):
        logging.info("Збираємо безкоштовні проксі...")
        sources = [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
        ]
        
        async with aiohttp.ClientSession() as session:
            for url in sources:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            text = await response.text()
                            lines = text.strip().split('\n')
                            for line in lines:
                                if line.strip():
                                    self.proxies.append(f"http://{line.strip()}")
                except Exception as e:
                    logging.error(f"Помилка завантаження проксі з {url}: {e}")
                    
        self.proxies = list(set(self.proxies))
        logging.info(f"Знайдено {len(self.proxies)} унікальних проксі. Починаємо перевірку...")
        
    async def check_proxy(self, proxy):
        try:
            proxies = {"http": proxy, "https": proxy}
            async with AsyncSession(proxies=proxies, impersonate="chrome110") as session:
                res = await session.get("https://ua.jooble.org/SearchResult?p=1", timeout=10)
                if res.status_code == 200 and "Just a moment" not in res.text:
                    self.working_proxies.append(proxy)
                    logging.info(f"[+] Проксі працює для Cloudflare: {proxy}")
        except:
            pass

    async def get_working_proxies(self, limit=10):
        await self.fetch_free_proxies()
        
        batch_size = 200
        for i in range(0, min(2000, len(self.proxies)), batch_size): 
            batch = self.proxies[i:i+batch_size]
            tasks = [self.check_proxy(p) for p in batch]
            await asyncio.gather(*tasks)
            if len(self.working_proxies) >= limit:
                break
                
        logging.info(f"Знайдено {len(self.working_proxies)} робочих проксі.")
        return self.working_proxies

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    pm = ProxyManager()
    asyncio.run(pm.get_working_proxies(5))
