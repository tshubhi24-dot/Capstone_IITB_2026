"""10-K ingestion — download, parse, and chunk SEC filings.

Downloads 10-K HTML from EDGAR, splits by Item (1A Risk Factors, 7 MD&A),
keeps tables as structured text, and saves passages with metadata.

Each passage gets a unique passage_id used for citations in answers.
passage_id format: {ticker}_{year}_{item}_{seq}
  e.g. MSFT_2024_item7_003
"""

from __future__ import annotations

from analystdesk.paths import APP_ROOT

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

from analystdesk.research.scope import COMPANIES

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"
CACHE_DIR = APP_ROOT / "data" / "edgar_cache"
PASSAGES_DIR = APP_ROOT / "data" / "passages"
# Plain-text chunks (tables flattened) for the E4 table-aware ablation
PLAIN_PASSAGES_DIR = APP_ROOT / "data" / "passages_plain"
USER_AGENT = "AnalystDesk IITBombay 25.jayshree@gmail.com"

# Items to extract — key for the Analyst Desk use case
TARGET_ITEMS = {
    "item1a": "Risk Factors",
    "item7":  "Management Discussion and Analysis",
}

# Item-number headings ("Item 1A.", "ITEM 7 MANAGEMENT'S ...", "Item 9A").
# Every item is captured so that any next item (1B, 1C, 2, 7A, 8...) ends the
# current section. The "." or space after the number is required: a bare
# "Item 8" line is a cross-reference link (Visa has dozens), not a heading.
ITEM_HEADING = re.compile(r"item\s*(\d{1,2}[a-c]?)[.\s]")

# Title-only headings, for filers that do not number their sections
# (Morgan Stanley) or put them in an annual-report exhibit (Wells Fargo,
# whose MD&A is titled "Financial Review"). Only used when item-number
# headings do not find the target sections. Short generic titles must match
# exactly so risk-factor subheadings like "Cybersecurity risks" don't end
# Item 1A early; long titles match as prefixes.
EXACT_TITLES = {
    "risk factors": "item1a",
    "financial review": "item7",
    "unresolved staff comments": "item1b",
    "cybersecurity": "item1c",
    "legal proceedings": "item3",
    "controls and procedures": "item9a",
}
PREFIX_TITLES = {
    "management's discussion and analysis": "item7",
    "quantitative and qualitative disclosures about": "item7a",
    "financial statements and supplementary data": "item8",
}

# A target section shorter than this is treated as not found (e.g. a stub
# that points to an exhibit).
MIN_SECTION_CHARS = 5000

# Headings that always follow MD&A. Filers that don't number their body
# sections (JPM) otherwise run MD&A on into the financial statements. Only
# applied past MDA_END_MIN_CHARS so a page index at the start can't cut it.
MDA_END_TITLES = (
    "report of independent registered public accounting firm",
    "management's report on internal control over financial reporting",
)
MDA_END_MIN_CHARS = 10000

FILINGS_CACHE = CACHE_DIR / "filings"


def _pad_cik(cik: str) -> str:
    return cik.lstrip("0").zfill(10)


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _fetch_cached(url: str, cache_file: Path) -> bytes:
    """Fetch url once; later calls read the local copy (EDGAR asks for caching)."""
    if cache_file.exists():
        return cache_file.read_bytes()
    data = _fetch(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(data)
    time.sleep(0.2)
    return data


def _find_10k(cik: str, fiscal_year: int) -> tuple[str, str] | None:
    """Return (accession, primary_document) of the 10-K for a fiscal year.

    The fiscal year is the year the reporting period ends (reportDate), the
    same rule edgar.py uses for XBRL facts, so passages and numbers line up
    for June-end (MSFT) and January-end (NVDA) filers alike.
    """
    padded = _pad_cik(cik)
    cache_file = CACHE_DIR / f"submissions_{padded}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
    else:
        data = json.loads(_fetch(SUBMISSIONS_URL.format(cik=padded)))
        cache_file.write_text(json.dumps(data))
        time.sleep(0.2)

    def _search_filings(filings: dict) -> tuple[str, str] | None:
        for form, report_date, accn, doc in zip(
            filings.get("form", []),
            filings.get("reportDate", []),
            filings.get("accessionNumber", []),
            filings.get("primaryDocument", []),
        ):
            if form == "10-K" and report_date[:4] == str(fiscal_year):
                return accn, doc
        return None

    found = _search_filings(data.get("filings", {}).get("recent", {}))
    if found:
        return found

    # Recent filings may not go far enough back — check older filings pages
    for older in data.get("filings", {}).get("files", []):
        name = older.get("name", "")
        older_cache = CACHE_DIR / name
        if older_cache.exists():
            older_data = json.loads(older_cache.read_text())
        else:
            older_url = f"https://data.sec.gov/submissions/{name}"
            try:
                older_data = json.loads(_fetch(older_url))
                older_cache.write_text(json.dumps(older_data))
                time.sleep(0.2)
            except Exception:
                continue
        found = _search_filings(older_data)
        if found:
            return found

    return None


def _heading_label(line: str, use_titles: bool) -> str | None:
    """Return the item label if this line is a section heading, else None."""
    s = re.sub(r"\s+", " ", line.strip().lower().replace("’", "'"))
    # Headings are short-to-medium lines; the 100-char cap avoids matching body
    # text while allowing MSFT's "ITEM 7. MANAGEMENT'S DISCUSSION..." headers
    if not s or len(s) >= 100:
        return None
    m = ITEM_HEADING.match(s)
    if m:
        return f"item{m.group(1)}"
    s = s.rstrip(" .:")
    if use_titles:
        if s in EXACT_TITLES:
            return EXACT_TITLES[s]
        for prefix, label in PREFIX_TITLES.items():
            if s.startswith(prefix):
                return label
    return None


def _item_order(label: str) -> tuple[int, str]:
    m = re.fullmatch(r"item(\d+)([a-c]?)", label)
    return int(m.group(1)), m.group(2)


def _split_sections(lines: list[str], use_titles: bool) -> dict[str, str]:
    """Split lines into sections at headings; keep the longest run per target.

    A heading for the section we are already in is a running page header
    (Mastercard repeats "ITEM 1A. RISK FACTORS" on every page), so it continues
    the section instead of restarting it. Table-of-contents entries and
    cross-references produce short runs, which lose to the real section.

    Items run in increasing order, so once inside a real section, a numbered
    heading that jumps back (BAC's MD&A links "Item 1A. Risk Factors" on its
    own line) is a cross-reference and stays in the text. Title headings are
    exempt: WFC's annual report puts "Risk Factors" after its MD&A.
    """
    best: dict[str, list[str]] = {}
    current, run, run_chars = None, [], 0

    def _close():
        if current in TARGET_ITEMS and len("\n".join(run)) > len("\n".join(best.get(current, []))):
            best[current] = run

    in_table = False
    for line in lines:
        # Rows of a table of contents ("Item 1A | Risk Factors | 12") are not
        # headings; only text outside table blocks can start a section.
        if line.strip() in (TABLE_START, TABLE_END):
            in_table = line.strip() == TABLE_START
            label = None
        else:
            label = None if in_table else _heading_label(line, use_titles)
        if (label and current and not use_titles and run_chars > 2000
                and _item_order(label) < _item_order(current)):
            label = None
        if label and label != current:
            _close()
            current, run, run_chars = label, [], 0
        elif label is None and current:
            run.append(line)
            run_chars += len(line)
    _close()

    if "item7" in best:
        chars = 0
        for i, line in enumerate(best["item7"]):
            s = re.sub(r"\s+", " ", line.strip().lower().replace("’", "'"))
            if chars > MDA_END_MIN_CHARS and s.startswith(MDA_END_TITLES):
                best["item7"] = best["item7"][:i]
                break
            chars += len(line)

    # Normalize whitespace-only lines to "" so they become \n\n when joined,
    # giving _chunk_text the paragraph boundaries it needs.
    return {
        k: "\n".join("" if not ln.strip() else ln for ln in v).strip()
        for k, v in best.items()
    }


TABLE_START, TABLE_END = "[TABLE]", "[/TABLE]"
NUMERIC_CELL = re.compile(r"^\(?[$€£]?\s?-?[\d,]*\d(\.\d+)?\)?%?$|^[—–-]$")


def _table_rows(table) -> list[str]:
    """Render an HTML table as 'cell | cell' rows.

    10-K tables spread one value over several cells ("$" | "1,234" | ")"),
    with empty spacer cells in between; those are merged back together.
    """
    rows = []
    for tr in table.find_all("tr"):
        cells, pending = [], ""
        for td in tr.find_all(["td", "th"]):
            c = " ".join(td.get_text(" ").split())
            if not c:
                continue
            if c in ("$", "€", "£"):
                pending = c
                continue
            if c in (")", "%", ")%") and cells:
                cells[-1] += c
                continue
            cells.append(pending + c)
            pending = ""
        if cells:
            rows.append(" | ".join(cells))
    return rows


def _mark_tables(soup) -> None:
    """Replace data tables with marked 'cell | cell' text blocks in place.

    Only tables with 2+ rows and 2+ numeric cells count as data; 10-Ks also
    use tables for layout (item headings, page footers), and those must stay
    plain text so heading detection still sees them.
    """
    for table in soup.find_all("table"):
        if table.find_parent("table"):
            continue
        rows = _table_rows(table)
        numeric = sum(
            1 for r in rows for c in r.split(" | ") if NUMERIC_CELL.match(c)
        )
        if len(rows) >= 2 and numeric >= 2:
            table.replace_with(
                "\n\n" + TABLE_START + "\n" + "\n".join(rows) + "\n" + TABLE_END + "\n\n"
            )


def _parse_items(html: str, table_aware: bool = True) -> dict[str, str]:
    """Extract Item 1A and Item 7 text from 10-K HTML.

    Scans line-by-line so item headings embedded mid-paragraph (common in
    iXBRL filings like Alphabet) are found. Tries numbered "Item" headings
    first and falls back to section titles for filers that don't number them.
    Blank lines are preserved so _chunk_text can split on paragraph boundaries.

    table_aware keeps data tables as marked row blocks; False flattens them
    into the text stream (the plain-text arm of the E4 ablation).
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "footer", "header"]):
        tag.decompose()
    if table_aware:
        _mark_tables(soup)

    lines = soup.get_text(separator="\n").split("\n")

    result = _split_sections(lines, use_titles=False)
    if all(len(result.get(k, "")) >= MIN_SECTION_CHARS for k in TARGET_ITEMS):
        return result
    by_title = _split_sections(lines, use_titles=True)
    for k in TARGET_ITEMS:
        if len(by_title.get(k, "")) > len(result.get(k, "")):
            result[k] = by_title[k]
    return {k: v for k, v in result.items() if v}


def _split_large_para(para: str, max_chars: int, overlap: int) -> list[str]:
    """Sentence-level fallback for paragraphs that exceed max_chars."""
    sentences = re.split(r"(?<=[.!?])\s+", para)
    parts, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) > max_chars and current:
            parts.append(current.strip())
            current = current[-overlap:] + " " + sent
        else:
            current = (current + " " + sent).strip()
    if current:
        parts.append(current.strip())
    return parts or [para[:max_chars]]


def _chunk_table(rows: list[str], context: str, max_chars: int = 2500) -> list[str]:
    """Split a table into passages by rows, repeating the header row.

    Rows are never cut in half, so every passage holds whole table cells that
    a citation can point at. The context line (usually the table's title, the
    last text line above it) is prefixed so the passage is retrievable.
    """
    header, body = rows[0], rows[1:] or []
    prefix = (f"{context}\n" if context else "") + header
    chunks, current = [], prefix
    for row in body:
        if len(current) + len(row) + 1 > max_chars and current != prefix:
            chunks.append(current)
            current = prefix
        current += "\n" + row
    chunks.append(current)
    return chunks


def _chunk_item(text: str) -> list[tuple[str, str]]:
    """Chunk one item's text into (kind, passage) pairs, tables kept whole.

    Text between table blocks goes through _chunk_text; each table block
    becomes one or more "table" passages via _chunk_table.
    """
    pattern = re.compile(re.escape(TABLE_START) + r"\n(.*?)\n" + re.escape(TABLE_END), re.S)
    out, pos = [], 0
    for m in pattern.finditer(text):
        before = text[pos:m.start()]
        out.extend(("text", c) for c in _chunk_text(before))
        lines_before = [ln.strip() for ln in before.splitlines() if ln.strip()]
        context = lines_before[-1][:200] if lines_before else ""
        rows = [r for r in m.group(1).split("\n") if r.strip()]
        if rows:
            out.extend(("table", c) for c in _chunk_table(rows, context))
        pos = m.end()
    out.extend(("text", c) for c in _chunk_text(text[pos:]))
    return out


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks on paragraph boundaries.

    Falls back to sentence-level splitting for paragraphs larger than max_chars
    (handles filings like GOOGL where risk factors lack blank-line separators).
    """
    raw_paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    paragraphs: list[str] = []
    for para in raw_paras:
        if len(para) > max_chars:
            paragraphs.extend(_split_large_para(para, max_chars, overlap))
        else:
            paragraphs.append(para)

    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            chunks.append(current.strip())
            current = current[-overlap:] + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip()
    if current:
        chunks.append(current.strip())
    return chunks


def ingest_company_year(ticker: str, cik: str, fiscal_year: int,
                        table_aware: bool = True) -> list[dict]:
    """Download, parse and chunk one company-year 10-K. Returns list of passages.

    table_aware=False writes plain-text chunks to PLAIN_PASSAGES_DIR instead,
    for the E4 comparison against table-aware parsing.
    """
    passages_dir = PASSAGES_DIR if table_aware else PLAIN_PASSAGES_DIR
    out_file = passages_dir / f"{ticker}_{fiscal_year}.jsonl"
    if out_file.exists():
        return [json.loads(l) for l in out_file.read_text().splitlines() if l.strip()]

    found = _find_10k(cik, fiscal_year)
    if not found:
        print(f"  ⚠  No 10-K found for {ticker} FY{fiscal_year}")
        return []
    accn, primary_doc = found
    accn_clean = accn.replace("-", "")
    base_url = FILING_URL.format(cik=cik.lstrip("0"), accession=accn_clean, doc="")
    filing_cache = FILINGS_CACHE / ticker / accn_clean

    print(f"  Loading {ticker} FY{fiscal_year} 10-K ({accn})...")
    try:
        html = _fetch_cached(base_url + primary_doc, filing_cache / primary_doc)
        items = _parse_items(html.decode("utf-8", errors="replace"), table_aware)

        # Some banks (WFC) answer Items 1A and 7 by reference to an annual
        # report filed as an exhibit; the largest non-XBRL HTML document in
        # the filing is that report.
        if any(len(items.get(k, "")) < MIN_SECTION_CHARS for k in TARGET_ITEMS):
            index = json.loads(_fetch_cached(base_url + "index.json", filing_cache / "index.json"))
            exhibits = sorted(
                (f for f in index["directory"]["item"]
                 if f["name"].endswith((".htm", ".html"))
                 and f["name"] != primary_doc
                 and not re.fullmatch(r"R\d+\.htm", f["name"])
                 and "index" not in f["name"]),
                key=lambda f: int(f.get("size") or 0),
                reverse=True,
            )
            if exhibits:
                name = exhibits[0]["name"]
                ex_items = _parse_items(
                    _fetch_cached(base_url + name, filing_cache / name).decode("utf-8", errors="replace"),
                    table_aware,
                )
                for k, v in ex_items.items():
                    if len(v) > len(items.get(k, "")):
                        items[k] = v
    except Exception as e:
        print(f"  ⚠  Download failed: {e}")
        return []

    if not items:
        print(f"  ⚠  No items extracted for {ticker} FY{fiscal_year}")
        return []

    passages = []
    for item_key, text in items.items():
        chunks = _chunk_item(text)
        for seq, (kind, chunk) in enumerate(chunks):
            pid = f"{ticker}_{fiscal_year}_{item_key}_{seq:03d}"
            passages.append({
                "passage_id": pid,
                "company": ticker,
                "fiscal_year": fiscal_year,
                "item": item_key,
                "item_label": TARGET_ITEMS.get(item_key, item_key),
                "accession": accn,
                "kind": kind,
                "text": chunk,
            })

    passages_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(json.dumps(p) for p in passages))
    print(f"  ✓  {ticker} FY{fiscal_year}: {len(passages)} passages saved")
    return passages


def ingest_all(companies=None, years=None, table_aware: bool = True) -> list[dict]:
    """Ingest all company-year combinations. Returns all passages."""
    companies = companies or COMPANIES
    years = years or [2022, 2023, 2024]
    all_passages = []
    for company in companies:
        for year in years:
            passages = ingest_company_year(company.ticker, company.cik, year, table_aware)
            all_passages.extend(passages)
    return all_passages


def load_passages(table_aware: bool | None = None) -> list[dict]:
    """Load all saved passages from disk.

    table_aware=None follows AGENT_PASSAGES: "plain" loads the plain-text
    chunks (the E4 ablation), anything else the table-aware ones.
    """
    if table_aware is None:
        table_aware = os.getenv("AGENT_PASSAGES", "tables") != "plain"
    passages = []
    passages_dir = PASSAGES_DIR if table_aware else PLAIN_PASSAGES_DIR
    for f in sorted(passages_dir.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                passages.append(json.loads(line))
    return passages
