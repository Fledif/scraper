import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time

def test_uc():
    options = uc.ChromeOptions()
    options.headless = True
    # We can try headful for bypassing CF, then close
    driver = uc.Chrome(options=options)
    
    print("Testing Jooble with UC...")
    driver.get("https://ua.jooble.org/SearchResult?p=1")
    time.sleep(5)
    html = driver.page_source
    print("Jooble HTML length:", len(html))
    if "Cloudflare" in html or "Just a moment" in html:
        print("Jooble: Blocked by Cloudflare")
    else:
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article') or soup.find_all('div', attrs={"data-test-id": "vacancy-card"})
        print("Jooble cards found:", len(cards))
    
    print("Testing Robota with UC...")
    driver.get("https://robota.ua/zapros/ukraine")
    time.sleep(5)
    html = driver.page_source
    print("Robota HTML length:", len(html))
    if "Cloudflare" in html or "Just a moment" in html:
        print("Robota: Blocked by Cloudflare")
    else:
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article')
        if not cards:
            cards = soup.find_all('div', class_=lambda x: x and 'santa-' in x)
        print("Robota cards found:", len([c for c in cards if c.find('a')]))

    driver.quit()

if __name__ == "__main__":
    test_uc()
