import time
import random
import os
import urllib.request
import urllib.parse
from playwright.sync_api import sync_playwright

MAX_KUDOS = 60

def main():
    print("POČETAK SKRIPTE")
    
    # Lista za spremanje imena osoba kojima smo dali kudos
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

            # Na Stravi je gumb obično unutar kontejnera koji predstavlja cijelu aktivnost (npr. .react-card)
            # Tražimo sve gumbe
            buttons = page.locator(
                "button[title='Give kudos'], "
                "button[title='Be the first to give kudos!']"
            )
            count = buttons.count()
            print(f"Našao {count} kudos gumba u ovom krugu")

            for i in range(count):
                if total_clicked >= MAX_KUDOS:
                    print(f"Dosegnut sigurni limit od {MAX_KUDOS} kudosa u ovom runu – prekidam.")
                    stop = True
                    break

                try:
                    btn = buttons.nth(i)
                    pre_pause = random.uniform(0.8, 2.0)
                    btn.scroll_into_view_if_needed()
                    time.sleep(pre_pause)
                    
                    # Pokušaj pronaći ime vlasnika aktivnosti.
                    # Strava često mijenja klase, pa tražimo link za profil unutar najbližeg "react-card" ili roditeljskog elementa.
                    # Ovo koristi xpath za navigaciju prema gore do roditelja aktivnosti, pa natrag dolje do imena.
                    try:
                        # Pokušaj dohvatiti tekst elementa koji obično sadrži ime (data-testid='owner-name' ili slično).
                        # Zbog čestih promjena Strava UI-ja, idemo po lokatoru iznad gumba.
                        card = btn.locator("xpath=ancestor::div[contains(@class, 'react-card') or contains(@class, 'feed-entry')]")
                        # Probaj naći tag a koji izgleda kao link profila, obično prva ili druga poveznica s imenom
                        name_element = card.locator("a.entry-owner, [data-testid='owner-name']").first
                        if name_element.count() > 0:
                             athlete_name = name_element.inner_text().strip()
                        else:
                             # Fallback: ako ne nađe te klase, potraži bilo koji strong tag u headeru aktivnosti
                             header_strong = card.locator("header strong, .entry-head strong").first
                             if header_strong.count() > 0:
                                 athlete_name = header_strong.inner_text().strip()
                             else:
                                 athlete_name = "Netko"
                    except Exception:
                        athlete_name = "Netko"
                        
                    # Ako nije prazno dodaj ga
                    if not athlete_name:
                         athlete_name = "Netko"

                    btn.click(timeout=3000)
                    total_clicked += 1
                    
                    # Dodaj u listu
                    kudos_names.append(athlete_name)
                    
                    print(f"  Kliknuo gumb {i + 1} za '{athlete_name}' (ukupno kliknuto: {total_clicked})")

                    post_pause = random.uniform(1.0, 3.0)
                    time.sleep(post_pause)

                except Exception as e:
                    print(f"  Preskačem gumb {i + 1} (greška: {e})")

            if stop:
                break

            scroll_amount = random.randint(1000, 1800)
            page.mouse.wheel(0, scroll_amount)
            scroll_pause = random.uniform(2.0, 4.0)
            time.sleep(scroll_pause)

        print(f"\nGotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()
        
        # Slanje obavijesti na Telegram
        tel_token = os.environ.get("TELEGRAM_TOKEN")
        tel_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if tel_token and tel_chat_id:
            # Kreiraj poruku s imenima
            if total_clicked > 0:
                # Ograniči popis imena da poruka ne bude preduga za Telegram
                if len(kudos_names) > 30:
                    names_str = ", ".join(kudos_names[:30]) + f" ...i još {len(kudos_names)-30} drugih"
                else:
                    names_str = ", ".join(kudos_names)
                    
                message = f"Strava bot je odradio posao!\n\nPodijeljeno novih kudosa: {total_clicked} 🚴‍♂️🔥\n\nKudose su dobili: {names_str}"
            else:
                message = "Strava bot je odradio posao!\n\nNije pronađena nijedna nova aktivnost za davanje kudosa. 🕵️‍♂️"
                
            try:
                url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
                data = urllib.parse.urlencode({'chat_id': tel_chat_id, 'text': message}).encode('utf-8')
                urllib.request.urlopen(url, data=data, timeout=5)
                print("Telegram izvješće s imenima uspješno poslano na mobitel!")
            except Exception as e:
                print(f"Greška pri slanju Telegram poruke: {e}")
                
        print("KRAJ SKRIPTE")

if __name__ == "__main__":
    main()
