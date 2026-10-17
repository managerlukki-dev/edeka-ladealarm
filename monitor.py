
import asyncio
from playwright.async_api import async_playwright

URL = "https://lademap.ladenetz.de/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="de-DE")

        page.on("console", lambda msg: print(
            "BROWSER:", msg.type, msg.text[:500]
        ))
        page.on("pageerror", lambda error: print(
            "JAVASCRIPT-FEHLER:", str(error)[:500]
        ))
        page.on("requestfailed", lambda request: print(
            "ANFRAGE FEHLGESCHLAGEN:",
            request.method,
            request.url.split("?")[0],
            request.failure
        ))

        try:
            response = await page.goto(
                URL, wait_until="domcontentloaded", timeout=60000
            )
            print("HTTP:", response.status if response else "keine Antwort")

            if response:
                print("CONTENT-TYPE:",
                      response.headers.get("content-type", "unbekannt"))

                html = await response.text()
                print("HTML-LÄNGE:", len(html))
                print("HTML-ANFANG:", repr(html[:1500]))

            await page.wait_for_timeout(10000)
            print("TITEL:", repr(await page.title()))
            print("TEXT:", repr(
                (await page.locator("body").inner_text())[:1500]
            ))

        except Exception as error:
            print("TESTFEHLER:", type(error).__name__, str(error)[:500])
        finally:
            await browser.close()

asyncio.run(main())
