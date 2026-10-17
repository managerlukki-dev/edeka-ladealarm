
import json
import os
import sys
from datetime import datetime, timezone

import requests

WORKER_URL = os.environ["WORKER_URL"].rstrip("/")
PUSH_SECRET = os.environ["PUSH_SECRET"]

CHARGERS = [
    "DESWDE000020101",
    "DESWDE000020102",
]


def main():
    # Wir prüfen zunächst, ob die GitHub-Secrets funktionieren
    # und der Cloudflare-Worker erreichbar ist.
    response = requests.get(
        WORKER_URL + "/",
        timeout=20,
    )
    response.raise_for_status()

    print("Cloudflare-Worker ist erreichbar.")

    # Noch keine Statusdaten senden:
    # Wir müssen zuerst den tatsächlichen Live-Datenabruf
    # zuverlässig verifizieren, damit keine falschen Alarme entstehen.
    print("Worker erreichbar; Live-Datenquelle noch nicht eingerichtet.")
    print("Zeitpunkt:", datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
