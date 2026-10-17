
import asyncio
from playwright.async_api import async_playwright

URL = "https://lademap.ladenetz.de/"
CHARGERS = [
    "DESWDE000020101",
    "DESWDE000020102",
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            locale="de-DE",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        page.on("response", lambda response: print(
            "DETAIL:", response.status,
            response.url.split("?")[0]
        ) if "getObject_detail.php" in response.url else None)

        try:
            response = await page.goto(
                URL, wait_until="domcontentloaded", timeout=60000
            )
            print("HTTP:", response.status if response else "keine Antwort")
            await page.wait_for_timeout(8000)

            print("SEITENTITEL:", await page.title())
            text = await page.locator("body").inner_text(timeout=15000)
            print("SEITENTEXT:")
            print(text[:5000])

            for charger in CHARGERS:
                print(
                    "LADEPUNKT", charger,
                    "GEFUNDEN:" if charger in text else "NICHT IM TEXT:"
                )

        except Exception as error:
            print("TESTFEHLER:", type(error).__name__, str(error)[:500])
        finally:
            await browser.close()

asyncio.run(main())
