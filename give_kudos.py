import json
import os
import sys
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

STATE_FILE = "strava_state.json"
FEED_URL = "https://www.strava.com/dashboard"

def log(msg):
    print(msg, flush=True)

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
        raise ValueError("storage_state nema polja 'cookies' i 'origins'.")
    log(f"STATE OK: cookies={len(data.get('cookies', []))}, origins={len(data.get('origins', []))}")

def dismiss_cookie_banner(page):
    try:
        # Strava cookie banner (ako se pojavi)
        btn = page.locator("button.btn-accept-cookie-banner, .cookie-banner button, [data-testid='accept-cookies-button']").first
        if btn.is_visible(timeout=2000):
            btn.click()
            time.sleep(1)
            log("Uklonjen cookie banner.")
    except Exception:
        pass

def get_btn_state(btn):
    try:
        title = (btn.get_attribute("title") or "").strip()
    except:
        title = ""
    try:
        aria = (btn.get_attribute("aria-label") or "").strip()
    except:
        aria = ""
    try:
        return title, aria, btn.locator("svg[data-testid='unfilled_kudos']").count() > 0, btn.locator("svg[data-testid='filled_kudos']").count() > 0
    except:
        return title, aria, False, False

def visible_candidates(page):
    buttons = page.locator("button[data-testid='kudos_button']")
    out = []
    seen = set()
    count = buttons.count()
    for i in range(count):
        try:
            btn = buttons.nth(i)
            if not btn.is_visible() or not btn.is_enabled():
                continue
            box = btn.bounding_box()
            if not box:
                continue
            key = f"{round(box['x'])}-{round(box['y'])}-{round(box['width'])}-{round(box['height'])}"
            if key in seen:
                continue
            seen.add(key)
            out.append(btn)
        except:
            pass
    return out

def click_visible_unfilled(page, clicked_keys):
    clicked_now = 0
    buttons = visible_candidates(page)
    log(f"Vidljivih kudos gumba: {len(buttons)}")
    for idx, btn in enumerate(buttons, start=1):
        try:
            box = btn.bounding_box()
            if not box:
                continue
            key = f"{round(box['x'])}-{round(box['y'])}"
            if key in clicked_keys:
                continue

            title, aria, unfilled, filled = get_btn_state(btn)
            log(f"Kandidat #{idx}: title='{title}', aria='{aria}', unfilled={unfilled}, filled={filled}")

            if not unfilled or filled:
                continue

            btn.scroll_into_view_if_needed(timeout=2000)
            time.sleep(0.3) # Malo duže čekanje da se UI smiri

            for attempt in range(3):
                try:
                    # Dodan hover prije klika da simuliramo ljudski mišem
                    btn.hover()
                    time.sleep(0.1)
                    btn.click(timeout=2500, force=(attempt > 0))
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)

            time.sleep(1.5 + random.uniform(0.3, 0.8))

            title2, aria2, unfilled2, filled2 = get_btn_state(btn)
            if filled2 or (not unfilled2) or "View all kudos" in title2:
                clicked_keys.add(key)
                clicked_now += 1
                log(f"STVARNI kudos dan #{clicked_now} u ovom prolazu")
            else:
                log(f"Klik nije potvrđen: title_after='{title2}', unfilled_after={unfilled2}, filled_after={filled2}")

        except Exception as e:
            log(f"Greška na kandidatu #{idx}: {e}")
    return clicked_now

def scan_scroll_cycle(page, clicked_keys, cycles=10):
    total = 0
    for c in range(cycles):
        log(f"--- ciklus {c+1}/{cycles} ---")
        dismiss_cookie_banner(page) # Za svaki slučaj
        clicked_now = click_visible_unfilled(page, clicked_keys)
        total += clicked_now
        log(f"Ciklus {c+1}: kliknuto {clicked_now}, ukupno {total}")
        page.mouse.wheel(0, 1600)
        time.sleep(2.5 + random.uniform(0.5, 1.2))
    return total

def final_sweep(page, clicked_keys, rounds=3):
    total = 0
    for r in range(rounds):
        log(f"Final sweep {r+1}/{rounds}")
        clicked_now = click_visible_unfilled(page, clicked_keys)
        total += clicked_now
        log(f"Final sweep {r+1}: kliknuto {clicked_now}, ukupno {total}")
        time.sleep(1.5)
    return total

def main():
    try:
        validate_state_file()

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            # Postavili smo user agent da izgleda više kao normalan korisnik
            context = browser.new_context(
                storage_state=STATE_FILE, 
                viewport={"width": 1440, "height": 1200},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
            )
            page = context.new_page()
            page.set_default_timeout(10000)

            page.goto(FEED_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(8) # Povećano vrijeme čekanja na početku

            if "login" in page.url.lower():
                raise RuntimeError("Session nije valjan, otvorena je login stranica.")

            dismiss_cookie_banner(page)

            clicked_keys = set()
            total_clicked = 0

            log("Počinjem glavni prolaz")
            total_clicked += scan_scroll_cycle(page, clicked_keys, cycles=10)

            log("Vraćam se malo gore za dodatni sweep")
            page.mouse.wheel(0, -2500)
            time.sleep(3)

            total_clicked += final_sweep(page, clicked_keys, rounds=5)

            log(f"GOTOVO. Ukupno stvarno kliknuto kudosa: {total_clicked}")

            context.close()
            browser.close()

    except PlaywrightTimeoutError as e:
        log(f"PLAYWRIGHT TIMEOUT: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"GREŠKA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()