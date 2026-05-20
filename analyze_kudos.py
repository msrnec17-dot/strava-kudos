import csv
from collections import Counter, defaultdict
from pathlib import Path

LOG_PATH = Path("output/kudos_log.csv")


def load_rows():
    if not LOG_PATH.exists():
        return []

    with LOG_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def clean(value, default=""):
    value = (value or "").strip()
    return value if value else default


def print_status_block(title, counter):
    print(title)
    if not counter:
        print("  (nema podataka)")
        return

    for key, value in counter.most_common():
        print(f"  - {key}: {value}")


def main():
    rows = load_rows()

    print("ANALIZA KUDOS LOGA")
    print("==================")

    if not rows:
        print("Nema podataka.")
        return

    total_rows = len(rows)

    status_counter = Counter()
    user_counter = Counter()
    details_counter = Counter()
    system_counter = Counter()
    user_status_counter = defaultdict(Counter)

    clicked_users = Counter()
    clicked_details = Counter()

    for row in rows:
        timestamp = clean(row.get("timestamp"))
        user = clean(row.get("user"), "UNKNOWN_USER")
        status = clean(row.get("status"), "unknown")
        details = clean(row.get("details"))

        status_counter[status] += 1
        if details:
            details_counter[details] += 1

        if user == "SYSTEM":
            system_counter[status] += 1
            continue

        user_counter[user] += 1
        user_status_counter[user][status] += 1

        if status == "clicked":
            clicked_users[user] += 1
            if details:
                clicked_details[details] += 1

    clicked_count = sum(clicked_users.values())
    unique_clicked_users = len(clicked_users)
    no_click_runs = system_counter.get("no_clicks", 0)
    summary_runs = system_counter.get("summary", 0)

    print(f"Ukupno redaka u logu: {total_rows}")
    print(f"Ukupno kliknutih kudosa: {clicked_count}")
    print(f"Broj jedinstvenih korisnika s klikom: {unique_clicked_users}")
    print(f"Broj runova bez klikova: {no_click_runs}")
    print(f"Broj runova sa summary zapisom: {summary_runs}")
    print()

    print_status_block("Statusi", status_counter)
    print()

    print("Top 10 korisnika po broju zapisa")
    top_users = user_counter.most_common(10)
    if not top_users:
        print("  (nema korisničkih zapisa)")
    else:
        for user, count in top_users:
            status_parts = ", ".join(
                f"{status}={value}"
                for status, value in user_status_counter[user].most_common()
            )
            print(f"  - {user}: {count} zapisa ({status_parts})")
    print()

    print("Top korisnici po broju klikova")
    top_clicked = clicked_users.most_common(10)
    if not top_clicked:
        print("  (nema klikova)")
    else:
        for user, count in top_clicked:
            print(f"  - {user}: {count} klikova")
    print()

    interesting_statuses = [
        "click_not_confirmed",
        "click_error",
        "disabled",
        "no_button",
        "already_kudoed",
        "unknown_button_state",
    ]

    print("Detalji po problematičnim statusima")
    has_any_problem = False
    for status_name in interesting_statuses:
        count = status_counter.get(status_name, 0)
        if count > 0:
            has_any_problem = True
            print(f"  - {status_name}: {count}")
    if not has_any_problem:
        print("  (nema problematičnih statusa)")
    print()

    print("Top 10 detail poruka")
    top_details = details_counter.most_common(10)
    if not top_details:
        print("  (nema detail poruka)")
    else:
        for detail, count in top_details:
            print(f"  - {count}x {detail}")
    print()

    print("Top 10 detail poruka za klikove")
    top_clicked_details = clicked_details.most_common(10)
    if not top_clicked_details:
        print("  (nema detail poruka za klikove)")
    else:
        for detail, count in top_clicked_details:
            print(f"  - {count}x {detail}")


if __name__ == "__main__":
    main()
