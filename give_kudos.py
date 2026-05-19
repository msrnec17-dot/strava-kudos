import time
import random
from playwright.sync_api import sync_playwright

# Maksimalan broj kudosa po jednom pokretanju skripte
MAX_KUDOS = 60


def main():
    with sync_playwright() as p:
        # Firefox u headless modu za GitHub Actions
        browser = p.firefox.launch(headless=True)

        # Kontekst sa snimljenom Strava sesijom
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

        # Početno nasumično čekanje – kao da prvo malo gledaš feed
        time.sleep(random.uniform(7.0, 12.0))

        total_clicked = 0
        stop = False

        # Prolazimo kroz nekoliko krugova skrolanja po feedu
        for round_num in range(3):
            if stop:
                break

            print(f"Krug {round_num + 1} – tražim kudose...")

            # Gumbi za davanje kudosa
            buttons = page.locator(
                "button[title='Give kudos'], "
                "button[title='Be the first to give kudos!']"
            )
            count = buttons.count()
            print(f"Našao {count} kudos gumba")

            for i in range(count):
                if total_clicked >= MAX_KUDOS:
                    print(
                        f"Dosegnut sigurni limit od {MAX_KUDOS} kudosa "
                        "u ovom runu – prekidam."
                    )
                    stop = True
                    break

                try:
                    btn = buttons.nth(i)

                    # Malo skrolaj do gumba i "čitaj" aktivnost prije klika
                    btn.scroll_into_view_if_needed()
                    time.sleep(random.uniform(1.5, 4.5))

                    # Klik na kudos
                    btn.click(timeout=3000)
                    total_clicked += 1
                    print(
                        f"  Kliknuo gumb {i + 1} "
                        f"(ukupno kliknuto: {total_clicked})"
                    )

                    # Pauza nakon klika, kao da gledaš sljedeću aktivnost
                    time.sleep(random.uniform(2.0, 6.0))

                except Exception as e:
                    print(f"  Preskačem gumb {i + 1} (greška: {e})")

            if stop:
                break

            # Nasumičan skrol – kao da pomakneš kotačić miša
            scroll_amount = random.randint(1200, 2500)
            page.mouse.wheel(0, scroll_amount)

            # Pričekaj da se učitaju nove aktivnosti i slike
            time.sleep(random.uniform(4.0, 8.0))

        print(f"Gotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()


if __name__ == "__main__":
    main()
