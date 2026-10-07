#!/usr/bin/env python3
"""Step 1: fetch HUDS and Harvard College pages, save raw copies, extract prices and rules.

Writes data/huds_prices.csv with columns: item, value, unit, source_url, fetched_at, notes.
Every value comes from a fetched (or manually saved) page -- nothing is hardcoded.
The notes column quotes the exact page text each value was read from.
No modelling or calculations happen here.

Usage:  python3 scripts/fetch_prices.py      (Python 3.9+, standard library only)

dining.harvard.edu blocks scripted requests (HTTP 403 via Akamai). For those pages,
open each one in a browser, "Save Page As... > Web Page, HTML Only", and put it at
data/raw/manual/<slug>.html (slugs listed in SOURCES). The script parses that copy,
checks its canonical URL, and records the file's save time as fetched_at.
"""

import csv
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
MANUAL_DIR = RAW_DIR / "manual"
OUT_CSV = ROOT / "data" / "huds_prices.csv"

USER_AGENT = "Mozilla/5.0 (meal-plan-research script; course project)"
FIELDS = ["item", "value", "unit", "source_url", "fetched_at", "notes"]
NUMBER_WORDS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}
MONEY = r"\d{1,3}(?:,\d{3})*(?:\.\d{2})?"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch(url):
    """Return (html_text, None) on success or (None, error_message)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace"), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"network error: {e.reason}"


class BlockParser(HTMLParser):
    """Flatten HTML into text blocks, skipping scripts, styles and site chrome."""

    BLOCK_TAGS = {"p", "li", "tr", "td", "th", "div", "br", "h1", "h2", "h3", "h4", "h5", "dt", "dd", "section"}
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.buf, self.skip_depth = [], [], 0

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            self.blocks.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        elif tag in self.BLOCK_TAGS:
            self.flush()

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in self.BLOCK_TAGS:
            self.flush()

    def handle_data(self, data):
        if not self.skip_depth:
            self.buf.append(data)


def page_text(page):
    p = BlockParser()
    p.feed(page)
    p.flush()
    text = " ".join(p.blocks)
    # Normalise typographic dashes and quotes so patterns stay simple.
    return text.translate(str.maketrans({"–": "-", "—": "-", "’": "'", "“": '"', "”": '"'}))


def canonical_url(page):
    m = re.search(r'<link rel="canonical" href="([^"]+)"', page)
    return m.group(1) if m else None


class Extractor:
    """Collects CSV rows from one page. Every lookup either adds a row quoting the page or a NOT EXTRACTED row."""

    def __init__(self, page, url, fetched_at, provenance):
        self.text = page_text(page)
        self.url, self.fetched_at, self.provenance = url, fetched_at, provenance
        self.rows = []

    def add(self, item, value, unit, quote, note=""):
        notes = f'{self.provenance}; quote: "{quote}"' + (f"; {note}" if note else "")
        self.rows.append({"item": item, "value": value, "unit": unit, "source_url": self.url,
                          "fetched_at": self.fetched_at, "notes": notes})

    def missing(self, item, pattern):
        self.rows.append(failure_row(item, self.url, self.fetched_at,
                                     f"{self.provenance}; pattern not found on page: {pattern}"))

    def value(self, item, pattern, unit, group=1, note=""):
        m = re.search(pattern, self.text)
        if not m:
            self.missing(item, pattern)
            return None
        raw = m.group(group)
        val = NUMBER_WORDS.get(raw.lower(), raw.replace(",", "")) if unit != "text" else raw
        self.add(item, val, unit, m.group(0), note)
        return m

    def rule(self, item, pattern):
        """A rule is stored verbatim: value = the sentence(s) from the page."""
        m = re.search(pattern, self.text)
        if not m:
            self.missing(item, pattern)
            return None
        self.add(item, m.group(0), "rule", m.group(0))
        return m


def extract_undergrad_meal_plans(ex):
    ex.rule("Resident plan: requirement",
            r"Harvard College requires all undergraduates living on campus to have an unlimited meal plan\.")
    ex.value("Resident plan: number of dining halls", r"We operate (\w+) dining halls", "dining halls")

    fy = re.search(r"(FY\d{2}-\d{2}) Rates", ex.text)
    label = fy.group(1) if fy else "year not found"
    ex.value(f"Non-resident plans {label}: fall term dates",
             r"FY\d{2}-\d{2} Rates \(Fall Term: ([^/]+?) //", "text")
    ex.value(f"Non-resident plans {label}: spring term dates",
             r"FY\d{2}-\d{2} Rates \(Fall Term: [^/]+// Spring Term: ([^)]+?)\)", "text")
    for n in (5, 10, 21):
        ex.value(f"Non-resident {n} meals/week plan {label}",
                 rf"FY\d{{2}}-\d{{2}} Rates.*?\b{n} Meal Plan // \$({MONEY}) per term", "USD/term")

    ex.rule("Non-resident plans: refunds", r"The program is non-refundable\.")
    ex.rule("Non-resident plans: swipes per meal period",
            r"Participants are allowed one meal swipe per meal period[^.]*\.")
    ex.rule("Non-resident plans: where meals can be used", r"Meals can be used at any of the Houses[^.]*\.")
    ex.rule("Non-resident plans: weekly forfeiture", r"Unused meal balances are not transferable[^.]*\.")
    ex.rule("Summer: no summer plan for non-residents", r"Summer meal plans are not available[^.]*\.")


def extract_undergrad_faqs(ex):
    ex.value("Resident plan: BoardPlus per semester", r"BoardPlus: \$(\d+) per semester", "USD/semester")
    ex.rule("Resident plan: BoardPlus expiry", r"You may not add more BoardPlus dollars[^.]*\.")
    ex.value("Resident plan: BoardPlus expiry date listed on FAQ page",
             r"BoardPlus for the \d{4}-\d{2} school year expires at the end-of-day on ([^.]+)\.", "text",
             note="check the school year in the quote; the FAQ may not be updated for the current year")

    yr = re.search(r"Guest Meal Rates for (\d{4}-\d{2}) are as follows", ex.text)
    label = yr.group(1) if yr else "year not found"
    guest = re.compile(rf"(Breakfast|Brunch|Lunch|Dinner) - (.+?) \$({MONEY}) \+ (\d+)% MMBT = \$({MONEY})")
    matches = list(guest.finditer(ex.text))
    if not matches:
        ex.missing(f"Guest meal rates {label}", guest.pattern)
    else:
        ex.add(f"Guest meal rates {label}: Massachusetts meals tax (MMBT)", matches[0].group(4), "percent",
               matches[0].group(0))
    for m in matches:
        meal, when = m.group(1), m.group(2).strip()
        ex.add(f"Guest meal {label}: {meal} ({when}), before tax", m.group(3), "USD/meal", m.group(0))
        ex.add(f"Guest meal {label}: {meal} ({when}), incl. tax", m.group(5), "USD/meal", m.group(0))

    # The FAQ also lists non-resident rates; record them under whatever year label the page gives.
    fy = re.search(r"(FY\d{2}-\d{2}) rates \(Fall Term: ([^;]+); Spring Term: ([^)]+)\):", ex.text)
    if not fy:
        ex.missing("Non-resident plan rates on FAQ page", "FYxx-xx rates (Fall Term: ...)")
        return
    for n in (5, 10, 21):
        ex.value(f"Non-resident {n} meals/week plan {fy.group(1)} (as listed on FAQ page)",
                 rf"{fy.group(1)} rates.*?\b{n} Meal Plan \$({MONEY}) per term", "USD/term",
                 note=f"FAQ page labels these {fy.group(1)}; the meal-plans page lists its own rates separately")


def extract_grad_meal_plans(ex):
    yr = re.search(r"Academic Year (\d{4}-\d{2})", ex.text)
    label = yr.group(1) if yr else "year not found"

    ex.rule("Commons at Lehman Hall plan: who it is for / required of",
            r"Available to any Harvard affiliate \(and required of the Harvard Griffin GSAS residence hall occupants\)[^.]*\.")
    for term in ("Fall", "Spring"):
        m = ex.value(f"Commons at Lehman Hall plan {label}: {term.lower()} term declining balance",
                     rf"{term} Term \(([^)]+)\) - \$({MONEY}) in declining balance", "USD/term", group=2)
        if m:
            ex.add(f"Commons at Lehman Hall plan {label}: {term.lower()} term dates", m.group(1), "text", m.group(0))
    ex.rule("Commons at Lehman Hall plan: cancellation", r"The meal plan is for a full year and may not be cancelled\.")
    ex.rule("Commons at Lehman Hall plan: rollover and forfeiture",
            r"Declining balance dollars will be allocated[^.]*\. Unused declining balance dollars will be forfeited at the end of the academic year\.")
    ex.rule("Commons at Lehman Hall plan: where it can be used",
            r"The meal plan cannot be used at other professional school or campus cafes, nor at College dining halls\.")
    ex.value("Commons at Lehman Hall: days and meals served",
             r"The Commons at Lehman Hall (Monday - Friday L, D)", "text")

    ex.value("GradPlus Regular: monthly amount", r"The Regular plan provides \$(\d+) a month", "USD/month")
    ex.value("GradPlus Deluxe: monthly amount", r"the Deluxe plan provides \$(\d+) a month", "USD/month")
    table = r"GradPlus Regular GradPlus Deluxe Fall Semester (\d{4}) \$(\d+) \$(\d+) Spring Semester (\d{4}) \$(\d+) \$(\d+)"
    m = re.search(table, ex.text)
    if not m:
        ex.missing("GradPlus semester amounts table", table)
    else:
        ex.add(f"GradPlus Regular {label}: fall {m.group(1)} semester amount", m.group(2), "USD/semester", m.group(0))
        ex.add(f"GradPlus Deluxe {label}: fall {m.group(1)} semester amount", m.group(3), "USD/semester", m.group(0))
        ex.add(f"GradPlus Regular {label}: spring {m.group(4)} semester amount", m.group(5), "USD/semester", m.group(0))
        ex.add(f"GradPlus Deluxe {label}: spring {m.group(4)} semester amount", m.group(6), "USD/semester", m.group(0))
    ex.value("GradPlus: discount on purchases made with the plan",
             r"you will receive a (\d+)% discount for any purchase made with your meal plan", "percent")
    ex.value(f"GradPlus {label}: fall plan dates", r"The fall meal plan runs from ([^.]+?)\.", "text")
    ex.value(f"GradPlus {label}: spring plan dates", r"The spring meal plan runs from ([^.]+?)\.", "text")
    ex.rule("GradPlus: rollover", r"Funds will roll over from the fall semester to the spring, if enrolled\.")
    ex.rule("GradPlus: forfeiture and refunds",
            r"Unused declining balance dollars will be forfeited at the end of the academic year \(final day[^)]*\)\. There will be no meal plan refunds\.")


def extract_coa(ex):
    """Harvard College 2026-27 Cost of Attendance table. 'Food' is Harvard's name for the board fee."""
    m = re.search(r"2026-2027 Cost of Attendance(.*?)(?:2025-2026 Cost of Attendance|$)", ex.text)
    if not m:
        ex.missing("Harvard College 2026-27 cost of attendance", "2026-2027 Cost of Attendance")
        return
    section = m.group(1)
    money = r"\d{1,3}(?:,\d{3})*"
    for row in re.finditer(rf"([A-Z][A-Za-z \-]+?)\s*\$({money})(?:\s*-\s*\$({money}))?", section):
        label, lo, hi = row.group(1).strip(), row.group(2), row.group(3)
        if label.startswith("In addition"):
            continue
        val = f"{lo.replace(',', '')}-{hi.replace(',', '')}" if hi else lo.replace(",", "")
        note = "published as a range" if hi else ""
        if label == "Food":
            label = "Board fee (listed as 'Food')"
            note = "official Harvard College 2026-27 board fee for resident undergrads"
        ex.add(f"Harvard College 2026-27 cost of attendance: {label}", val, "USD/year", row.group(0), note)
    ex.value("Harvard College 2026-27 health insurance (if not waived)",
             r"health insurance is required at a cost of \$(" + money + r") \(for 2026-27\)", "USD/year")


# slug -> (url, extractor)
SOURCES = {
    "huds_undergrad_meal_plans": ("https://www.dining.harvard.edu/undergraduate-dining/meal-plans", extract_undergrad_meal_plans),
    "huds_undergrad_faqs": ("https://www.dining.harvard.edu/undergraduate-dining/faqs", extract_undergrad_faqs),
    "huds_grad_meal_plans": ("https://www.dining.harvard.edu/graduate-professional-dining/meal-plans", extract_grad_meal_plans),
    "college_cost_of_attendance": ("https://college.harvard.edu/financial-aid/how-aid-works", extract_coa),
}


def failure_row(item, url, fetched_at, why):
    return {"item": item, "value": "", "unit": "", "source_url": url, "fetched_at": fetched_at,
            "notes": f"NOT EXTRACTED: {why}"}


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []

    for slug, (url, extractor) in SOURCES.items():
        fetched_at = now_iso()
        page, err = fetch(url)
        if page is not None:
            saved = RAW_DIR / f"{slug}_{stamp}.html"
            saved.write_text(page, encoding="utf-8")
            provenance = f"live fetch, raw copy {saved.relative_to(ROOT)}"
        else:
            manual = MANUAL_DIR / f"{slug}.html"
            if not manual.exists():
                print(f"[FAIL] {slug}: {err}", file=sys.stderr)
                rows.append(failure_row(slug, url, fetched_at,
                                        f"live fetch failed ({err}); no manual copy at {manual.relative_to(ROOT)}"))
                continue
            page = manual.read_text(encoding="utf-8", errors="replace")
            canon = canonical_url(page)
            if canon != url:
                print(f"[FAIL] {slug}: manual copy's canonical URL is {canon!r}, expected {url}", file=sys.stderr)
                rows.append(failure_row(slug, url, fetched_at,
                                        f"manual copy {manual.relative_to(ROOT)} has canonical URL {canon!r}, not this page"))
                continue
            fetched_at = datetime.fromtimestamp(manual.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()
            provenance = (f"live fetch blocked ({err}); browser-saved copy {manual.relative_to(ROOT)}, "
                          f"canonical URL verified; fetched_at = file save time")

        ex = Extractor(page, url, fetched_at, provenance)
        extractor(ex)
        failed = sum(1 for r in ex.rows if r["notes"].startswith("NOT EXTRACTED"))
        print(f"[{'ok' if not failed else 'WARN'}] {slug}: {len(ex.rows)} rows, {failed} not extracted", file=sys.stderr)
        rows.extend(ex.rows)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT_CSV.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
