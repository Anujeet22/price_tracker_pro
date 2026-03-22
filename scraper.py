import re
import json
import time
import random
import logging
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Optional, List

import requests
from bs4 import BeautifulSoup


# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scraper")


# ── Result container ─────────────────────────────────────────────────────────
@dataclass
class ScrapeResult:
    url: str
    site: str
    name: Optional[str] = None
    price: Optional[float] = None
    currency: str = "INR"          
    available: bool = False
    image_url: Optional[str] = None
    method: str = "unknown"
    error: Optional[str] = None

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


# ── Helpers ───────────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
]

def get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }

def clean_price(raw: str) -> Optional[float]:
    """Remove all non-numeric characters except dot, then convert to float."""
    try:
        cleaned = re.sub(r"[^\d.]", "", str(raw))
        return float(cleaned) if cleaned else None
    except Exception:
        return None

def polite_delay():
    """Wait a short random time between requests to be respectful."""
    time.sleep(random.uniform(1.5, 3))


# ── Site detection ────────────────────────────────────────────────────────────
SITE_MAP = {
    "amazon":        "amazon",
    "flipkart":      "flipkart",
    "ebay":          "ebay",
    "books.toscrape": "books",
}

def detect_site(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    for pattern, key in SITE_MAP.items():
        if pattern in domain:
            return key
    return "unsupported"


# ── Scrapers ──────────────────────────────────────────────────────────────────

def scrape_amazon(url: str) -> ScrapeResult:
    """Scrape product name and price from Amazon using Playwright."""
    result = ScrapeResult(url=url, site="amazon")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            # Get product name — target span only to avoid hidden input conflict
            name = page.locator("span#productTitle").first.inner_text()

            # Get price — whole part + fraction part (e.g. 499 + 00 = 499.00)
            price_whole = page.locator(".a-price-whole").first.inner_text()
            price_fraction = "00"
            fraction_el = page.locator(".a-price-fraction").first
            if fraction_el.count() > 0:
                price_fraction = fraction_el.inner_text().strip()

            price_str = price_whole.strip().rstrip('.') + "." + price_fraction

            result.name      = name.strip()
            result.price     = clean_price(price_str)
            result.currency  = "INR"
            result.available = True
            result.method    = "playwright"

            browser.close()

    except Exception as e:
        result.error = str(e)

    return result


def scrape_flipkart(url: str) -> ScrapeResult:
    """Scrape product name and price from Flipkart using Playwright."""
    result = ScrapeResult(url=url, site="flipkart")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            name  = page.locator("span.B_NuCI").first.inner_text()
            price = page.locator("div._30jeq3").first.inner_text()

            result.name      = name.strip()
            result.price     = clean_price(price)
            result.currency  = "INR"
            result.available = True
            result.method    = "playwright"

            browser.close()

    except Exception as e:
        result.error = str(e)

    return result


def scrape_ebay(url: str) -> ScrapeResult:
    """Scrape product name and price from eBay using requests + BeautifulSoup."""
    result = ScrapeResult(url=url, site="ebay")
    try:
        r = requests.get(url, headers=get_headers(), timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        # Try structured JSON data first (more reliable)
        script = soup.find("script", {"type": "application/ld+json"})
        if script and script.string:
            try:
                data  = json.loads(script.string)
                offer = data.get("offers", {})
                price = clean_price(str(offer.get("price", "")))
                if price:
                    result.name     = data.get("name")
                    result.price    = price
                    result.currency = "INR"
                    result.method   = "json"
                    return result
            except Exception:
                pass

        # Fallback to HTML selectors
        name  = soup.select_one("h1 span")
        price = soup.select_one("span.ux-textspans")

        if name and price:
            result.name     = name.text.strip()
            result.price    = clean_price(price.text)
            result.currency = "INR"
            result.method   = "html"
        else:
            result.error = "eBay parsing failed — selectors not found"

    except Exception as e:
        result.error = str(e)

    return result


def scrape_books(url: str) -> ScrapeResult:
    """Scrape product name and price from books.toscrape.com (good for testing)."""
    result = ScrapeResult(url=url, site="books")
    try:
        r    = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        name  = soup.select_one("h1")
        price = soup.select_one("p.price_color")

        if not name or not price:
            result.error = "books.toscrape parsing failed"
            return result

        result.name      = name.text.strip()
        result.price     = clean_price(price.text)
        result.currency  = "INR"   # converted to INR as per project requirement
        result.available = True
        result.method    = "html"

        img = soup.select_one(".thumbnail img")
        if img:
            result.image_url = "http://books.toscrape.com/" + img["src"].lstrip("./")

    except Exception as e:
        result.error = str(e)

    return result


def scrape_unsupported(url: str) -> ScrapeResult:
    """Returned when the site is not supported."""
    return ScrapeResult(
        url=url,
        site="unsupported",
        error="This site is not supported. Supported: Amazon, Flipkart, eBay, books.toscrape"
    )


# ── Scraper registry ──────────────────────────────────────────────────────────
SCRAPERS = {
    "amazon":   scrape_amazon,
    "flipkart": scrape_flipkart,
    "ebay":     scrape_ebay,
    "books":    scrape_books,
}


# ── Public API ────────────────────────────────────────────────────────────────

def scrape_product(url: str) -> dict:
    """
    Main entry point. Pass any product URL and get back a result dict.
    Always returns a dict with a 'success' key — never raises an exception.
    """
    url = url.strip()

    if not url.startswith("http"):
        url = "https://" + url

    # Remove query parameters to get clean URL
    url = url.split("?")[0]

    site = detect_site(url)
    log.info(f"Scraping: {url}  (site={site})")

    polite_delay()

    scraper = SCRAPERS.get(site, scrape_unsupported)
    result  = scraper(url)

    log.info(f"Result: success={result.success}  error={result.error}")

    return result.to_dict()


def scrape_multiple(urls: List[str], delay: float = 3.0) -> List[dict]:
    """Scrape a list of URLs one by one with a delay between each."""
    results = []
    for i, url in enumerate(urls, 1):
        log.info(f"[{i}/{len(urls)}] {url}")
        results.append(scrape_product(url))
        if i < len(urls):
            time.sleep(delay)
    return results


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_urls = [
        "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    ]

    for url in test_urls:
        r = scrape_product(url)
        print(f"\nURL     : {r['url'][:70]}")
        print(f"Success : {r['success']}")
        if r["success"]:
            print(f"Name    : {r['name']}")
            print(f"Price   : {r['currency']} {r['price']}")
            print(f"Method  : {r['method']}")
        else:
            print(f"Error   : {r['error']}")