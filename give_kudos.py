import time
import random
import os
import urllib.request
import urllib.parse
from playwright.sync_api import sync_playwright

MAX_KUDOS = 60


def clean_name(text):
    if not text:
        return ""
    text = " ".join(text.split()).strip()
    bad_values = {
        "", "give kudos", "be the first to give kudos!", "kudos",
        "comment", "share", "more", "view all comments"
    }
    if text.lower() in bad_values:
        return ""
    return text


def get_athlete_name_from_button(btn):
    card = btn.locator(
        "xpath=ancestor::*["
        "contains(@class, 'react-card') or "
        "contains(@class, 'feed-entry') or "
        "contains(@class, 'FeedEntry') or "
        "self::article"
        "][1]"
    )

    candidate_selectors = [
        "a[data-testid='owners-name']",
        "header a[data-testid='owners-name']",
        "a[href*='/athletes/']",
        "header a[href*='/athletes/']",
        ".entry-owner",
        ".minimal-user",
        ".avatar-athlete-name",
        "strong a",
        "h3 a",
    ]

    for selector in candidate_selectors:
        try:
            loc = card.locator(selector).first
            if loc.count() > 0:
                txt = clean_name(loc.inner_text(timeout=1000))
                if txt:
                    return txt
        except Exception:
            pass

    fallback_selectors = [
        "header",
        ".entry-head",
        ".activity-header",
        ".feed-entry__header",
        "h3",
        "strong",
    ]

    for selector in fallback_selectors:
        try:
            loc = card.locator(selector).first
            if loc.count() > 0:
                txt = clean_name(loc.inner_text(timeout=1000))
                if txt:
                    first_line = txt.split("\n")[0].strip()
                    first_line = clean_name(first_line)
                    if first_line:
                        return first_line
        except Exception:
            pass

    return "Nepoznato ime"


def send_telegram_report(total_clicked, kudos_names):
    tel_token = os.environ.get("TELEGRAM_TOKEN")
    tel_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not tel_token or not tel_chat_id:
        print("Telegram token/chat id nisu postavljeni.")
        return

    if total_clicked > 0:
        unique_names = []
        for name in kudos_names:
            if name not in unique_names:
                unique_names.append(name)

        if len(unique_names) > 30:
            names_str = "\n".join(f"- {name}" for name in unique_names[:30])
            names_str += f"\n... i još {len(unique_names) - 30} osoba"
        else:
            names_str = "\n".join(f"- {name}" for name in unique_names)

        message = (
            f"Strava bot je završio.\n\n"
            f"Podijeljeno kudosa: {total_clicked}\n\n"
            f"Kudose su dobili:\n{names_str}"
        )
    else:
        message = (
            "Strava bot je završio.\n\n"
            "Nije pronađena nijedna nova aktivnost za kudos."
        )

    try:
        url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": tel_chat_id,
            "text": message
        }).encode("utf-8")
        urllib.request.urlopen(url, data=data, timeout=10)
        print("Telegram izvješće uspješno poslano.")
    except Exception as e:
        print(f"Greška pri slanju Telegram poruke: {e}")


def main():
    print("POČETAK SKRIPTE")
    kudos_names = []

    with sync_playwright() as p:
        print("Pokrećem Firefox (headless)...")
        browser = p.firefox.launch(headless=True)

        print("Kreiram Strava kontekst sa strava_state.json...")
        context = browser.new_context(
            storage_state="strava_state.json",
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) "
                "Gecko/20100101 Firefox/110.0"
            ),
        )

        page = context.new_page()

        print("Otvaram Strava dashboard...")
        page.goto("https://www.strava.com/dashboard", wait_until="networkidle")

        pause = random.uniform(4.0, 6.0)
        print(f"Čekam {pause:.1f} s da se feed učita...")
        time.sleep(pause)

        total_clicked = 0
        stop = False

        for round_num in range(6):
            if stop:
                break

            print(f"\nKrug {round_num + 1} – tražim kudose...")

            buttons = page.locator(
                "button[title='Give kudos'], "
                "button[title='Be the first to give kudos!']"
            )
            count = buttons.count()
            print(f"Našao {count} kudos gumba u ovom krugu")

            for i in range(count):
                if total_clicked >= MAX_KUDOS:
                    print(f"Dosegnut limit od {MAX_KUDOS} kudosa – prekidam.")
                    stop = True
                    break

                try:
                    btn = buttons.nth(i)
                    btn.scroll_into_view_if_needed()

                    pre_pause = random.uniform(0.8, 2.0)
                    time.sleep(pre_pause)

                    athlete_name = get_athlete_name_from_button(btn)

                    btn.click(timeout=3000)
                    total_clicked += 1
                    kudos_names.append(athlete_name)

                    print(
                        f"  Kliknuo gumb {i + 1} za: {athlete_name} "
                        f"(ukupno kliknuto: {total_clicked})"
                    )

                    post_pause = random.uniform(1.0, 3.0)
                    time.sleep(post_pause)

                except Exception as e:
                    print(f"  Preskačem gumb {i + 1} (greška: {e})")

            if stop:
                break

            scroll_amount = random.randint(1000, 1800)
            print(f"Kraj kruga {round_num + 1}, skrolam za {scroll_amount} px...")
            page.mouse.wheel(0, scroll_amount)

            scroll_pause = random.uniform(2.0, 4.0)
            time.sleep(scroll_pause)

        print(f"\nGotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()

    send_telegram_report(total_clicked, kudos_names)
    print("KRAJ SKRIPTE")


if __name__ == "__main__":
    main()
