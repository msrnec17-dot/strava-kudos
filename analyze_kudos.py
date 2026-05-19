import csv
from collections import Counter
from pathlib import Path
import os
import urllib.request
import urllib.parse

LOG_PATH = Path("output/kudos_log.csv")
REPORT_PATH = Path("output/daily_kudos_top20.txt")


def load_counts():
    counts = Counter()

    if not LOG_PATH.exists():
        return counts

    with LOG_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("user") or "").strip()
            if name:
                counts[name] += 1

    return counts


def format_report(counts):
    total = sum(counts.values())
    unique = len(counts)
    top20 = counts.most_common(20)

    lines = []
    lines.append("Dnevna analiza kudosa")
    lines.append(f"Ukupno dodijeljeno kudosa: {total}")
    lines.append(f"Broj korisnika: {unique}")
    lines.append("")
    lines.append("Top 20 korisnika:")

    if top20:
        for idx, (name, count) in enumerate(top20, start=1):
            lines.append(f"{idx}. {name} - {count}")
    else:
        lines.append("Nema podataka.")

    return "\n".join(lines)


def send_telegram(message):
    tel_token = os.environ.get("TELEGRAM_TOKEN")
    tel_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not tel_token or not tel_chat_id:
        print("Telegram token/chat id nisu postavljeni.")
        return

    url = f"https://api.telegram.org/bot{tel_token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": tel_chat_id,
            "text": message,
        }
    ).encode("utf-8")

    urllib.request.urlopen(url, data=data, timeout=10)


def main():
    counts = load_counts()
    report = format_report(counts)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(report)

    try:
        send_telegram(report)
        print("Telegram analiza poslana.")
    except Exception as e:
        print(f"Greška pri slanju Telegram analize: {e}")


if __name__ == "__main__":
    main()
