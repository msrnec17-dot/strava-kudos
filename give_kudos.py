import json
import os
import time
from playwright.sync_api import sync_playwright

STATE_FILE = "strava_state.json"

def validate_state_file():
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(f"Datoteka {STATE_FILE} ne postoji.")

    if os.path.getsize(STATE_FILE) == 0:
        raise ValueError(f"Datoteka {STATE_FILE} je prazna.")

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("storage_state nije JSON objekt.")

    if "cookies" not in data or "origins" not in data:
        raise ValueError("storage_state nema očekivana polja 'cookies' i 'origins'.")

    print(f"STATE OK: cookies={len(data.get('cookies', []))}, origins={len(data.get('origins', []))}")

def click_visible_kudos(page, clicked_keys):
    buttons = page.locator("button[title*='kudos'], button[title*='Kudos']")
    count = buttons.count()
    clicked_now = 0

    for i in range(count):
        try:
            btn = buttons.nth(i)
            title = btn.get_attribute("title") or ""
            box = btn.bounding_box()
            if not box:
                continue

            key = f"{round(box['x'])}-{round(box['y'])}-{title}"
            if key in clicked_keys:
                continue

            btn.click(timeout=3000)
            clicked_keys.add(key)
            clicked_now += 1
            time.sleep(0.8)
        except Exception:
            pass

    return clicked_now

def main():
    validate_state_file()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)

        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        page.goto("https://www.strava.com/dashboard", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        current_url = page.url
        print(f"OPENED URL: {current_url}")

        if "login" in current_url.lower():
            raise RuntimeError("Strava session nije valjana. Otvorena je login stranica umjesto dashboarda.")

        clicked_keys = set()
        total_clicked = 0

        for round_num in range(8):
            clicked_now = click_visible_kudos(page, clicked_keys)
            total_clicked += clicked_now
            print(f"KRUG {round_num + 1}: kliknuto {clicked_now}, ukupno {total_clicked}")
            page.mouse.wheel(0, 2200)
            time.sleep(3)

        print(f"GOTOVO: ukupno kliknuto kudosa: {total_clicked}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
