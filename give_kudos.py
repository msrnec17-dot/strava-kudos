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


def get_card_name(card):
    name_selectors = [
        "a[data-testid='owners-name']",
        "a[href*='/athletes/']",
        "header a[data-testid='owners-name']",
        "header a[href*='/athletes/']",
    ]

    for selector in name_selectors:
        try:
            loc = card.locator(selector).first
            if loc.count() > 0:
                txt = clean_name(loc.inner_text(timeout=1000))
                if txt:
                    return txt
        except Exception:
            pass

    return "Nepoznato ime"


def get_card_kudos_button(card):
    button_selectors = [
        "[data-testid='kudos_button']",
        "button[title='Give kudos']",
        "button[title='Be the first to give kudos!']",
    ]

    for selector in button_selectors:
        try:
            loc = card.locator(selector).first
            if loc.count() > 0:
                return loc
        except Exception:
            pass

    return None


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

        names_str = ", ".join(unique_names)

        message = (
            f"Strava bot je završio | "
            f"Podijeljeno kudosa: {total_clicked} | "
            f"Korisnici: {names_str}"
        )
    else:
        message = "Strava bot je završio | Nije pronađena nijedna nova aktivnost za kudos."

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

        for round_num in range(3):
            if stop:
                break

            print(f"\nKrug {round_num + 1} – tražim aktivnosti...")

            card_selectors = [
                "[data-testid='web-feed-entry']",
                "article",
                ".react-card",
                ".feed-entry",
            ]

            cards = None
            card_count = 0

            for selector in card_selectors:
                try:
                    loc = page.locator(selector)
                    count = loc.count()
                    if count > 0:
                        cards = loc
                        card_count = count
                        print(f"Našao {count} aktivnosti preko selektora: {selector}")
                        break
                except Exception:
                    pass

            if not cards or card_count == 0:
                print("Nisam našao nijednu aktivnost u feedu.")
                break

            for i in range(card_count):
                if total_clicked >= MAX_KUDOS:
                    print(f"Dosegnut limit od {MAX_KUDOS} kudosa – prekidam.")
                    stop = True
                    break

                try:
                    card = cards.nth(i)
                    card.scroll_into_view_if_needed()
                    time.sleep(random.uniform(0.5, 1.2))

                    athlete_name = get_card_name(card)
                    btn = get_card_kudos_button(card)

                    if btn is None:
                        print(f"  Aktivnost {i + 1}: nema dostupnog kudos gumba.")
                        continue

                    try:
                        aria_pressed = btn.get_attribute("aria-pressed")
                        if aria_pressed == "true":
                            print(f"  Aktivnost {i + 1}: {athlete_name} već ima kudos.")
                            continue
                    except Exception:
                        pass

                    try:
                        button_title = btn.get_attribute("title") or ""
                        if "Give kudos" not in button_title and "Be the first to give kudos!" not in button_title:
                            print(f"  Aktivnost {i + 1}: kudos gumb nije aktivan za {athlete_name}.")
                            continue
                    except Exception:
                        pass

                    pre_pause = random.uniform(0.8, 1.8)
                    time.sleep(pre_pause)

                    btn.click(timeout=3000)
                    total_clicked += 1
                    kudos_names.append(athlete_name)

                    print(
                        f"  Kliknuo kudos za: {athlete_name} "
                        f"(ukupno kliknuto: {total_clicked})"
                    )

                    post_pause = random.uniform(1.0, 2.5)
                    time.sleep(post_pause)

                except Exception as e:
                    print(f"  Preskačem aktivnost {i + 1} (greška: {e})")

            if stop:
                break

            scroll_amount = random.randint(1200, 2200)
            print(f"Kraj kruga {round_num + 1}, skrolam za {scroll_amount} px...")
            page.mouse.wheel(0, scroll_amount)
            time.sleep(random.uniform(2.0, 4.0))

        print(f"\nGotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()

    send_telegram_report(total_clicked, kudos_names)
    print("KRAJ SKRIPTE")


if __name__ == "__main__":
    main()
