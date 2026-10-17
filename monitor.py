
import asyncio
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

URL = "https://lademap.ladenetz.de/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="de-DE")

        def on_response(response):
            request = response.request
            if request.resource_type not in ("xhr", "fetch"):
                return

            parts = urlsplit(response.url)
            safe_url = f"{parts.scheme}://{parts.netloc}{parts.path}"
            print(
                f"NETZWERK: {response.status} "
                f"{request.resource_type} {safe_url}"
            )

            async def show_body():
                try:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type.lower():
                        body = await response.text()
                        print("DATENANTWORT:", body[:1200])
                except Exception:
                    pass

            asyncio.create_task(show_body())

        page.on("response", on_response)

        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(15000)
            print("SEITENTEXT:")
            print((await page.locator("body").inner_text())[:3000])
        except Exception as error:
            print("TESTFEHLER:", type(error).__name__, str(error)[:300])
        finally:
            await browser.close()

asyncio.run(main())
