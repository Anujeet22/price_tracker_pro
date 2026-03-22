from playwright.sync_api import sync_playwright

url = "https://www.amazon.in/NutriPro-Bullet-Juicer-Grinder-Blades/dp/B09J2T124D"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, timeout=60000)
    page.wait_for_timeout(3000)

    # Test name
    try:
        name = page.locator("span#productTitle").first.inner_text()
        print("Name:", name.strip())
    except Exception as e:
        print("Name failed:", e)

    # Test price whole
    try:
        price_whole = page.locator(".a-price-whole").first.inner_text()
        print("Price whole:", price_whole.strip())
    except Exception as e:
        print("Price whole failed:", e)

    browser.close()