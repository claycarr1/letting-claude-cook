"""The USDA PDF parser against the saved August 2026 reports (expected values checked against the
rendered Low-/Moderate-/Liberal PDF page and the Thrifty PDF text)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_cooking_cost import USDA_REPORTS, latest_usda_pdfs, parse_usda, pdf_text  # noqa: E402

RAW = ROOT / "data" / "raw" / "usda"


def _parse(name, report):
    path = RAW / name
    if not path.exists():
        pytest.skip(f"{path} not saved")
    return parse_usda(pdf_text(path.read_bytes()), USDA_REPORTS[report])


def test_low_moderate_liberal_august_2026():
    rows, month = _parse("CostofFoodAug2026LowModLib.pdf", "LowModLib")
    assert month == "August 2026"
    weekly = {(plan, sex): w for plan, sex, age, w, m, q in rows}
    assert weekly[("Low-Cost", "Female")] == 63.60
    assert weekly[("Moderate-Cost", "Female")] == 77.60
    assert weekly[("Liberal", "Female")] == 99.00
    assert weekly[("Low-Cost", "Male")] == 73.20
    assert weekly[("Moderate-Cost", "Male")] == 91.90
    assert weekly[("Liberal", "Male")] == 112.20
    monthly = {(plan, sex): m for plan, sex, age, w, m, q in rows}
    assert monthly[("Liberal", "Male")] == 486.20
    assert {age for _, _, age, *_ in rows} == {"19-50"}


def test_thrifty_august_2026():
    rows, month = _parse("CostofFoodAug2026Thrifty.pdf", "Thrifty")
    assert month == "August 2026"
    assert [(sex, age, w) for _, sex, age, w, _, _ in rows] == [("Female", "20-50", 58.50), ("Male", "20-50", 73.60)]


def test_latest_pdf_links():
    html = ('<a href="/f/CostofFoodJul2026Thrifty.pdf"></a><a href="/f/CostofFoodAug2026Thrifty.pdf"></a>'
            '<a href="/f/CostofFoodDec2025LowModLib.pdf"></a><a href="/f/CostofFoodAug2026LowModLib.pdf"></a>')
    links = latest_usda_pdfs(html)
    assert links["Thrifty"].endswith("CostofFoodAug2026Thrifty.pdf")
    assert links["LowModLib"].endswith("CostofFoodAug2026LowModLib.pdf")
