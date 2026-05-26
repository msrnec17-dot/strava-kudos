import csv
import os
import random
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

LOG_PATH = Path("output/kudos_log.csv")
MAX_KUDOS = 40
MAX_ROUNDS = 14
FINAL_SWEEPS = 4
MAX_IDLE_PASSES = 4
DASHBOARD_URL = "https://www.strava.com/dashboard"


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
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            user,
            status,
            details,
        ])


def human_pause(min_s, max_s):
    time.sleep(random.uniform(min_s, max_s))


def clean_name(text):
    if not text:
        return ""

    text = " ".join(text.split()).strip()
    bad_values = {
        "",
        "give kudos",
        "be the first to give kudos!",
        "view all kudos",
        "kudos",
        "comment",
        "share",
        "more",
        "view all comments",
    }

    if text.lower() in bad_values:
        return ""

    return text


def get_card_name(card):
    selectors = [
        "a[data-testid='owners-name']",
        "header a[data-testid='owners-name']",
        "a[href*='/athletes/']",
        "header a[href*='/athletes/']",
    ]

    for selector in selectors:
        try:
            loc = card.locator(selector).first
            if loc.count() > 0:
                txt = clean_name(loc.inner_text(timeout=1000))
                if txt:
                    return txt
        except Exception:
            pass

    try:
        text = clean_name(card.inner_text(timeout=1000))
        if text:
            return text.split("\n")[0][:120]
    except Exception:
        pass

    return "UNKNOWN_USER"


def detect_button_state(button):
    try:
        title = (button.get_attribute("title") or "").strip()
    except Exception:
        title = ""

    try:
        aria_pressed = (button.get_attribute("aria-pressed") or "").strip().lower()
    except Exception:
        aria_pressed = ""

    try:
        disabled_attr = button.get_attribute("disabled")
        disabled = disabled_attr is not None
    except Exception:
        disabled = False

    title_lower = title.lower()

    if aria_pressed == "true":
        return "filled", title, aria_pressed

    if "view all kudos" in title_lower:
        return "filled", title, aria_pressed

    if "give kudos" in title_lower or "be the first to give kudos!" in title_lower:
        return "unfilled", title, aria_pressed

    if disabled:
        return "unknown", title, aria_pressed

    return "unknown", title, aria_pressed


def get_kudos_buttons(page):
    selectors = [
        "[data-testid='kudos_button']",
        "button[title='Give kudos']",
        "button[title='Be the first to give kudos!']",
        "button[title='View all kudos']",
        "button[aria-label*='kudos' i]",
    ]

    seen = set()
    buttons = []

    for selector in selectors:
        try:
            loc = page.locator(selector)
            count = loc.count()
            for i in range(count):
                btn = loc.nth(i)
                try:
                    if not btn.is_visible(timeout=500):
                        continue

                    box = btn.bounding_box()
                    if not box:
                        continue

                    key = (
                        round(box["x"], 1),
                        round(box["y"], 1),
                        round(box["width"], 1),
                        round(box["height"], 1),
                    )
                    if key in seen:
                        continue

                    seen.add(key)
                    buttons.append(btn)
                except Exception:
                    continue
        except Exception:
            continue

    return buttons


def find_card_for_button(button):
    xpath_candidates = [
        "xpath=ancestor::article[1]",
        "xpath=ancestor::*[@data-testid='web-feed-entry'][1]",
        "xpath=ancestor::*[contains(@class,'react-card')][1]",
        "xpath=ancestor::*[contains(@class,'feed-entry')][1]",
    ]

    for xp in xpath_candidates:
        try:
            loc = button.locator(xp)
            if loc.count() > 0:
                return loc.first
        except Exception:
            pass

    return None


def wait_for_kudos_confirmation(button, timeout_ms=4000):
    end_time = time.time() + (timeout_ms / 1000)
    while time.time() < end_time:
        state, title, aria = detect_button_state(button)
        if state == "filled":
            return True, title, aria
        human_pause(0.15, 0.35)
    state, title, aria = detect_button_state(button)
    return False, title, aria


def click_button_human_like(button):
    box = button.bounding_box()
    if box:
        x = box["x"] + box["width"] * random.uniform(0.35, 0.65)
        y = box["y"] + box["height"] * random.uniform(0.35, 0.65)
        button.page.mouse.move(x, y, steps=random.randint(8, 20))
        human_pause(0.08, 0.22)


def try_click_button(button, user):
    state_before, title_before, aria_before = detect_button_state(button)

    if state_before == "filled":
        append_to_log(user, "already_kudoed", f"title={title_before}; aria={aria_before}")
        return False

    if state_before == "unknown":
        append_to_log(user, "unknown_button_state", f"title={title_before}; aria={aria_before}")
        return False

    try:
        button.scroll_into_view_if_needed(timeout=2500)
    except Exception:
        pass

    human_pause(0.45, 1.1)

    try:
        click_button_human_like(button)
    except Exception:
        pass

    click_errors = []

    try:
        button.click(timeout=3500)
    except PlaywrightTimeoutError as e:
        click_errors.append(f"timeout:{e}")
    except Exception as e:
        click_errors.append(f"{type(e).__name__}:{e}")

    human_pause(0.45, 0.9)

    confirmed, title_after, aria_after = wait_for_kudos_confirmation(button, timeout_ms=3500)
    if confirmed:
        append_to_log(user, "clicked", f"title_before={title_before}; title_after={title_after}")
        print(f"Klik potvrđen: {user}")
        return True

    try:
        button.click(timeout=3500, force=True)
    except Exception as e:
        click_errors.append(f"force_{type(e).__name__}:{e}")

    human_pause(0.5, 1.1)

    confirmed, title_after, aria_after = wait_for_kudos_confirmation(button, timeout_ms=4000)
    if confirmed:
        append_to_log(user, "clicked", f"title_before={title_before}; title_after={title_after}; mode=force")
        print(f"Klik potvrđen (force): {user}")
        return True

    append_to_log(
        user,
        "click_not_confirmed",
        f"title_before={title_before}; aria_before={aria_before}; title_after={title_after}; aria_after={aria_after}; errors={' | '.join(click_errors)}",
    )
    print(f"Klik nije potvrđen: {user} | after={title_after}")
    return False


def get_cumulative_stats():
    ensure_log_file()

    total_clicked_all_time = 0
    clicks_by_user = Counter()
    runs_finished = 0
    runs_without_clicks = 0
    statuses = Counter()

    try:
        with LOG_PATH.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user = (row.get("user") or "UNKNOWN_USER").strip()
                status = (row.get("status") or "").strip()
                details = (row.get("details") or "").strip()

                if not status:
                    continue

                statuses[status] += 1

                if status == "clicked":
                    total_clicked_all_time += 1
                    clicks_by_user[user] += 1

                if user == "SYSTEM" and status == "summary" and "Run finished" in details:
                    runs_finished += 1

                if user == "SYSTEM" and status == "no_clicks":
                    runs_without_clicks += 1

    except Exception as e:
        print(f"Greška pri čitanju kumulativne statistike: {e}")

    top_users = clicks_by_user.most_common(20)

    return {
        "total_clicked_all_time": total_clicked_all_time,
        "clicks_by_user": clicks_by_user,
        "top_users": top_users,
        "runs_finished": runs_finished,
        "runs_without_clicks": runs_without_clicks,
        "statuses": statuses,
    }


def build_telegram_message(total_clicked, unique_names, run_clicks_by_user, cumulative_stats):
    lines = []
    lines.append("Strava bot je završio.")
    lines.append("")
    lines.append("📊 U OVOM RUNU:")
    lines.append(f"Podijeljeno kudosa: {total_clicked}")

    if unique_names:
        lines.append(f"Broj korisnika koji su dobili kudos: {len(unique_names)}")
        lines.append("Korisnici:")
        for user, count in run_clicks_by_user.most_common(20):
            if count == 1:
                lines.append(f"- {user}: 1 kudos")
            else:
                lines.append(f"- {user}: {count} kudosa")
    else:
        lines.append("Nije pronađena nijedna nova aktivnost za kudos.")

    lines.append("")
    lines.append("📈 UKUPNO:")
    lines.append(f"Ukupno podijeljenih kudosa ikad: {cumulative_stats['total_clicked_all_time']}")
    lines.append(f"Ukupno završenih runova: {cumulative_stats['runs_finished']}")
    lines.append(f"Runovi bez klikova: {cumulative_stats['runs_without_clicks']}")

    if cumulative_stats["top_users"]:
        lines.append("")
        lines.append("🏆 TOP 20 KORISNIKA PO UKUPNOM BROJU KUDOSA:")
        for user, count in cumulative_stats["top_users"]:
            if count == 1:
                lines.append(f"- {user}: 1 kudos")
            else:
                lines.append(f"- {user}: {count} kudosa")

    return "\n".join(lines)


def send_telegram_report(total_clicked, kudos_names):
    tel_token = os.environ.get("TELEGRAM_TOKEN")
    tel_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not tel_token or not tel_chat_id:
        print("Telegram token/chat id nisu postavljeni.")
        return

    unique_names = []
    for name in kudos_names:
        if name not in unique_names:
            unique_names.append(name)

    run_clicks_by_user = Counter(kudos_names)
    cumulative_stats = get_cumulative_stats()
    message = build_telegram_message(
        total_clicked=total_clicked,
        unique_names=unique_names,
        run_clicks_by_user=run_clicks_by_user,
        cumulative_stats=cumulative_stats,
    )

    try:
        url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": tel_chat_id,
            "text": message,
        }).encode("utf-8")
        urllib.request.urlopen(url, data=data, timeout=20)
        print("Telegram izvješće uspješno poslano.")
    except Exception as e:
        print(f"Greška pri slanju Telegram poruke: {e}")


def process_visible_buttons(page, label, total_clicked, kudos_names, seen_users):
    clicked_this_pass = 0
    buttons = get_kudos_buttons(page)

    print(f"{label} | Vidljivih kudos gumba: {len(buttons)}")

    for idx, button in enumerate(buttons, start=1):
        if total_clicked >= MAX_KUDOS:
            break

        try:
            card = find_card_for_button(button)
            if card is None:
                append_to_log("UNKNOWN_USER", "no_button", "button without matching card")
                continue

            user = get_card_name(card)
            state, title, aria = detect_button_state(button)

            print(f"Kandidat {idx} | user={user} | title={title} | aria={aria} | state={state}")

            if user in seen_users and state != "unfilled":
                continue

            if state == "filled":
                append_to_log(user, "already_kudoed", f"title={title}; aria={aria}")
                seen_users.add(user)
                continue

            if state == "unknown":
                append_to_log(user, "unknown_button_state", f"title={title}; aria={aria}")
                continue

            success = try_click_button(button, user)
            seen_users.add(user)

            if success:
                total_clicked += 1
                clicked_this_pass += 1
                kudos_names.append(user)

            human_pause(0.9, 2.2)

        except Exception as e:
            append_to_log("UNKNOWN_USER", "click_error", f"loop_error: {type(e).__name__}: {e}")
            print(f"Greška u prolazu: {e}")

    return total_clicked, kudos_names, clicked_this_pass, seen_users


def main():
    ensure_log_file()
    print("POČETAK SKRIPTE")

    total_clicked = 0
    kudos_names = []
    idle_passes = 0
    seen_users = set()

    append_to_log("SYSTEM", "summary", "Run started")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            storage_state="strava_state.json",
            viewport={"width": 1600, "height": 2200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) "
                "Gecko/20100101 Firefox/110.0"
            ),
        )
        page = context.new_page()

        print("Otvaram dashboard...")
        page.goto(DASHBOARD_URL, wait_until="domcontentloaded")
        human_pause(5.0, 7.5)

        for round_num in range(1, MAX_ROUNDS + 1):
            if total_clicked >= MAX_KUDOS:
                break

            print(f"--- ciklus {round_num}/{MAX_ROUNDS} ---")
            total_clicked, kudos_names, clicked_this_round, seen_users = process_visible_buttons(
                page,
                f"Ciklus {round_num}",
                total_clicked,
                kudos_names,
                seen_users,
            )

            print(f"Ciklus {round_num} kliknuto {clicked_this_round}, ukupno {total_clicked}")
            append_to_log(
                "SYSTEM",
                "cycle_summary",
                f"cycle={round_num}; clicked_this_cycle={clicked_this_round}; total_clicked={total_clicked}"
            )

            if clicked_this_round == 0:
                idle_passes += 1
            else:
                idle_passes = 0

            if total_clicked >= MAX_KUDOS:
                break

            if idle_passes >= MAX_IDLE_PASSES:
                print(f"Nema novih potvrđenih klikova već {idle_passes} prolaza, prekidam glavni dio.")
                break

            try:
                page.mouse.wheel(0, random.randint(1400, 2400))
            except Exception:
                pass

            human_pause(2.5, 4.8)

        for sweep_num in range(1, FINAL_SWEEPS + 1):
            if total_clicked >= MAX_KUDOS:
                break

            print(f"Final sweep {sweep_num}/{FINAL_SWEEPS}")
            total_clicked, kudos_names, clicked_this_sweep, seen_users = process_visible_buttons(
                page,
                f"Final sweep {sweep_num}",
                total_clicked,
                kudos_names,
                seen_users,
            )

            print(f"Final sweep {sweep_num} kliknuto {clicked_this_sweep}, ukupno {total_clicked}")
            append_to_log(
                "SYSTEM",
                "sweep_summary",
                f"sweep={sweep_num}; clicked_this_sweep={clicked_this_sweep}; total_clicked={total_clicked}"
            )

            if total_clicked >= MAX_KUDOS:
                break

            try:
                page.mouse.wheel(0, random.randint(700, 1200))
            except Exception:
                pass

            human_pause(2.0, 3.6)

        browser.close()

    if total_clicked == 0:
        append_to_log("SYSTEM", "no_clicks", "No kudos buttons were successfully clicked in this run")

    unique_names = []
    for name in kudos_names:
        if name not in unique_names:
            unique_names.append(name)

    append_to_log(
        "SYSTEM",
        "summary",
        f"Run finished; total_clicked={total_clicked}; unique_users={len(unique_names)}"
    )

    send_telegram_report(total_clicked, unique_names if unique_names else kudos_names)

    print(f"Ukupno kliknutih kudosa: {total_clicked}")
    print("KRAJ SKRIPTE")


if __name__ == "__main__":
    main()
