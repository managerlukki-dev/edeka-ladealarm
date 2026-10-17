const { chromium } = require("playwright");

const WORKER_URL = process.env.WORKER_URL;
const PUSH_SECRET = process.env.PUSH_SECRET;

if (!WORKER_URL || !PUSH_SECRET) {
  throw new Error("WORKER_URL oder PUSH_SECRET fehlt.");
}

const DETAIL_URL = "https://lademap.ladenetz.de/getObject_detail.php";

const payload = {
  diff_time_zone: -2,
  objectID: "28830295",
  poiposition: "51.274923 6.743708",
  stateAll: "30000",
  category: 1,
  language: "de",
  prognosis_offset: -1,
  windowSize: 305
};

const CHARGERS = [
  "DESWDE000020101",
  "DESWDE000020102"
];

function stripHtml(text) {
  return text
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeStatus(status) {
  const s = status.toLowerCase();
  if (s === "belegt") return "Belegt";
  if (s === "frei") return "Frei";
  if (s.includes("außer")) return "Außer Betrieb";
  return "Unbekannt";
}

function parseStationHtml(html) {
  const cleanText = stripHtml(html);
  const seitMatches = [
    ...cleanText.matchAll(
      /seit:\s*(?:Mo|Di|Mi|Do|Fr|Sa|So)?\s*(\d{1,2}:\d{2})/gi
    )
  ];
  const seitZeiten = seitMatches.map(m => m[1]);

  return CHARGERS.map((id, i) => {
    const pos = html.indexOf(id);

    if (pos === -1) {
      return { id, status: "Unbekannt", seit: seitZeiten[i] || "", typ: "Typ 2" };
    }

    let nextPos = html.length;
    if (i < CHARGERS.length - 1) {
      const p = html.indexOf(CHARGERS[i + 1], pos + id.length);
      if (p !== -1) nextPos = p;
    } else {
      nextPos = Math.min(html.length, pos + 3000);
    }

    const afterText = stripHtml(html.substring(pos, nextPos));
    const match = afterText.match(
      /Status:\s*(Belegt|Frei|Außer Betrieb|Unbekannt)/i
    );

    return {
      id,
      status: match ? normalizeStatus(match[1]) : "Unbekannt",
      seit: seitZeiten[i] || "",
      typ: "Typ 2"
    };
  });
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-blink-features=AutomationControlled"]
  });

  const context = await browser.newContext({
    locale: "de-DE",
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
  });

  const page = await context.newPage();

  let viewerSession = null;

  page.on("request", request => {
    const headers = request.headers();
    if (headers["x-viewer-session"]) {
      viewerSession = headers["x-viewer-session"];
    }
  });

  try {
    await page.goto("https://lademap.ladenetz.de/", {
      waitUntil: "domcontentloaded",
      timeout: 30000
    });

    // Give the Lademap JavaScript time to create its viewer session.
    for (let i = 0; i < 20 && !viewerSession; i++) {
      await page.waitForTimeout(500);
    }

    if (!viewerSession) {
      throw new Error("Keine X-Viewer-Session der Lademap gefunden.");
    }

    console.log("Viewer-Session erkannt.");

    const encoded = Buffer
      .from(JSON.stringify(payload), "utf8")
      .toString("base64");

    const result = await page.evaluate(
      async ({ detailUrl, encoded, viewerSession }) => {
        const response = await fetch(detailUrl, {
          method: "POST",
          credentials: "include",
          headers: {
            "Accept": "*/*",
            "Content-Type":
              "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "X-Viewer-Session": viewerSession
          },
          body: "post=" + encodeURIComponent(encoded)
        });

        return {
          status: response.status,
          text: await response.text()
        };
      },
      { detailUrl: DETAIL_URL, encoded, viewerSession }
    );

    console.log("Lademap HTTP:", result.status);
    console.log("Antwortlänge:", result.text.length);

    if (result.status !== 200 || result.text.length < 100) {
      throw new Error(
        `Lademap lieferte keine gültigen Daten (HTTP ${result.status}, ${result.text.length} Bytes).`
      );
    }

    const status = parseStationHtml(result.text);

    if (status.some(x => x.status === "Unbekannt")) {
      throw new Error(
        "Mindestens ein Type-2-Ladepunkt konnte nicht eindeutig gelesen werden: " +
        JSON.stringify(status)
      );
    }

    console.log(JSON.stringify(status, null, 2));

    const pushResponse = await fetch(
      WORKER_URL.replace(/\/$/, "") + "/external-update",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Ladealarm-Secret": PUSH_SECRET
        },
        body: JSON.stringify({ status })
      }
    );

    const pushText = await pushResponse.text();

    if (!pushResponse.ok) {
      throw new Error(
        `Worker-Update fehlgeschlagen: HTTP ${pushResponse.status} ${pushText}`
      );
    }

    console.log("Worker aktualisiert:", pushText);
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
