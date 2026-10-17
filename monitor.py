
import asyncio
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

URL = "https://lademap.ladenetz.de/"
CHARGERS = [
    "DESWDE000020101",
    "DESWDE000020102",
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="de-DE")
        page = await context.new_page()

        seen = set()

        def on_response(response):
            url = response.url
            if "getObject_detail.php" not in url:
                return

            parts = urlsplit(url)
            safe_url = f"{parts.scheme}://{parts.netloc}{parts.path}"
            print("DETAIL-ANFRAGE:", response.status, safe_url)

            async def inspect():
                try:
                    body = await response.body()
                    print("DETAIL-ANTWORT-LAENGE:", len(body))
                    if body:
                        print(
                            "DETAIL-ANTWORT-ANFANG:",
                            body[:1000].decode("utf-8", errors="replace")
                        )
                except Exception as error:
                    print("ANTWORTFEHLER:", type(error).__name__)

            asyncio.create_task(inspect())

        page.on("response", on_response)

        try:
            await page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.wait_for_timeout(15000)

            print("SEITE GELADEN:", page.url)
            print("HINWEIS: Detailanfragen werden nur erkannt,")
            print("wenn die Seite sie selbst auslöst.")

            # Die Karte wird nicht automatisch angeklickt.
            # Wir prüfen zunächst, ob sie selbst Detailanfragen startet.
            await page.wait_for_timeout(5000)

        except Exception as error:
            print("TESTFEHLER:", type(error).__name__, str(error)[:300])
        finally:
            await context.close()
            await browser.close()

asyncio.run(main())
