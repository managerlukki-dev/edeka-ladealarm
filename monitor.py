"""Fetch Ladenetz live status and forward validated results to the Worker."""

from __future__ import annotations

import base64
import html
from html.parser import HTMLParser
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://lademap.ladenetz.de/"
STATION_ID = "28830295"
STATION_POSITION = "51.274923 6.743708"
CHARGERS = ("DESWDE000020101", "DESWDE000020102")
ALLOWED_STATUSES = {"Frei", "Belegt", "Außer Betrieb"}


class MonitorError(Exception):
    """An expected failure that can be reported without leaking credentials."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    parser.close()
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def parse_station_status(markup: str) -> list[dict[str, str]]:
    """Parse each exact charger row; fail closed on missing/unknown states."""
    text = _plain_text(markup)
    rows: list[dict[str, str]] = []

    for charger_id in CHARGERS:
        match = re.search(
            rf"ID\s*:\s*{re.escape(charger_id)}\b(?P<row>.*?)(?=\bID\s*:|$)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            raise MonitorError("Die Antwort enthält nicht beide erwarteten Ladepunkte.")

        row = match.group("row")
        status_match = re.search(
            r"\bStatus\s*:\s*(Frei|Belegt|Außer\s+Betrieb|Unbekannt)\b",
            row,
            flags=re.IGNORECASE,
        )
        if not status_match:
            raise MonitorError("Ein Ladepunktstatus fehlt oder ist nicht lesbar.")

        raw_status = re.sub(r"\s+", " ", status_match.group(1)).casefold()
        normalized_status = {
            "frei": "Frei",
            "belegt": "Belegt",
            "ausser betrieb": "Außer Betrieb",
            "unbekannt": "Unbekannt",
        }.get(raw_status, raw_status)
        if normalized_status not in ALLOWED_STATUSES:
            raise MonitorError("Ladenetz meldet für einen Ladepunkt keinen bekannten Status.")

        since_match = re.search(
            r"\bseit\s*:\s*(?:(?:Mo|Di|Mi|Do|Fr|Sa|So)\s*)?(\d{1,2}:\d{2})",
            row,
            flags=re.IGNORECASE,
        )
        rows.append(
            {
                "id": charger_id,
                "status": normalized_status,
                "seit": since_match.group(1) if since_match else "",
                "typ": "Typ 2",
            }
        )

    return rows


def _extract_viewer_session(markup: str) -> str:
    match = re.search(
        r'var\s+viewerSessionId\s*=\s*["\']([^"\']+)["\']', markup
    )
    if not match:
        raise MonitorError("Ladenetz hat keine gültige Viewer-Session bereitgestellt.")
    return match.group(1)


def fetch_live_status() -> list[dict[str, str]]:
    payload = {
        "diff_time_zone": 0,
        "objectID": STATION_ID,
        "poiposition": STATION_POSITION,
        "myposition": "",
        "stateAll": "30000",
        "category": 1,
        "language": "de",
        "prognosis_offset": -1,
        "windowSize": 305,
    }
    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Origin": "https://lademap.ladenetz.de",
        "Referer": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        with urlopen(Request(BASE_URL, headers=browser_headers), timeout=30) as response:
            landing_markup = response.read(2_000_001).decode("utf-8")
        if len(landing_markup) > 2_000_000:
            raise MonitorError("Die Ladenetz-Startseite ist unerwartet groß.")
        viewer_session = _extract_viewer_session(landing_markup)

        form = urlencode({"post": encoded}).encode()
        request = Request(
            f"{BASE_URL}getObject_detail.php",
            data=form,
            headers={
                **browser_headers,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Viewer-Session": viewer_session,
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise MonitorError("Ladenetz hat keine erfolgreiche Detailantwort geliefert.")
            markup = response.read(2_000_001).decode("utf-8")
    except MonitorError:
        raise
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, OSError) as exc:
        # Do not include exception text: transport diagnostics can contain secrets.
        raise MonitorError("Der Live-Abruf bei Ladenetz ist fehlgeschlagen.") from exc

    if len(markup) > 2_000_000:
        raise MonitorError("Die Ladenetz-Detailantwort ist unerwartet groß.")
    if len(markup) < 100:
        raise MonitorError("Ladenetz hat eine leere oder unvollständige Detailantwort geliefert.")
    return parse_station_status(markup)


def push_to_worker(status: list[dict[str, str]]) -> None:
    worker_url = os.environ.get("WORKER_URL", "").strip().rstrip("/")
    push_secret = os.environ.get("PUSH_SECRET", "")
    if not worker_url or not push_secret:
        raise MonitorError("WORKER_URL oder PUSH_SECRET fehlt.")
    if not worker_url.startswith("https://"):
        raise MonitorError("WORKER_URL muss HTTPS verwenden.")

    body = json.dumps({"status": status}, separators=(",", ":")).encode()
    request = Request(
        f"{worker_url}/external-update",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Ladealarm-Secret": push_secret,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise MonitorError("Der Worker hat das Statusupdate abgelehnt.")
    except HTTPError as exc:
        raise MonitorError(f"Der Worker hat das Statusupdate abgelehnt (HTTP {exc.code}).") from exc
    except URLError as exc:
        raise MonitorError("Der Worker war beim Statusupdate nicht erreichbar.") from exc


def main() -> int:
    try:
        status = fetch_live_status()
        push_to_worker(status)
    except MonitorError as exc:
        print(f"Ladealarm: {exc}", file=sys.stderr)
        return 1
    print("Beide Ladepunktstatus wurden abgerufen und an den Worker übergeben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

