"""Fetch public source documents as plain text and record where each one came from.

Run from the backend folder:
    .venv\\Scripts\\python.exe ..\\scripts\\collect_sources.py

Two routes are used:
- Web pages (European Commission, EFRAG): fetched directly.
- EU legal texts: fetched through the Publications Office resolver
  (publications.europa.eu/resource/celex/<CELEX number>), the official service for machine access.
  The website eur-lex.europa.eu answers automated requests with a bot check, so it is not used.

Anything that does not return real content is skipped and reported, never worked around.
"""

import csv
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "data" / "sources"
SOURCES_CSV = ROOT / "data" / "sources.csv"

HEADERS = {"User-Agent": "UC1 RAG pilot (student project)", "Accept-Language": "eng"}
CELEX_URL = "https://publications.europa.eu/resource/celex/{celex}"

# slug, title, publisher, document_type, route, locator, effective_from, notes
SOURCES = [
    ("csrd-2022-original", "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive, original text",
     "European Parliament and Council", "directive", "celex", "32022L2464", "2023-01-05",
     "Original Official Journal text of 16 December 2022"),
    ("csrd-2022-consolidated-2025-04-17", "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive, consolidated 2025-04-17",
     "European Parliament and Council", "directive", "celex", "02022L2464-20250417", "2025-04-17",
     "Consolidated text after the stop-the-clock directive"),
    ("csrd-2022-consolidated-2026-03-18", "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive, consolidated 2026-03-18",
     "European Parliament and Council", "directive", "celex", "02022L2464-20260318", "2026-03-18",
     "Consolidated text after the Omnibus I directive"),
    ("stop-the-clock-2025-794", "Directive (EU) 2025/794 stop-the-clock",
     "European Parliament and Council", "directive", "celex", "32025L0794", "2025-04-17",
     "Postpones reporting dates for later waves of companies"),
    ("omnibus-i-2026-470", "Directive (EU) 2026/470 Omnibus I",
     "European Parliament and Council", "directive", "celex", "32026L0470", "2026-03-18",
     "Amends scope and content of sustainability reporting rules"),
    ("esrs-set1-2023-2772", "Delegated Regulation (EU) 2023/2772 European Sustainability Reporting Standards, Set 1",
     "European Commission", "regulation", "celex", "32023R2772", "2023-12-25",
     "Entered into force 3 days after publication on 22 December 2023"),
    ("esrs-revised-2026-1563", "Delegated Regulation (EU) 2026/1563 revised European Sustainability Reporting Standards",
     "European Commission", "regulation", "celex", "32026R1563", "2026-11-10",
     "Adopted 3 July 2026, published 21 September 2026, in force 10 November 2026, applies to financial years from 1 January 2027"),
    ("ec-revised-esrs-news-2026-07-03", "Commission adopts revised sustainability reporting standards",
     "European Commission", "news", "web",
     "https://finance.ec.europa.eu/news/commission-adopts-revised-sustainability-reporting-standards-reduce-administrative-burdens-eu-2026-07-03_en",
     "2026-07-03", "News item of 3 July 2026; its scrutiny status is superseded by the Official Journal text"),
    ("ec-corporate-sustainability-reporting", "Corporate sustainability reporting",
     "European Commission", "guidance", "web",
     "https://finance.ec.europa.eu/financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en",
     date.today().isoformat(), "Page snapshot; the page has no publication date"),
    ("efrag-esrs-simplification", "ESRS simplification",
     "EFRAG", "guidance", "web", "https://www.efrag.org/en/projects/esrs-simplification",
     date.today().isoformat(), "Page snapshot; content describes 2025 and may be out of date"),
]

# Versions of one law share a document title so ingestion chains them as versions of one document.
DOCUMENT_TITLES = {
    "csrd-2022-original": "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive",
    "csrd-2022-consolidated-2025-04-17": "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive",
    "csrd-2022-consolidated-2026-03-18": "Directive (EU) 2022/2464 Corporate Sustainability Reporting Directive",
    "esrs-set1-2023-2772": "Delegated Regulation (EU) 2023/2772 European Sustainability Reporting Standards",
    "esrs-revised-2026-1563": "Delegated Regulation (EU) 2023/2772 European Sustainability Reporting Standards",
}

SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg", "form", "aside", "button"}
BLOCK_TAGS = {"p", "div", "li", "br", "tr", "section", "article", "ul", "ol", "table", "td"}
HEADING_TAGS = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### "}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag in HEADING_TAGS:
            self.parts.append("\n\n" + HEADING_TAGS[tag])
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag in HEADING_TAGS:
            self.parts.append("\n\n")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fetch_celex(celex: str) -> httpx.Response:
    """Resolve a CELEX number to its XHTML text, following redirects over HTTPS only."""
    url = CELEX_URL.format(celex=celex)
    headers = {**HEADERS, "Accept": "application/xhtml+xml, text/html;q=0.8"}
    for _ in range(6):
        response = httpx.get(url, headers=headers, timeout=120, follow_redirects=False)
        location = response.headers.get("location")
        if response.status_code in (301, 302, 303, 307, 308) and location:
            url = str(httpx.URL(url).join(location)).replace("http://", "https://", 1)
            continue
        return response
    raise httpx.TooManyRedirects("too many redirects", request=httpx.Request("GET", url))


def main() -> int:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    rows, skipped = [], []
    for slug, title, publisher, doc_type, route, locator, effective_from, notes in SOURCES:
        try:
            if route == "celex":
                response, url = fetch_celex(locator), CELEX_URL.format(celex=locator)
            else:
                response = httpx.get(locator, headers=HEADERS, follow_redirects=True, timeout=60)
                url = locator
        except httpx.HTTPError as exc:
            skipped.append((slug, f"request failed: {exc}"))
            continue
        if response.status_code != 200 or not response.content:
            skipped.append((slug, f"HTTP {response.status_code}, {len(response.content)} bytes"))
            continue
        text = html_to_text(response.text)
        if len(text) < 500 or "Continue to the Internet" in text[:300]:
            skipped.append((slug, f"no document text returned ({len(text)} characters)"))
            continue
        (SOURCES_DIR / f"{slug}.txt").write_text(text, encoding="utf-8")
        rows.append([slug, DOCUMENT_TITLES.get(slug, title), title, publisher, doc_type, "EU", url, date.today().isoformat(), effective_from, len(text), notes])
        print(f"saved   {slug}  ({len(text):,} characters)")

    with SOURCES_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["slug", "document_title", "version_label", "publisher", "document_type", "jurisdiction", "url",
                         "retrieved_on", "effective_from", "characters", "notes"])
        writer.writerows(rows)
    for slug, reason in skipped:
        print(f"skipped {slug}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
