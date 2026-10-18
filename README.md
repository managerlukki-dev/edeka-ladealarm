# EDEKA Ladealarm – GitHub Actions

Der Job öffnet die Ladenetz-Lademap mit Chromium/Playwright, übernimmt die
X-Viewer-Session des echten Browser-Kontexts, liest `getObject_detail.php`
und übergibt die beiden Type-2-Statuswerte an den vorhandenen Cloudflare Worker.

## GitHub Secrets

Im Repository unter Settings → Secrets and variables → Actions drei Secrets anlegen:

- `WORKER_URL` = deine bestehende Worker-URL
- `PUSH_SECRET` = ein selbst gewähltes langes Zufallsgeheimnis

`BOT_TOKEN` bleibt ausschließlich im Cloudflare Worker.

## Wichtig

GitHub Actions kann geplante Workflows maximal alle 5 Minuten starten.
Der Workflow startet deshalb zu Minute 2, 7, 12 usw. Dadurch wird nicht
jede Minute garantiert. GitHub weist außerdem darauf hin, dass geplante
Workflows bei hoher Auslastung verzögert werden können.

## Worker

Im bestehenden Worker muss zusätzlich ein geschützter POST-Endpunkt
`/external-update` ergänzt werden. Dieser übernimmt `status`, vergleicht ihn
mit `last_station_state`, speichert Änderungen und versendet die Telegram-
Meldungen an die bereits registrierten Nutzer.

Die bisherige Telegram-/KV-Logik bleibt bestehen.
