#!/usr/bin/env python3
"""Step 2a: cooking cost data. Fetch the latest USDA Food Plans "Cost of Food at Home" reports and
BLS average retail food prices (U.S. city average and Northeast region); save raw copies; extract
the values. No modelling or calculations happen here (see src/cooking.py).

Writes data/cooking_cost.csv with columns: item, value, unit, source_url, fetched_at, notes
(the same layout as data/huds_prices.csv). The notes column quotes the text each value was read
from.

  USDA: weekly cost of the Thrifty, Low-Cost, Moderate-Cost and Liberal food plans for a female
        and a male adult (Thrifty: 20-50 years; the other three: 19-50 years), U.S. average,
        individuals in 4-person households. Parsed from the PDFs with the standard library.
  BLS:  average prices (series APU0000xxxxxx = U.S. city average, APU0100xxxxxx = Northeast) for
        the latest month both areas report, from the BLS public API v1 (no key needed). BLS
        doesn't publish average prices for the Boston metro area; Northeast is the closest.

Usage:  python3 scripts/fetch_cooking_cost.py            (download, save raw copies, parse)
        python3 scripts/fetch_cooking_cost.py --offline  (re-parse the saved raw copies)
Python 3.9+, standard library only.
"""

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_USDA = ROOT / "data" / "raw" / "usda"
RAW_BLS = ROOT / "data" / "raw" / "bls"
OUT_CSV = ROOT / "data" / "cooking_cost.csv"
FIELDS = ["item", "value", "unit", "source_url", "fetched_at", "notes"]
USER_AGENT = "Mozilla/5.0 (meal-plan-research script; course project)"

USDA_PAGE = "https://www.fna.usda.gov/research/cnpp/usda-food-plans/cost-food-monthly-reports"
USDA_BASE = "https://www.fna.usda.gov"
USDA_REPORTS = {"Thrifty": ["Thrifty"], "LowModLib": ["Low-Cost", "Moderate-Cost", "Liberal"]}

BLS_API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_AREAS = {"0000": "U.S. city average", "0100": "Northeast"}
# BLS average-price item codes tried; only those with data for both areas in the same month are kept.
BLS_ITEMS = {
    "701111": "Flour, white, all purpose, per lb",
    "701312": "Rice, white, long grain, uncooked, per lb",
    "701322": "Spaghetti and macaroni, per lb",
    "702111": "Bread, white, pan, per lb",
    "702212": "Bread, whole wheat, pan, per lb",
    "703112": "Ground beef, 100% beef, per lb",
    "704111": "Bacon, sliced, per lb",
    "706111": "Chicken, fresh, whole, per lb",
    "FF1101": "Chicken breast, boneless, per lb",
    "708111": "Eggs, grade A, large, per doz",
    "709112": "Milk, fresh, whole, fortified, per gal",
    "710212": "Cheddar cheese, natural, per lb",
    "711211": "Bananas, per lb",
    "711311": "Oranges, navel, per lb",
    "712112": "Potatoes, white, per lb",
    "712211": "Lettuce, iceberg, per lb",
    "712311": "Tomatoes, field grown, per lb",
    "717311": "Coffee, 100% ground roast, per lb",
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read(), resp.geturl()


# ---------------------------------------------------------------------------- USDA

def pdf_text(data: bytes) -> str:
    """Text of a simple PDF: the strings drawn by Tj/TJ in every Flate-compressed content stream,
    with a line break at each text-positioning operator. Enough for the USDA tables, which use
    plain TrueType fonts with standard encoding."""
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            stream = zlib.decompress(m.group(1))
        except zlib.error:
            continue
        for op in re.finditer(rb"\[(.*?)\]\s*TJ|\(((?:\\.|[^\\)])*)\)\s*Tj|(T\*|Td|TD|Tm|ET)\b", stream, re.S):
            if op.group(3):
                out.append("\n" if op.group(3) in (b"ET", b"Tm", b"T*") else "")
                continue
            src = op.group(1) if op.group(1) is not None else b"(" + op.group(2) + b")"
            s = b"".join(re.findall(rb"\(((?:\\.|[^\\)])*)\)", src, re.S))
            out.append(re.sub(rb"\\(.)", rb"\1", s).decode("latin-1"))
    return "".join(out)


def latest_usda_pdfs(page_html: str):
    """{report: url} for the newest month's Thrifty and LowModLib PDFs linked on the page."""
    found = {}
    for report in USDA_REPORTS:
        links = re.findall(rf'href="([^"]*CostofFood([A-Z][a-z]{{2}})(\d{{4}}){report}\.pdf)"', page_html)
        if not links:
            raise SystemExit(f"no {report} PDF link on {USDA_PAGE}")
        months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
        href, mon, year = max(links, key=lambda l: (int(l[2]), months.index(l[1])))
        found[report] = href if href.startswith("http") else USDA_BASE + href
    return found


def parse_usda(text: str, plans):
    """[(plan, sex, age_group, weekly, monthly, quote)] for adult women and men, plus the report month."""
    flat = re.sub(r"\s+", "", text)
    month = re.search(r"U\.S\.Average,([A-Z][a-z]+)(\d{4})", flat)
    if not month:
        raise ValueError("report month not found")
    rows = []
    for sex, nxt in (("Female", "Male:"), ("Male", "Food")):
        block = flat[flat.index(sex + ":"):]
        m = re.search(r"(19-50|20-50)years((?:\$[\d,]+\.\d{2})+)", block)
        if not m:
            raise ValueError(f"{sex} adult row not found")
        amounts = [float(a.replace(",", "")) for a in re.findall(r"\$([\d,]+\.\d{2})", m.group(2))]
        if len(amounts) != 2 * len(plans):
            raise ValueError(f"{sex} adult row has {len(amounts)} amounts, expected {2 * len(plans)}")
        quote = f"{sex}: {m.group(1)} years " + " ".join(f"${a:.2f}" for a in amounts)
        for i, plan in enumerate(plans):
            rows.append((plan, sex, m.group(1), amounts[2 * i], amounts[2 * i + 1], quote))
    return rows, f"{month.group(1)} {month.group(2)}"


def usda_rows(offline: bool):
    RAW_USDA.mkdir(parents=True, exist_ok=True)
    page_path = RAW_USDA / "cost_food_monthly_reports.html"
    if offline:
        page = page_path.read_text(encoding="utf-8")
    else:
        body, _ = http(USDA_PAGE)
        page = body.decode("utf-8", "replace")
        page_path.write_text(page, encoding="utf-8")
    out = []
    for report, url in latest_usda_pdfs(page).items():
        pdf_path = RAW_USDA / url.rsplit("/", 1)[1]
        if not offline:
            pdf_path.write_bytes(http(url)[0])
        fetched = datetime.fromtimestamp(pdf_path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()
        rows, month = parse_usda(pdf_text(pdf_path.read_bytes()), USDA_REPORTS[report])
        for plan, sex, age, weekly, monthly, quote in rows:
            item = f"USDA {plan} food plan: {sex.lower()} {age}, {month}"
            note = (f"Official USDA Food Plans, U.S. average, {month}; individuals in 4-person households "
                    f"(USDA: add 20% for 1-person households); raw copy data/raw/usda/{pdf_path.name}; "
                    f'quote: "{quote}"')
            out.append({"item": item + ", weekly", "value": f"{weekly:.2f}", "unit": "USD per week",
                        "source_url": url, "fetched_at": fetched, "notes": note})
            out.append({"item": item + ", monthly", "value": f"{monthly:.2f}", "unit": "USD per month",
                        "source_url": url, "fetched_at": fetched, "notes": note})
    return out


# ---------------------------------------------------------------------------- BLS

def bls_rows(offline: bool, year: int):
    RAW_BLS.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_BLS / "average_prices.json"
    ids = [f"APU{area}{item}" for item in BLS_ITEMS for area in BLS_AREAS]
    if offline:
        saved = json.loads(raw_path.read_text())
    else:
        series = []
        for i in range(0, len(ids), 25):  # API v1: at most 25 series per request
            body = json.dumps({"seriesid": ids[i:i + 25], "startyear": str(year - 1), "endyear": str(year)}).encode()
            resp = json.loads(http(BLS_API, body, {"Content-Type": "application/json"})[0])
            if resp.get("status") != "REQUEST_SUCCEEDED":
                raise SystemExit(f"BLS API: {resp.get('status')} {resp.get('message')}")
            series += resp["Results"]["series"]
        saved = {"fetched_at": now_iso(), "request": {"url": BLS_API, "seriesid": ids}, "series": series}
        raw_path.write_text(json.dumps(saved, indent=1))
    by_id = {s["seriesID"]: {(d["year"], d["period"]): d["value"] for d in s["data"] if d["value"] not in ("-", "")}
             for s in saved["series"]}
    out = []
    for item, name in BLS_ITEMS.items():
        us, ne = by_id.get(f"APU0000{item}", {}), by_id.get(f"APU0100{item}", {})
        common = sorted(set(us) & set(ne))
        if not common:
            continue
        y, period = common[-1]  # the latest month both areas report
        for area, values in (("0000", us), ("0100", ne)):
            sid = f"APU{area}{item}"
            out.append({"item": f"BLS average price, {BLS_AREAS[area]}: {name}, {y}-{period[1:]}",
                        "value": values[(y, period)], "unit": "USD", "source_url": f"https://data.bls.gov/timeseries/{sid}",
                        "fetched_at": saved["fetched_at"],
                        "notes": f"series {sid}, {y} {period}; raw copy data/raw/bls/average_prices.json"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="re-parse saved raw copies instead of downloading")
    ap.add_argument("--year", type=int, default=datetime.now().year, help="latest year of BLS data to request")
    args = ap.parse_args()
    rows = usda_rows(args.offline) + bls_rows(args.offline, args.year)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT_CSV.relative_to(ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    sys.exit(main())
