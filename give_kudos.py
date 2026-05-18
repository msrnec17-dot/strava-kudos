import time
from playwright.sync_api import sync_playwright

def click_visible_kudos(page, clicked_keys):
    # Strava najpouzdanije registrira klik na gumb sa data-testid atributom
    # Tražimo sve gumbe kojima je testid "kudos_button"
    buttons = page.locator("button[data-testid='kudos_button']")
    count = buttons.count()
    clicked_now = 0

    for i in range(count):
        try:
            btn = buttons.nth(i)
            # Provjeri postoji li 'aria-pressed' atribut. Ako je 'true', kudos je već dan.
            # Kod nekih verzija UI-a koristi se aria-pressed, a kod nekih 'unfilled' u title-u.
            is_pressed = btn.get_attribute("aria-pressed")
            if is_pressed == "true":
                continue
                
            box = btn.bounding_box()
            if not box:
                continue

            # Generiramo jedinstveni ključ na osnovu koordinata
            key = f"{round(box['x'])}-{round(box['y'])}"
            if key in clicked_keys:
                continue

            # Skrolaj do elementa tako da sigurno bude u viewportu
            btn.scroll_into_view_if_needed()
            time.sleep(0.5)

            # Klikni u centar gumba (precizniji klik za SVG gumbe)
            btn.click(force=True, delay=200)
            
            clicked_keys.add(key)
            clicked_now += 1
            
            # Pričekaj 2 sekunde između klikova jer Strava filtrira brze zahtjeve
            time.sleep(2)
            
        except Exception as e:
            print(f"Greška na gumbu {i}: {e}")

    return clicked_now

def main():
    with sync_playwright() as p:
        # Povećavamo viewport da izbjegnemo preklapanja elemenata (česti uzrok failed klikova na Stravi)
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            storage_state="strava_state.json",
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Otvaram Stravu...")
        page.goto("https://www.strava.com/dashboard", wait_until="load")
        
        # Pusti da se stranica do kraja izrenderira
        time.sleep(10)

        clicked_keys = set()
        total_clicked = 0

        for round_num in range(8):
            print(f"Započinjem krug {round_num + 1}...")
            clicked_now = click_visible_kudos(page, clicked_keys)
            total_clicked += clicked_now
            print(f"Krug {round_num + 1}: kliknuto {clicked_now}, ukupno do sada: {total_clicked}")

            # Skrolamo za učitavanje starijih aktivnosti
            page.mouse.wheel(0, 2500)
            time.sleep(5)

        print(f"Gotovo. Ukupno podijeljeno kudosa: {total_clicked}")
        browser.close()

if __name__ == "__main__":
    main()
