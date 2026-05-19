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
    athlete_name = ""

    # Najbliža kartica aktivnosti iznad kudos gumba
    card = btn.locator(
        "xpath=ancestor::*["
        "contains(@class, 'react-card') or "
        "contains(@class, 'feed-entry') or "
        "contains(@class, 'FeedEntry') or "
        "self::article"
        "][1]"
    )

    # Najprije probaj točno ono što si našao u inspectu
    candidate_selectors = [
        "a[data-testid='owners-name']",
        "a[href*='/athletes/']",
        "header a[data-testid='owners-name']",
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

    # Fallback: pokušaj iz headera aktivnosti
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

    if total_clicked
