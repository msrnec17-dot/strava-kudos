import json
import csv
import os
import sys
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

STATE_FILE = "strava_state.json"
KUDSOS_LOG = "kudos_log.csv"

def log(msg):
    print(msg, flush=True)

def init_log():
    if not os.path.exists(KUDSOS_LOG):
        with open(KUDSOS_LOG, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['datum', 'activity_url', 'osoba', 'title', 'status'])

def log_kudos(activity_url, osoba, title, status):
    with open(KUDSOS_LOG, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), activity_url, osoba, title, status])

def extract_person_from_activity(btn):
    try:
        # Pokušaj izvući ime iz parent kartice
        parent = btn.locator('..').locator('xpath=..').first
        name = parent.locator('[data-testid*="athlete"], [class*="athlete"], a[href*="/athletes/"]').text_content().strip()[:50]
        if name:
            return name
    except:
        pass
    return "nepoznato"

def click_visible_unfilled(page, clicked_keys):
    clicked_now = 0
    buttons = page.locator("button[data-testid='kudos_button']")
    
    for i in range(buttons.count()):
        try:
            btn = buttons.nth(i)
            if not btn.is_visible() or not btn.is_enabled():
                continue
                
            # Provjeri da li ima unfilled kudos
            unfilled = btn.locator("svg[data-testid='unfilled_kudos']").count() > 0
            if not unfilled:
                continue
                
            box = btn.bounding_box()
            key = f"{round(box['x'])}-{round(box['y'])}"
            if key in clicked_keys:
                continue
                
            # Dohvati URL aktivnosti iz parenta
            activity_link = page.locator(f'xpath=(//a[contains(@href, "/activities/")])[position()={i+1}]').get_attribute('href') or ""
            
            # Izvuci ime osobe
            osoba = extract_person_from_activity(btn)
            title = btn.get_attribute("title") or ""
            
            log_kudos(activity_link, osoba, title, "klik")
            clicked_keys.add(key)
            
            btn.click(timeout=3000, force=True)
            time.sleep(1.2)
            clicked_now += 1
            
        except Exception:
            pass
    return clicked_now

def print_stats():
    if not os.path.exists(KUDSOS_LOG):
        log("Nema log datoteke.")
        return
    
    stats = {}
    with open(KUDSOS_LOG, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            osoba = row['osoba']
            if osoba not in stats:
                stats[osoba] = 0
            stats[osoba] += 1
    
    log("
=== KUDSOS STATISTIKA ===")
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    for i, (osoba, broj) in enumerate(sorted_stats[:10], 1):
        log(f"{i}. {osoba}: {broj} kudosa")
    log("========================")

def main():
    init_log()
    
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        
        page.goto("https://www.strava.com/dashboard")
        time.sleep(6)
        
        clicked_keys = set()
        total = 0
        
        for round_num in range(12):
            clicked_now = click_visible_unfilled(page, clicked_keys)
            total += clicked_now
            log(f"Krug {round_num+1}: {clicked_now} kliknuto, ukupno {total}")
            
            page.mouse.wheel(0, 2000)
            time.sleep(3)
        
        print_stats()
        log(f"GOTOVO: {total} kudosa")
        
        browser.close()

if __name__ == "__main__":
    main()
