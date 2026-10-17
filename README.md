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
ein eindeutiger Status gefunden werden. `Unbekannt`, leere Antworten,
Zeitüberschreitungen und unerwartete Formate brechen den Lauf ab; sie werden
nicht an den Worker gesendet und niemals als „Frei“ oder „Belegt“ ausgegeben.
Der Abruf kann sich ändern, wenn Ladenetz seine nicht als öffentliche API
dokumentierte Karten-Schnittstelle oder das Antwort-HTML ändert.

## Einrichtung

### GitHub Actions Secrets

Unter Settings → Secrets and variables → Actions müssen vorhanden sein:

- `WORKER_URL`: Basis-URL des Cloudflare Workers
- `PUSH_SECRET`: dasselbe Push-Geheimnis wie im Worker

`BOT_TOKEN` bleibt ausschließlich als Secret im Cloudflare Worker.

### Cloudflare Worker

Der Worker muss `POST /external-update` mit dem Header
`X-Ladealarm-Secret` entgegennehmen und die vom bestehenden Sender verwendete
JSON-Form `{ "status": [{ "id", "status", "seit", "typ" }, ...] }`
akzeptieren. Der Worker-Code liegt nicht in diesem Repository. Daher konnten
weder Secret-Prüfung und KV-Binding noch das Telegram-Verhalten gegen den
tatsächlich eingesetzten Worker überprüft werden.

Vor dem produktiven Start muss am Worker bestätigt werden, dass der erste
gültige Abruf nur als KV-Ausgangswert gespeichert wird und keine Nachricht
sendet. Benachrichtigungen dürfen nur bei einem Vergleich mit einem bereits
gespeicherten gültigen Zustand ausgelöst werden. Ungültige oder fehlende
Statuswerte müssen den KV-Zustand unverändert lassen. Für diese Worker-Prüfung
ist dessen Quellcode erforderlich.

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

