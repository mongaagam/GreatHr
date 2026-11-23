import os
import sys
from playwright.sync_api import sync_playwright

def load_env_file():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env_file()
URL = os.environ.get("GREYTHR_URL", "https://vcreatek.greythr.com")
LOGIN_ID = os.environ.get("GREYTHR_LOGIN_ID")
PASSWORD = os.environ.get("GREYTHR_PASSWORD")
if not LOGIN_ID or not PASSWORD:
    sys.exit("`.env` mein GREYTHR_LOGIN_ID aur GREYTHR_PASSWORD daalo.")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    page.set_default_timeout(25_000)

    print("1) Site khol raha hoon...")
    page.goto(URL)
    print("   Page title:", page.title())
    page.screenshot(path="test-1-login-page.png")

    print("2) Login kar raha hoon...")
    page.get_by_label("Login ID").fill(LOGIN_ID)
    page.get_by_label("Password").first.fill(PASSWORD)
    page.get_by_role("button", name="Login").click()
    page.wait_for_load_state("networkidle")
    page.screenshot(path="test-2-after-login.png")

    print("3) Buttons jo page par dikh rahe hain:")
    for b in page.get_by_role("button").all():
        try:
            text = b.inner_text().strip()
            if text:
                print("   -", text)
        except Exception:
            pass

    input("\nBrowser dekh lo. Band karne ke liye Enter dabao...")
    browser.close()