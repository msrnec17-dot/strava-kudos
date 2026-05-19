import time
import random
from playwright.sync_api import sync_playwright

# Maksimalan broj kudosa po jednom pokretanju skripte
MAX_KUDOS = 60


def main():
    print("POČETAK SKRIPTE")

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

        # Kraće početno čekanje – i dalje malo nasumično
        pause = random.uniform(4.0, 6.0)
        print(f"Čekam {pause:.1f} s da se feed učita...")
        time.sleep(pause)

        total_clicked = 0
        stop = False

        # 2 kruga skrolanja – dovoljno brzo, a opet prođe nešto feeda
        for round_num in range(2):
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
                    print(
                        f"Dosegnut sigurni limit od {MAX_KUDOS} kudosa "
                        "u ovom runu – prekidam."
                    )
                    stop = True
                    break

                try:
                    btn = buttons.nth(i)

                    # Kratko "gledanje" aktivnosti prije klika
                    pre_pause = random.uniform(0.8, 2.0)
                    print(
                        f"  Pripremam klik na gumb {i + 1}, "
                        f"čekam {pre_pause:.1f} s..."
                    )
                    btn.scroll_into_view_if_needed()
                    time.sleep(pre_pause)

                    # Klik na kudos
                    btn.click(timeout=3000)
                    total_clicked += 1
                    print(
                        f"  Kliknuo gumb {i + 1} "
                        f"(ukupno kliknuto: {total_clicked})"
                    )

                    # Kratka pauza nakon klika
                    post_pause = random.uniform(1.0, 3.0)
                    print(
                        f"  Pauza nakon klika {post_pause:.1f} s prije sljedećeg..."
                    )
                    time.sleep(post_pause)

                except Exception as e:
                    print(f"  Preskačem gumb {i + 1} (greška: {e})")

            if stop:
                break

            scroll_amount = random.randint(1000, 1800)
            print(
                f"Kraj kruga {round_num + 1}, skrolam za {scroll_amount} px "
                "i čekam da se učita novi sadržaj..."
            )
            page.mouse.wheel(0, scroll_amount)

            scroll_pause = random.uniform(2.0, 4.0)
            time.sleep(scroll_pause)

        print(f"\nGotovo. Ukupno kliknuto kudosa: {total_clicked}")
        print("Zatvaram browser...")
        browser.close()
        print("KRAJ SKRIPTE")


if __name__ == "__main__":
    main()
