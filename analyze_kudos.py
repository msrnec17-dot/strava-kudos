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

    for row in rows:
        timestamp = (row.get("timestamp") or "").strip()
        user = (row.get("user") or "UNKNOWN_USER").strip()
        status = (row.get("status") or "unknown").strip()
        details = (row.get("details") or "").strip()

        status_counter[status] += 1
        details_counter[details] += 1

        if user == "SYSTEM":
            system_counter[status] += 1
        else:
            user_counter[user] += 1
            user_status_counter[user][status] += 1

    clicked_count = status_counter.get("clicked", 0)
    no_click_runs = system_counter.get("no_clicks", 0)
    summary_runs = system_counter.get("summary", 0)

    print(f"Ukupno redaka u logu: {total_rows}")
    print(f"Ukupno kliknutih kudosa: {clicked_count}")
    print(f"Broj runova bez klikova: {no_click_runs}")
    print(f"Broj runova sa summary zapisom: {summary_runs}")
    print()

    print_status_block("Statusi", status_counter)
    print()

    top_users = user_counter.most_common(10)
    print("Top 10 korisnika po broju zapisa")
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

    top_details = [(k, v) for k, v in details_counter.most_common(10) if k]
    print("Top 10 detail poruka")
    if not top_details:
        print("  (nema detail poruka)")
    else:
        for detail, count in top_details:
            print(f"  - {count}x {detail}")


if __name__ == "__main__":
    main()
