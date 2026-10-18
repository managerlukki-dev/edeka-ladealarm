
import requests

URL = "https://lademap.ladenetz.de/getObject_quick.php"

# Base64-Parameter aus deiner Browser-Anfrage
encoded = (
    "eyJvYmplY3RJRCI6IjI4ODMwMjk1Iiwic3RhdGVBbGwiOiIyMDAwMCIs"
    "InBvaUltYWdlIjoiaW1nL2NhdGVnb3JpZXMvTEFELzJfMV91bmRlZmluZWQwMDAy"
    "QDEucG5nIiwibGFuZ3VhZ2UiOiJkZSIsImNhdGVnb3J5IjoxLCJwcm9nbm9zaXNf"
    "b2Zmc2V0IjotMSwidXNlcklkIjoiMjE2MTc3NiJ9"
)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    ),
    "Origin": "https://lademap.ladenetz.de",
    "Referer": "https://lademap.ladenetz.de/",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

response = requests.post(
    URL,
    data={"data": encoded},
    headers=headers,
    timeout=30,
)

print("HTTP:", response.status_code)
print("ANTWORT-LAENGE:", len(response.content))
print("CONTENT-TYPE:", response.headers.get("content-type"))
print("ANTWORT-ANFANG:", repr(response.text[:1500]))
