import json
import os
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

STATE_FILE = "strava_state.json"

def log(msg):
    print(msg, flush=True)

def validate_state_file():
    log("1. Provjeravam strava_state.json")

    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(f"Datoteka {STATE_FILE} ne postoji.")

    if os.path.getsize(STATE_FILE) == 0:
        raise ValueError(f"Datoteka {STATE_FILE} je prazna.")

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("storage_state nije JSON objekt.")

    if "cookies" not in data or "origins" not in data:
        raise ValueError("storage_state nema polja 'cookies' i 'origins'.")

    log(f"2. STATE OK: cookies={len(data.get('cookies', []))}, origins={len(data.get('origins', []))}")

def click_visible_kudos(page, clicked_keys):
    log("7. Tražim kudos gumbe na trenutno vidljivom dijelu stranice")
    buttons = page.locator("button[title*='kudos'], button[title*='Kudos']")
    count = buttons.count()
    log(f"8. Pronađeno gumba: {count}")

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

            btn.click(timeout=2000)
            clicked_keys.add(key)
            clicked_now += 1
            log(f"9. Kliknut kudos #{clicked_now} u ovom krugu")
            time.sleep(0.5)
        except Exception:
            pass

    return clicked_now

def main():
    try:
        validate_state_file()

        log("3. Pokrećem Playwright")
        with sync_playwright() as p:
            log("4. Launch Firefox headless")
            browser = p.firefox.launch(headless=True)

            log("5. Kreiram browser context iz storage state")
            context = browser.new_context(storage_state=STATE_FILE)

            log("6. Otvaram novu stranicu")
            page = context.new_page()
            page.set_default_timeout(10000)

            log("7. Idem na Strava dashboard")
            page.goto("https://www.strava.com/dashboard", wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            current_url = page.url
            log(f"8. Trenutni URL: {current_url}")

            if "login" in current_url.lower():
                raise RuntimeError("Session nije valjan, otvorena je login stranica.")

            clicked_keys = set()
            total_clicked = 0

            for round_num in range(5):
                log(f"9. Počinje krug {round_num + 1}")
                clicked_now = click_visible_kudos(page, clicked_keys)
                total_clicked += clicked_now
                log(f"10. Krug {round_num + 1} gotov, kliknuto {clicked_now}, ukupno {total_clicked}")

                log("11. Scrollam dalje")
                page.mouse.wheel(0, 1800)
                time.sleep(2)

            log(f"12. GOTOVO. Ukupno kliknuto kudosa: {total_clicked}")

            context.close()
            browser.close()
            log("13. Browser zatvoren")

    except PlaywrightTimeoutError as e:
        log(f"PLAYWRIGHT TIMEOUT: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"GREŠKA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
