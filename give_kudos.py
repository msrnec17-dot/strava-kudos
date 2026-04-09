name: run-kudos-cron

on:
  workflow_dispatch:
  schedule:
    - cron: "0 9 * * *"

jobs:
  run-kudos:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Install Playwright Firefox
        run: python -m playwright install firefox

      - name: Restore Strava session
        shell: bash
        run: |
          echo "${{ secrets.STRAVA_STATE_B64 }}" | base64 -d > strava_state.json

      - name: Run kudos script
        run: python give_kudos.py
