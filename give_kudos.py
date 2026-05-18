import time
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        # Firefox u headless modu za GitHub Actions
        browser = p.firefox.launch(headless=True)

        # Učitavamo prijavu iz strava_state.json (taj file ti workflow vraća iz secreta)
        context = browser.new_context(storage_state="strava_state.json")
        page = context.new_page()

        print("Otvaram Strava dashboard...")
        page.goto("https://www.strava.com/dashboard", wait_until="networkidle")
        # Pričekaj da se feed i svi gumbi lijepo učitaju
        time.sleep(8)

        total_clicked = 0

        # Nekoliko krugova: u svakom krugu kliknemo sve vidljive gumbe pa skrolamo dolje
        for round_num in range(6):
            print(f"Krug {round_num + 1} – tražim kudose...")

            # Jednostavan selektor po naslovu gumba, kao u starim skriptama
            buttons = page.locator(
                "button[title='Give kudos'], button[title='Be the first to give kudos!']"
            )
            count = buttons.count()
            print(f"Našao {count} kudos gumba")

            for i in range(count):
                try:
                    btn = buttons.nth(i)
                    btn.click(timeout=3000)
                    total_clicked += 1
                    print(f"  Kliknuo gumb {i + 1}")
                    time.sleep(1.0)  # kratka pauza između klikova
                except Exception as e:
                    print(f"  Preskačem gumb {i + 1} (greška: {e})")

            # Skrolamo dolje da se učitaju nove aktivnosti
            page.mouse.wheel(0, 2200)
            time.sleep(4)

        print(f"Gotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()


if __name__ == "__main__":
    main()
