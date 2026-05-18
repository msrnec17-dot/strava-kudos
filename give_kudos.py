import time
from playwright.sync_api import sync_playwright

def click_visible_kudos(page, clicked_keys):
    # Tražimo sve gumbe koji u naslovu imaju riječ 'kudos' (velikim ili malim slovom)
    buttons = page.locator("button[title*='kudos'], button[title*='Kudos']")
    count = buttons.count()
    clicked_now = 0

    for i in range(count):
        try:
            btn = buttons.nth(i)
            text = btn.get_attribute("title") or ""
            box = btn.bounding_box()
            
            # Ako gumb nije vidljiv na ekranu, preskoči
            if not box:
                continue

            # Generiramo jedinstveni ključ za gumb temeljen na poziciji
            key = f"{round(box['x'])}-{round(box['y'])}-{text}"
            if key in clicked_keys:
                continue

            # 1. Hover (prelazak mišem preko gumba smanjuje šansu da Strava ignorira klik)
            btn.hover()
            time.sleep(0.5)
            
            # 2. Klik (sa simulacijom trajanja pritiska i force opcijom)
            btn.click(force=True, delay=150, timeout=3000)
            
            clicked_keys.add(key)
            clicked_now += 1
            
            # 3. Malo dulja pauza da server stigne registrirati klik
            time.sleep(1.5)
            
        except Exception as e:
            # U slučaju greške s pojedinim gumbom (npr. nestane sa stranice), samo idemo dalje
            print(f"Greška na gumbu {i}: {e}")

    return clicked_now

def main():
    with sync_playwright() as p:
        # headless=True ostaje za GitHub Actions
        browser = p.firefox.launch(headless=True)
        
        # OVO JE DODANO: fiksna velika rezolucija i User-Agent da Strava ne posumnja na bota
        context = browser.new_context(
            storage_state="strava_state.json",
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Otvaram Stravu...")
        page.goto("https://www.strava.com/dashboard", wait_until="load")
        time.sleep(8)  # Čekamo dulje da se sve slike i komponente učitaju na novoj rezoluciji

        clicked_keys = set()
        total_clicked = 0

        for round_num in range(8):
            print(f"Započinjem krug {round_num + 1}...")
            clicked_now = click_visible_kudos(page, clicked_keys)
            total_clicked += clicked_now
            print(f"Krug {round_num + 1}: kliknuto {clicked_now}, ukupno do sada: {total_clicked}")

            # Scrollamo dolje za učitavanje novih objava
            page.mouse.wheel(0, 2200)
            time.sleep(4)

        print(f"Gotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()

if __name__ == "__main__":
    main()
