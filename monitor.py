
import base64
import json
import requests

URL = "https://lademap.ladenetz.de/getObject_quick.php"

payload = {
    "objectID": "28830295",
    "stateAll": "20000",
    "poiImage": "img/categories/LAD/2_1_undefined0002@1.png",
    "language": "de",
    "category": 1,
    "prognosis_offset": -1,
    "userId": "2161776",
}

encoded = base64.b64encode(
    json.dumps(payload, separators=(",", ":")).encode()
).decode()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    ),
    "Origin": "https://lademap.ladenetz.de",
    "Referer": "https://lademap.ladenetz.de/",
}

tests = [
    ("JSON", {"Content-Type": "application/json"}, payload),
    ("BASE64", {"Content-Type": "text/plain;charset=UTF-8"}, encoded),
]

for name, extra_headers, body in tests:
    try:
        response = requests.post(
            URL,
            headers={**headers, **extra_headers},
            json=body if name == "JSON" else None,
            data=body if name == "BASE64" else None,
            timeout=30,
        )
        print(f"\nTEST: {name}")
        print("HTTP:", response.status_code)
        print("ANTWORT-LAENGE:", len(response.content))
        print("CONTENT-TYPE:", response.headers.get("content-type"))
        print("ANTWORT-ANFANG:", repr(response.text[:1500]))
    except Exception as error:
        print(f"TESTFEHLER {name}:", type(error).__name__, str(error)[:300])
