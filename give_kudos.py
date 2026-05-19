import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE_FILE = "strava_state.json"
LOG_PATH = Path("output/kudos_log.csv")
STRAVA_DASHBOARD_URL = "https://www.strava.com/dashboard"


def ensure_log_file():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "user", "status", "details"])


def append_to_log(user, status, details=""):
    ensure_log_file()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                user,
                status,
                details,
            ]
        )


def send_telegram_message(message: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram token/chat_id nije postavljen, preskačem slanje poruke.")
        return

    try:
        import urllib.parse
        import urllib.request

        data = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": message,
            }
        ).encode("utf-8")

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                print("Telegram izvješće uspješno poslano.")
            else:
                print(f"Telegram slanje nije uspjelo. HTTP {response.status}")
    except Exception as e:
        print(f"Greška pri slanju Telegram poruke: {e}")


def get_activity_name(activity):
    candidates = [
        "[data-testid='entry-header'] a",
        "header a",
        "a[href*='/activities/']",
        "strong",
    ]

    for selector in candidates:
        try:
            loc = activity.locator(selector).first
            if loc.count() > 0:
                text = loc.inner_text().strip()
                if text:
                    return text
        except Exception:
            pass

    return "UNKNOWN_USER"


def find_kudos_button(activity):
    selectors = [
        "button[title*='Give kudos']",
        "button[title*='Be the first to give kudos']",
        "button[aria-label*='Give kudos']",
        "button[aria-label*='Be the first to give kudos']",
        "button[title*='View all kudos']",
        "button[aria-label*='View all kudos']",
    ]

    for selector in selectors:
        try:
            loc = activity.locator(selector).first
            if loc.count() > 0:
                return loc
        except Exception:
            pass

    return None


def button_state(btn):
    try:
        title = (btn.get_attribute("title") or "").strip()
    except Exception:
        title = ""

    try:
        aria = (btn.get_attribute("aria-label") or "").strip()
    except Exception:
        aria = ""

    try:
        disabled = btn.is_disabled()
    except Exception:
        disabled = False

    text = f"{title} {aria}".lower()

    is_filled = "view all kudos" in text
    is_unfilled = ("give kudos" in text) or ("be the first to give kudos" in text)

    return {
        "title": title,
        "aria": aria,
        "disabled": disabled,
        "is_filled": is_filled,
        "is_unfilled": is_unfilled,
    }


def run():
    ensure_log_file()

    print("POČETAK SKRIPTE")

    total_clicked = 0
    scan_count = 0

    with sync_playwright() as p:
        print("Pokrećem Firefox (headless)...")
        browser = p.firefox.launch(headless=True)

        print(f"Kreiram Strava kontekst sa {STATE_FILE}...")
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        print("Otvaram Strava dashboard...")
        page.goto(STRAVA_DASHBOARD_URL, wait_until="domcontentloaded", timeout=120000)

        print("Čekam 4.5 s da se feed učita...")
        page.wait_for_timeout(4500)

        for cycle in range(1, 4):
            scan_count += 1
            print(f"Krug {cycle} – tražim aktivnosti...")

            activities = page.locator("[data-testid='web-feed-entry']")
            activity_count = activities.count()
            print(f"Našao {activity_count} aktivnosti preko selektora: [data-testid='web-feed-entry']")

            cycle_clicked = 0

            for i in range(activity_count):
                activity = activities.nth(i)
                user_name = get_activity_name(activity)
                btn = find_kudos_button(activity)

                if btn is None:
                    print(f"Aktivnost {i + 1}: nema dostupnog kudos gumba.")
                    append_to_log(user_name, "no_button", "Kudos button not found")
                    continue

                state_before = button_state(btn)

                if state_before["disabled"]:
                    print(f"Aktivnost {i + 1}: kudos gumb nije aktivan za {user_name}.")
                    append_to_log(user_name, "disabled", "Button is disabled")
                    continue

                if state_before["is_filled"]:
                    print(f"Aktivnost {i + 1}: već ima kudos za {user_name}.")
                    append_to_log(user_name, "already_kudoed", "Button already filled")
                    continue

                if not state_before["is_unfilled"]:
                    print(f"Aktivnost {i + 1}: nema dostupnog kudos gumba.")
                    append_to_log(user_name, "unknown_button_state", "Button found but state is unclear")
                    continue

                try:
                    btn.scroll_into_view_if_needed(timeout=5000)
                    page.wait_for_timeout(250)
                    btn.click(timeout=5000, force=True)
                    page.wait_for_timeout(1200)

                    state_after = button_state(btn)

                    if state_after["is_filled"]:
                        print(f"Aktivnost {i + 1}: kliknuo kudos za {user_name}.")
                        append_to_log(user_name, "clicked", "Kudos click confirmed")
                        total_clicked += 1
                        cycle_clicked += 1
                    else:
                        print(f"Aktivnost {i + 1}: klik nije potvrđen za {user_name}.")
                        append_to_log(
                            user_name,
                            "click_not_confirmed",
                            f"title={state_after['title']} aria={state_after['aria']}",
                        )
                except Exception as e:
                    print(f"Aktivnost {i + 1}: greška pri kliku za {user_name}: {e}")
                    append_to_log(user_name, "click_error", str(e))

            scroll_px = 1600 + (cycle * 150)
            print(f"Kraj kruga {cycle}, skrolam za {scroll_px} px...")
            page.mouse.wheel(0, scroll_px)
            page.wait_for_timeout(2500)

        print(f"Gotovo. Ukupno kliknuto kudosa: {total_clicked}")

        if total_clicked == 0:
            append_to_log("SYSTEM", "no_clicks", "No kudos buttons were successfully clicked in this run")
        else:
            append_to_log("SYSTEM", "summary", f"Total clicked: {total_clicked}")

        summary_message = (
            "Strava kudos izvješće\n"
            f"- Pregledanih krugova: {scan_count}\n"
            f"- Ukupno kliknuto kudosa: {total_clicked}"
        )
        send_telegram_message(summary_message)

        context.close()
        browser.close()

    print("KRAJ SKRIPTE")


if __name__ == "__main__":
    run()
