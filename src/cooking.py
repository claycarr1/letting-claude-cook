"""Cooking cost per meal, from data/cooking_cost.csv (scripts/fetch_cooking_cost.py).

cost per meal = USDA weekly food-plan cost (average of the female and male adult groups)
                / 21 meals a week
                x household-size factor (USDA's suggested adjustment)
                x Northeast/U.S. price ratio (BLS average prices)

- USDA plans are U.S.-average costs for individuals in 4-person households, all meals and
  snacks prepared at home. USDA suggests adding 20% for a 1-person household and 10% for a
  2-person one. Default: a student cooking alone (+20%); roommates sharing (4-person, no
  adjustment) is the lower case.
- BLS doesn't publish food price levels for Boston (its Boston CPI measures change over time,
  not price levels), so the regional adjustment is the Northeast/U.S. ratio of BLS average
  prices: the geometric mean over every item BLS reports for both areas in the same month.
- Groceries only: no cook's time, kitchen equipment or wasted food.
"""

import csv
import math
import re
from pathlib import Path
from typing import Dict, Optional

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "cooking_cost.csv"
MEALS_PER_WEEK = 21
PLANS = ("Thrifty", "Low-Cost", "Moderate-Cost", "Liberal")
DEFAULT_PLAN = "Moderate-Cost"
HOUSEHOLD_FACTOR = {1: 1.20, 2: 1.10, 3: 1.05, 4: 1.00}  # USDA's suggested adjustments
DEFAULT_HOUSEHOLD = 1  # cooking alone
ROOMMATES_HOUSEHOLD = 4  # the lower case in report.md


def _rows(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def usda_weekly(csv_path: Path = DEFAULT_CSV) -> Dict[str, Dict[str, float]]:
    """{plan: {"female": weekly, "male": weekly}} for the adult age groups."""
    out: Dict[str, Dict[str, float]] = {}
    for r in _rows(csv_path):
        m = re.match(r"USDA (\S+) food plan: (female|male) \S+, .*, weekly$", r["item"])
        if m:
            out.setdefault(m.group(1), {})[m.group(2)] = float(r["value"])
    missing = [p for p in PLANS if set(out.get(p, {})) != {"female", "male"}]
    if missing:
        raise ValueError(f"{csv_path}: missing USDA weekly costs for {missing}")
    return out


def northeast_ratios(csv_path: Path = DEFAULT_CSV) -> Dict[str, float]:
    """{item: Northeast price / U.S. city average price} for every item with both."""
    prices: Dict[str, Dict[str, float]] = {}
    for r in _rows(csv_path):
        m = re.match(r"BLS average price, (U\.S\. city average|Northeast): (.*), (\d{4}-\d{2})$", r["item"])
        if m:
            area = "us" if m.group(1).startswith("U.S.") else "ne"
            prices.setdefault(m.group(2), {})[area] = float(r["value"])
    ratios = {item: p["ne"] / p["us"] for item, p in prices.items() if {"us", "ne"} <= set(p)}
    if not ratios:
        raise ValueError(f"{csv_path}: no BLS items with both U.S. and Northeast prices")
    return ratios


def regional_factor(csv_path: Path = DEFAULT_CSV) -> float:
    """Geometric mean of the Northeast/U.S. price ratios."""
    r = list(northeast_ratios(csv_path).values())
    return math.exp(sum(math.log(x) for x in r) / len(r))


def cooking_cost_per_meal(plan: str = DEFAULT_PLAN, household: int = DEFAULT_HOUSEHOLD,
                          regional: Optional[float] = None, csv_path: Path = DEFAULT_CSV) -> float:
    if plan not in PLANS:
        raise ValueError(f"plan must be one of {PLANS}")
    if household not in HOUSEHOLD_FACTOR:
        raise ValueError(f"household must be one of {sorted(HOUSEHOLD_FACTOR)}")
    weekly = usda_weekly(csv_path)[plan]
    regional = regional_factor(csv_path) if regional is None else regional
    return (weekly["female"] + weekly["male"]) / 2 / MEALS_PER_WEEK * HOUSEHOLD_FACTOR[household] * regional


def cooking_range(household: int = DEFAULT_HOUSEHOLD, csv_path: Path = DEFAULT_CSV) -> Dict[str, float]:
    """Cost per meal on every USDA plan, cheapest (Thrifty) to most generous (Liberal)."""
    return {p: cooking_cost_per_meal(p, household, csv_path=csv_path) for p in PLANS}
