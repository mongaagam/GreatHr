import os
import re
import sys
import time
from datetime import datetime

import schedule
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

SIGNIN_TIME = "09:00"
SIGNOUT_TIME = "19:00"
RETRIES = 3
RETRY_DELAY_SEC = 120


def load_env_file():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def need(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing {name}. Add it to the .env file next to this script.")
    return value


load_env_file()
URL = os.environ.get("GREYTHR_URL", "https://vcreatek.greythr.com")
LOGIN_ID = need("GREYTHR_LOGIN_ID")
PASSWORD = need("GREYTHR_PASSWORD")
HEADLESS = os.environ.get("HEADLESS", "1") != "0"

SIGNIN_BTN = re.compile(r"^\s*sign\s*in\s*$", re.I)
SIGNOUT_BTN = re.compile(r"^\s*sign\s*out\s*$", re.I)


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def punch(action):
    """Returns 'clicked', 'skipped' or raises on failure."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(geolocation=None, permissions=[])
        page = context.new_page()
        page.set_default_timeout(25_000)
        try:
            page.goto(URL)
            page.get_by_label("Login ID").fill(LOGIN_ID)
            page.get_by_label("Password").first.fill(PASSWORD)
            page.get_by_role("button", name="Login").click()
            page.wait_for_load_state("networkidle")

            signin = page.get_by_role("button", name=SIGNIN_BTN)
            signout = page.get_by_role("button", name=SIGNOUT_BTN)

            # Wait until the home page shows whichever button applies right now
            signin.or_(signout).first.wait_for()

            if action == "signin":
                if signout.count() > 0 and signin.count() == 0:
                    log("Already signed in - nothing to do.")
                    return "skipped"
                signin.first.click()
            else:
                if signout.count() == 0:
                    log("Not signed in (or already signed out) - nothing to do.")
                    return "skipped"
                signout.first.click()

            page.wait_for_load_state("networkidle")
            page.screenshot(path=f"{action}-{stamp}.png")
            log(f"{action} clicked. Screenshot: {action}-{stamp}.png")
            return "clicked"
        except Exception:
            page.screenshot(path=f"error-{action}-{stamp}.png")
            log(f"Failed. Screenshot: error-{action}-{stamp}.png")
            raise
        finally:
            browser.close()


def punch_with_retry(action):
    for attempt in range(1, RETRIES + 1):
        try:
            punch(action)
            return
        except (PWTimeout, Exception) as err:
            log(f"{action} attempt {attempt}/{RETRIES} failed: {err}")
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY_SEC)
    log(f"{action} FAILED after {RETRIES} attempts.")


def run_scheduler():
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
        getattr(schedule.every(), day).at(SIGNIN_TIME).do(punch_with_retry, "signin")
        getattr(schedule.every(), day).at(SIGNOUT_TIME).do(punch_with_retry, "signout")
    log(f"Scheduler running: sign in {SIGNIN_TIME}, sign out {SIGNOUT_TIME} (Mon-Fri, system time).")
    while True:
        schedule.run_pending()
        time.sleep(20)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "run":
        run_scheduler()
    elif mode in ("signin", "signout"):
        punch_with_retry(mode)
    else:
        sys.exit("Usage: python greythr_auto.py run | signin | signout")