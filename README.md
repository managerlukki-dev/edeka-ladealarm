# EDEKA Ladealarm

GitHub Actions ruft die Live-Statuszeilen der zwei Ladepunkte an der EDEKA-
Station Niederrheinstraße 84, 40474 Düsseldorf, aus der Ladenetz-Lademap ab
und übergibt sie an den geschützten Cloudflare-Worker-Endpunkt
`/external-update`.

## Datenabruf

Die öffentliche Ladenetz-Karte verwendet für Stationsdetails einen POST an
`getObject_detail.php`. Der offizielle Seiten-Code sendet dabei ein Base64-
kodiertes JSON-Feld namens `post` und den kurzlebigen Header
`X-Viewer-Session`. `monitor.py` liest diese Session nur im Prozessspeicher
und sendet die Anfrage mit demselben Formularfeld und Header. Sitzungswerte
und Push-Geheimnisse werden nicht protokolliert. Chromium ist nicht
erforderlich: Ein headless Playwright-Aufruf lieferte hier eine leere
HTML-Seite, während der korrekte HTTP-Aufruf mit Viewer-Session echte
Ladepunktdetails zurückgab.

Die Antwort wird nur akzeptiert, wenn beide erwarteten Ladepunkt-IDs und je
ein eindeutiger Status gefunden werden. Die „seit“-Zeit wird über die von
Ladenetz in der Zeitzeile und Statuszeile gemeinsam verwendete interne
Stecker-ID dem richtigen Ladepunkt zugeordnet. Fehlt diese Verknüpfung oder
ist sie mehrdeutig, bleibt nur die Zeit leer; der Status wird weiter nur
über die konkrete Ladepunkt-ID gelesen. `Unbekannt`, leere Antworten,
Zeitüberschreitungen und unerwartete Formate brechen den Lauf ab; sie werden
nicht an den Worker gesendet und niemals als „Frei“ oder „Belegt“ ausgegeben.
Ein echter öffentlicher Detailabruf wurde am 19.10.2026 geprüft; er lieferte
beide Ladepunkt-IDs, Statuswerte und mit derselben internen Stecker-ID
verknüpfte „seit“-Zeiten. Der Abruf kann sich ändern, wenn Ladenetz seine
nicht als öffentliche API dokumentierte Karten-Schnittstelle oder das
Antwort-HTML ändert.

## Einrichtung

### GitHub Actions Secrets

Unter Settings → Secrets and variables → Actions müssen vorhanden sein:

- `WORKER_URL`: Basis-URL des Cloudflare Workers
- `PUSH_SECRET`: dasselbe Push-Geheimnis wie im Worker

`BOT_TOKEN` bleibt ausschließlich als Secret im Cloudflare Worker.

### Cloudflare Worker

Der Worker muss `POST /external-update` mit dem Header
`X-Ladealarm-Secret` entgegennehmen und die JSON-Form
`{ "status": [{ "id", "status", "seit", "typ" }, ...] }` akzeptieren.
Der im Chat bereitgestellte Worker-Code wurde gegen diesen Sender geprüft:
Der erste gültige Abruf wird ohne Alarm gespeichert, unveränderte Zustände
lösen nichts aus, und ein echter Wechsel zwischen „Frei“ und „Belegt“ sendet
eine Nachricht. Falsche Secrets werden abgewiesen; unbekannte und
„Außer Betrieb“-Statuswerte werden nicht gespeichert und lösen keinen Alarm
aus.

Der Worker-Code ist weiterhin nicht im Repository versioniert. Der geprüfte
Code akzeptiert nur „Frei“ und „Belegt“. Liefert Ladenetz „Außer Betrieb“,
weist der Worker das Update mit HTTP 422 zurück; der KV-Zustand bleibt dabei
unverändert.

Der Worker speichert den neuen KV-Zustand vor dem Telegram-Versand. Fehler beim
Versand werden protokolliert, aber nicht erneut versucht. Bei einem
vorübergehenden Telegram-Fehler kann deshalb eine Benachrichtigung verloren
gehen, obwohl der Status gespeichert wurde. Für automatische Wiederholung
wäre eine dauerhafte Zustellwarteschlange im Worker nötig; diese Änderung ist
nicht Teil dieses Abruf-PRs.

## Workflow und Prüfung

Der Workflow läuft manuell oder alle fünf Minuten. GitHub Actions kann
geplante Läufe verzögern; ein exaktes Fünf-Minuten-Intervall ist deshalb nicht
garantiert. Der Workflow führt zuerst die Parser-Tests aus und ruft danach
die Live-Daten ab. Das Skript verwendet ausschließlich die Python-
Standardbibliothek.

Lokal:

```sh
python -m unittest discover -s tests -v
```

Ein echter End-to-End-Worker-Aufruf benötigt die beiden oben genannten
GitHub-Secrets. In diesem Repository wurden keine produktiven Secrets
verändert oder ausgelesen.
