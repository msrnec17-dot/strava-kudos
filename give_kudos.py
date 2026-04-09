import time
from playwright.sync_api import sync_playwright

def click_visible_kudos(page, clicked_keys):
    buttons = page.locator("button[title*='kudos'], button[title*='Kudos']")
    count = buttons.count()
    clicked_now = 0

    for i in range(count):
        try:
            btn = buttons.nth(i)
            text = btn.get_attribute("title") or ""
            box = btn.bounding_box()
            if not box:
                continue

            key = f"{round(box['x'])}-{round(box['y'])}-{text}"
            if key in clicked_keys:
                continue

            btn.click(timeout=3000)
            clicked_keys.add(key)
            clicked_now += 1
            time.sleep(0.8)
        except Exception:
            pass

    return clicked_now

def main():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(storage_state="strava_state.json")
        page = context.new_page()

        page.goto("https://www.strava.com/dashboard", wait_until="load")
        time.sleep(5)

        clicked_keys = set()
        total_clicked = 0

        for round_num in range(8):
            clicked_now = click_visible_kudos(page, clicked_keys)
            total_clicked += clicked_now
            print(f"Krug {round_num + 1}: kliknuto {clicked_now}, ukupno {total_clicked}")

            page.mouse.wheel(0, 2200)
            time.sleep(3)

        print(f"Gotovo. Ukupno kliknuto kudosa: {total_clicked}")
        browser.close()

if __name__ == "__main__":
    main()
