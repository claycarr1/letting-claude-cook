"""Restaurant meal prices near Harvard Square and Central Square, from the hand-collected sample in
data/hand_collected/restaurant_meals.csv (README in that folder).

Out-the-door price = menu price x (1 + 7% Cambridge meals tax + 18% tip for sit-down meals).
The tip is figured on the pre-tax menu price, so a sit-down meal costs 1.25 x the menu price and
a counter meal 1.07 x. Averages are plain means over the meals in each group.

price_source "news article" (one row: Daily Provisions, from an Aug 2025 Boston Globe article)
is accepted but is second-hand and older than the other rows; `exclude_sources` lets a caller
drop it to check how much it matters.
"""

import csv
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "hand_collected" / "restaurant_meals.csv"
MEALS_TAX = 0.07
SIT_DOWN_TIP = 0.18
SERVICES = ("counter", "sit-down")
MEAL_TYPES = ("breakfast", "lunch", "dinner")
PRICE_SOURCES = ("in person", "restaurant website", "menu photo", "news article")
RESTAURANT_TYPES = ("coffee chain", "café", "bakery-café", "Mexican", "burgers", "pizza", "salad/bowls", "Mediterranean",
                    "Greek", "Vietnamese", "grilled cheese", "healthy bowls", "diner", "pub", "tavern", "New American",
                    "Italian")


def out_the_door(menu_price: float, service: str) -> float:
    if service not in SERVICES:
        raise ValueError(f"service must be one of {SERVICES}, got {service!r}")
    if menu_price < 0:
        raise ValueError(f"negative menu price {menu_price}")
    return menu_price * (1 + MEALS_TAX + (SIT_DOWN_TIP if service == "sit-down" else 0.0))


def load_meals(csv_path: Path = DEFAULT_CSV, exclude_sources: Iterable[str] = ()) -> List[dict]:
    """Every priced row, checked, with an added "price" (out the door). Blank prices are skipped."""
    exclude = set(exclude_sources)
    out = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            if not r["menu_price"].strip():
                continue
            for col, allowed in (("service", SERVICES), ("meal_type", MEAL_TYPES), ("price_source", PRICE_SOURCES)):
                if r[col] not in allowed:
                    raise ValueError(f"{csv_path.name} line {n}: {col} {r[col]!r} not in {allowed}")
            if "type" in r and r["type"] not in RESTAURANT_TYPES:
                raise ValueError(f"{csv_path.name} line {n}: type {r['type']!r} not in {RESTAURANT_TYPES}")
            if r["price_source"] in exclude:
                continue
            out.append({**r, "price": out_the_door(float(r["menu_price"]), r["service"])})
    return out


def _summary(prices: List[float]) -> Dict[str, float]:
    return {"n": len(prices), "mean": statistics.mean(prices), "median": statistics.median(prices),
            "min": min(prices), "max": max(prices)}


def averages(meals: Optional[List[dict]] = None, by: str = "service") -> Dict[str, Dict[str, float]]:
    """{group: {n, mean, median, min, max}} of out-the-door prices, grouped by a column
    ("service" or "meal_type")."""
    meals = load_meals() if meals is None else meals
    groups: Dict[str, List[float]] = {}
    for m in meals:
        groups.setdefault(m[by], []).append(m["price"])
    order = SERVICES if by == "service" else MEAL_TYPES
    return {g: _summary(groups[g]) for g in order if g in groups}


def average_price(service: str, meals: Optional[List[dict]] = None) -> float:
    """Mean out-the-door price of the sample's counter or sit-down meals."""
    return averages(meals, "service")[service]["mean"]


def summary_rows(meals: Optional[List[dict]] = None) -> List[dict]:
    """Out-the-door price summaries for the report: every meal, by service, by meal type, by meal
    type and service, and counter/sit-down without the news-article row."""
    meals = load_meals() if meals is None else meals
    groups = [("all meals", meals)]
    groups += [(s, [m for m in meals if m["service"] == s]) for s in SERVICES]
    groups += [(t, [m for m in meals if m["meal_type"] == t]) for t in MEAL_TYPES]
    groups += [(f"{t}, {s}", [m for m in meals if m["meal_type"] == t and m["service"] == s])
               for t in MEAL_TYPES for s in SERVICES]
    groups += [(f"{s}, without news-article rows", [m for m in meals if m["service"] == s
                                                     and m["price_source"] != "news article"]) for s in SERVICES]
    return [{"group": g, **{k: round(v, 2) for k, v in _summary([m["price"] for m in ms]).items()}}
            for g, ms in groups if ms]


def log_table(service: str, meals: Optional[List[dict]] = None) -> str:
    """Markdown table of every meal with this service, cheapest first (ties by restaurant name):
    restaurant, type, meal, item, menu price and out-the-door price."""
    meals = load_meals() if meals is None else meals
    real = "with tax and 18% tip" if service == "sit-down" else "with tax"
    lines = [f"| # | Restaurant | Type | Meal | Item | Menu price | Real price ({real}) |",
             "|---|---|---|---|---|---|---|"]
    rows = sorted((m for m in meals if m["service"] == service), key=lambda m: (m["price"], m["restaurant"]))
    for i, m in enumerate(rows, start=1):
        lines.append(f"| {i} | {m['restaurant']} | {m.get('type', '')} | {m['meal_type']} | {m['item']} | "
                     f"${float(m['menu_price']):.2f} | ${m['price']:.2f} |")
    return "\n".join(lines)
