import re
import time
import random
import logging
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Optional, List

import requests
from bs4 import BeautifulSoup


# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scraper")


# Result container
@dataclass
class ScrapeResult:
    url:       str
    site:      str
    name:      Optional[str]   = None
    price:     Optional[float] = None
    currency:  str             = "INR"
    available: bool            = False
    image_url: Optional[str]   = None
    method:    str             = "unknown"
    error:     Optional[str]   = None

    @property
    def success(self) -> bool:
        return self.price is not None and self.name is not None

    def to_dict(self) -> dict:
        return {
            "url":       self.url,
            "site":      self.site,
            "name":      self.name,
            "price":     self.price,
            "currency":  self.currency,
            "available": self.available,
            "image_url": self.image_url,
            "method":    self.method,
            "error":     self.error,
            "success":   self.success,
        }


# Helpers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

def get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-IN,en;q=0.9",
    }

def clean_price(raw: str) -> Optional[float]:
    try:
        cleaned = re.sub(r"[^\d.]", "", str(raw))
        return float(cleaned) if cleaned else None
    except:
        return None

def polite_delay():
    time.sleep(random.uniform(1.5, 3))


# Site detection
SITE_MAP = {
    "amazon":         "amazon",
    "flipkart":       "flipkart",
    "tatacliq":       "tatacliq",
    "myntra":         "myntra",
    "books.toscrape": "books",
}

def detect_site(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    for pattern, key in SITE_MAP.items():
        if pattern in domain:
            return key
    return "unsupported"


# Amazon
def scrape_amazon(url: str) -> ScrapeResult:
    result = ScrapeResult(url=url, site="amazon")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            name = page.locator("span#productTitle").first.inner_text()

            price = None

            # main selector (works most times)
            price_el = page.locator(".a-price .a-offscreen").first
            if price_el.count() > 0:
                price = clean_price(price_el.inner_text())

            # fallback selector
            if not price:
                alt = page.locator("#priceblock_ourprice, #priceblock_dealprice").first
                if alt.count() > 0:
                    price = clean_price(alt.inner_text())

            image_url = None
            img = page.locator("#landingImage").first
            if img.count() > 0:
                image_url = img.get_attribute("src")

            if not name or not price:
                result.error = "Amazon price not found"
                return result

            result.name = name.strip()
            result.price = price
            result.available = True
            result.image_url = image_url
            result.method = "playwright"

            browser.close()

    except Exception as e:
        result.error = str(e)

    return result


# Flipkart
def scrape_flipkart(url: str) -> ScrapeResult:
    result = ScrapeResult(url=url, site="flipkart")
    try:
        from camoufox.sync_api import Camoufox

        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, timeout=60000)

            page.wait_for_selector("h1", timeout=10000)
            page.wait_for_timeout(3000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Product name
            name_el = soup.select_one("h1")

            # Price
            price_text = soup.find(string=lambda x: x and "₹" in x)

            # 🔥 FIXED IMAGE LOGIC
            image_url = None
            imgs = soup.find_all("img")

            for img in imgs:
                src = img.get("src")
                if not src:
                    continue

                # ignore svg / placeholder
                if src.endswith(".svg"):
                    continue

                # pick real product images
                if "rukminim" in src or "flixcart.com/image" in src:
                    image_url = src
                    break

            if not name_el or not price_text:
                result.error = "Flipkart selectors not found"
                return result

            result.name = name_el.text.strip()
            result.price = clean_price(price_text)
            result.available = True
            result.image_url = image_url
            result.method = "camoufox+bs4"

    except Exception as e:
        result.error = str(e)

    return result


# TataCliq
def scrape_tatacliq(url: str) -> ScrapeResult:
    result = ScrapeResult(url=url, site="tatacliq")
    try:
        from camoufox.sync_api import Camoufox
        import json

        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, timeout=60000)

            page.wait_for_timeout(5000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # name
            name_el = soup.select_one("h1")
            name = name_el.text.strip() if name_el else None

            # price
            price_text = soup.find(string=lambda x: x and "₹" in x)
            price = clean_price(price_text) if price_text else None

            # image from JSON
            image_url = None

            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if script:
                try:
                    data = json.loads(script.string)

                    def find_image(obj):
                        if isinstance(obj, dict):
                            for v in obj.values():
                                if isinstance(v, str) and "img.tatacliq.com" in v:
                                    return v
                                res = find_image(v)
                                if res:
                                    return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = find_image(item)
                                if res:
                                    return res
                        return None

                    image_url = find_image(data)

                except:
                    pass

            if not name or not price:
                result.error = "TataCliq selectors not found"
                return result

            result.name = name
            result.price = price
            result.available = True
            result.image_url = image_url
            result.method = "camoufox+json"

    except Exception as e:
        result.error = str(e)

    return result

# Myntra
def scrape_myntra(url: str) -> ScrapeResult:
    result = ScrapeResult(url=url, site="myntra")
    try:
        from camoufox.sync_api import Camoufox
        import re

        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, timeout=60000)

            page.wait_for_timeout(6000)

            page.mouse.move(100, 200)
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(2000)

            name = None
            price = None
            image_url = None

            # name
            brand = page.locator("h1.pdp-title").first
            product = page.locator("h1.pdp-name").first

            if brand.count() > 0 and product.count() > 0:
                name = brand.inner_text() + " " + product.inner_text()

            # price
            price_el = page.locator("span.pdp-price").first
            if price_el.count() == 0:
                price_el = page.locator("span:has-text('₹')").first

            if price_el.count() > 0:
                price = clean_price(price_el.inner_text())

            # image from full HTML
            html = page.content()

            match = re.search(r'https://assets\.myntassets\.com[^\s"]+', html)
            if match:
                image_url = match.group(0)

            if not name or not price:
                result.error = "Myntra selectors not found"
                return result

            result.name = name.strip()
            result.price = price
            result.available = True
            result.image_url = image_url
            result.method = "camoufox+regex"

    except Exception as e:
        result.error = str(e)

    return result

# Books
def scrape_books(url: str) -> ScrapeResult:
    result = ScrapeResult(url=url, site="books")
    try:
        r = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        name = soup.select_one("h1").text
        price = clean_price(soup.select_one("p.price_color").text)

        img = soup.select_one(".thumbnail img")
        image_url = "http://books.toscrape.com/" + img["src"].lstrip("./") if img else None

        result.name = name
        result.price = price
        result.available = True
        result.image_url = image_url
        result.method = "html"

    except Exception as e:
        result.error = str(e)

    return result


def scrape_unsupported(url: str) -> ScrapeResult:
    return ScrapeResult(url=url, site="unsupported", error="Site not supported")


SCRAPERS = {
    "amazon": scrape_amazon,
    "flipkart": scrape_flipkart,
    "tatacliq": scrape_tatacliq,
    "myntra": scrape_myntra,
    "books": scrape_books,
}


def scrape_product(url: str) -> dict:
    if not url.startswith("http"):
        url = "https://" + url

    site = detect_site(url)
    log.info(f"Scraping: {url} (site={site})")

    polite_delay()

    scraper = SCRAPERS.get(site, scrape_unsupported)
    result = scraper(url)

    log.info(f"Result: success={result.success} error={result.error}")
    return result.to_dict()


# Test
if __name__ == "__main__":
    test_urls = [
        "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY",
        "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itmbf14ef54f645d",
        "https://www.tatacliq.com/apple-iphone-15-128-gb/p-mp000000021455495",
        "https://www.myntra.com/tshirts/hrx-by-hrithik-roshan/hrx-by-hrithik-roshan-men-blue-printed-round-neck-t-shirt/19943770/buy"
    ]

    for url in test_urls:
        r = scrape_product(url)
        print("\n", r)