"""Hand-worked checks for the cooking cost per meal (src/cooking.py)."""

import csv
import math

import pytest

from cooking import (
    PLANS,
    cooking_cost_per_meal,
    cooking_range,
    northeast_ratios,
    regional_factor,
    usda_weekly,
)

FIELDS = ["item", "value", "unit", "source_url", "fetched_at", "notes"]


def _csv(tmp_path, weekly, bls):
    path = tmp_path / "cooking_cost.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for (plan, sex), v in weekly.items():
            w.writerow({"item": f"USDA {plan} food plan: {sex} 19-50, August 2026, weekly", "value": v})
            w.writerow({"item": f"USDA {plan} food plan: {sex} 19-50, August 2026, monthly", "value": v * 4.333})
        for name, (us, ne) in bls.items():
            w.writerow({"item": f"BLS average price, U.S. city average: {name}, 2026-08", "value": us})
            w.writerow({"item": f"BLS average price, Northeast: {name}, 2026-08", "value": ne})
    return path


@pytest.fixture
def small_csv(tmp_path):
    weekly = {(p, s): v for p, base in zip(PLANS, (60, 63, 84, 105)) for s, v in (("female", base - 6), ("male", base + 6))}
    # Ratios 1.25 and 0.8: geometric mean exactly 1.
    bls = {"Bananas, per lb": (1.00, 1.25), "Bread, per lb": (2.00, 1.60)}
    return _csv(tmp_path, weekly, bls)


def test_parse(small_csv):
    assert usda_weekly(small_csv)["Moderate-Cost"] == {"female": 78, "male": 90}
    assert northeast_ratios(small_csv) == {"Bananas, per lb": pytest.approx(1.25), "Bread, per lb": pytest.approx(0.8)}
    assert regional_factor(small_csv) == pytest.approx(1.0)


def test_cost_per_meal(small_csv):
    # Moderate: (78 + 90) / 2 = 84 a week / 21 meals = $4.00; alone +20% = $4.80; regional factor 1.
    assert cooking_cost_per_meal("Moderate-Cost", 1, csv_path=small_csv) == pytest.approx(4.80)
    assert cooking_cost_per_meal("Moderate-Cost", 4, csv_path=small_csv) == pytest.approx(4.00)
    assert cooking_cost_per_meal("Moderate-Cost", 4, regional=1.1, csv_path=small_csv) == pytest.approx(4.40)
    r = cooking_range(1, csv_path=small_csv)
    assert r["Thrifty"] == pytest.approx(60 / 21 * 1.2) and r["Liberal"] == pytest.approx(105 / 21 * 1.2)


def test_input_checks(small_csv):
    with pytest.raises(ValueError):
        cooking_cost_per_meal("Gourmet", csv_path=small_csv)
    with pytest.raises(ValueError):
        cooking_cost_per_meal(household=7, csv_path=small_csv)


def test_real_data_august_2026():
    # Moderate-cost plan, Aug 2026: female $77.60, male $91.90 -> $4.036 a meal; alone x1.2.
    # Northeast factor: geometric mean of the 9 BLS items with both prices, about 1.063.
    g = regional_factor()
    assert len(northeast_ratios()) == 9
    assert g == pytest.approx(math.exp(sum(map(math.log, northeast_ratios().values())) / 9))
    assert 1.05 < g < 1.08
    assert cooking_cost_per_meal() == pytest.approx((77.60 + 91.90) / 2 / 21 * 1.2 * g)
    assert cooking_cost_per_meal() == pytest.approx(5.15, abs=0.01)
    r = cooking_range()
    assert r["Thrifty"] == pytest.approx(4.01, abs=0.01) and r["Liberal"] == pytest.approx(6.42, abs=0.01)
    assert cooking_cost_per_meal(household=4) == pytest.approx(4.29, abs=0.01)
