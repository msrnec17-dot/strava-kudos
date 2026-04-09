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

def get_button_state(locator):
    try:
        title = locator.get_attribute("title") or ""
    except:
        title = ""

    try:
        aria = locator.get_attribute("aria-label") or ""
    except:
        aria = ""

    try:
        pressed = locator.get_attribute("aria-pressed") or ""
    except:
        pressed = ""

    try:
        cls = locator.get_attribute("class") or ""
    except:
        cls = ""

    return {
        "title": title,
        "aria": aria,
        "pressed": pressed,
        "class": cls
    }

def state_signature(state):
    return f"{state['title']}|{state['aria']}|{state['pressed']}|{state['class']}"

def looks_already_kudosed(state):
    text = f"{state['title']} {state['aria']} {state['class']} {state['pressed']}".lower()
    return (
        "kudos given" in text or
        "given kudos" in text or
        "remove kudos" in text or
        "un-kudo" in text or
        "unkudo" in text or
        state["pressed"] == "true"
    )

def state_changed(before, after):
    return state_signature(before) != state_signature(after)

def find_kudos_candidates(page):
    selectors = [
        "button[title*='kudos']",
        "button[aria-label*='kudos']",
        "[role='button'][title*='kudos']",
        "[role='button'][aria-label*='kudos']",
        "button:has(svg)",
        "[role='button']:has(svg)"
    ]

    candidates = []
    seen = set()

    for selector in selectors:
        try:
            loc = page.locator(selector)
            count = loc.count()
            log(f"Selector '{selector}' -> pronađeno {count}")

            for i in range(count):
                try:
                    el = loc.nth(i)

                    if not el.is_visible():
                        continue

                    box = el.bounding_box()
                    if not box:
                        continue

                    if box["width"] < 20 or box["height"] < 20:
                        continue

                    key = f"{round(box['x'])}-{round(box['y'])}-{round(box['width'])}-{round(box['height'])}"
                    if key in seen:
                        continue

                    seen.add(key)
                    candidates.append(el)
                except:
                    pass
        except:
            pass

    return candidates

def click_real_kudos(page, clicked_keys):
    log("Tražim stvarne kudos gumbe")
    candidates = find_kudos_candidates(page)
    log(f"Ukupno kandidata nakon filtriranja: {len(candidates)}")

    clicked_now = 0

    for idx, btn in enumerate(candidates):
        try:
            box = btn.bounding_box()
            if not box:
                continue

            key = f"{round(box['x'])}-{round(box['y'])}"
            if key in clicked_keys:
                continue

            before = get_button_state(btn)

            if looks_already_kudosed(before):
                continue

            btn.scroll_into_view_if_needed(timeout=2000)
            time.sleep(0.3)

            try:
                btn.click(timeout=3000)
            except Exception:
                try:
                    btn.click(timeout=5000, force=True)
                except Exception:
                    continue

            time.sleep(1.2)

            after = get_button_state(btn)

            if state_changed(before, after) or looks_already_kudosed(after):
                clicked_keys.add(key)
                clicked_now += 1
                log(f"STVARNI kudos kliknut #{clicked_now} u ovom krugu")
            else:
                log(f"Kandidat #{idx + 1} kliknut ali bez potvrđene promjene stanja")

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
            time.sleep(6)

            current_url = page.url
            log(f"8. Trenutni URL: {current_url}")

            if "login" in current_url.lower():
                raise RuntimeError("Session nije valjan, otvorena je login stranica.")

            clicked_keys = set()
            total_clicked = 0

            for round_num in range(8):
                log(f"9. Počinje krug {round_num + 1}")
                clicked_now = click_real_kudos(page, clicked_keys)
                total_clicked += clicked_now
                log(f"10. Krug {round_num + 1} gotov, stvarno kliknuto {clicked_now}, ukupno {total_clicked}")

                log("11. Scrollam dalje")
                page.mouse.wheel(0, 2200)
                time.sleep(3)

            log(f"12. GOTOVO. Ukupno stvarno kliknuto kudosa: {total_clicked}")

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
