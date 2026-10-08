"""Step 2: deterministic cost model for Harvard dining plans.

Every function here is pure: it takes a Prices object, a weekly eating pattern and a
term length, and returns a TermCost. Prices are read from data/huds_prices.csv by
load_prices(). The only hardcoded dollar amount is CAFE_MEAL_PRICE_ESTIMATE, a marked
placeholder for GradPlus cafe meals until real cafe prices are collected.
For every plan, total_cost = plan_charge + extra_cash - credits (GradPlus also adjusts
for carry_in/carry_out; see below).

Modelling assumptions (each needs to go in report.md):

* A weekly pattern counts meals eaten at HUDS per week, by meal period. HUDS serves at
  most 7 breakfasts, 5 lunches (Mon-Fri), 2 brunches (Sat-Sun) and 7 dinners a week
  (21 periods, matching the guest-rate schedule and the 21-meal plan). Counts may be
  fractional averages.
* Meals a plan doesn't cover are eaten out or cooked at an "outside price" per meal
  (outside_prices=, e.g. flat_prices(12.0)); "no plan" is cost_outside(). A student without
  a plan can't buy HUDS guest meals (see CLAUDE.md), so guest rates are a reference only.
  For comparison with the archived guest-rate model, the swipe-plan functions still default
  to guest rates (incl. 7% meals tax; breakfast at the House rate unless
  breakfast_venue="annenberg_quincy") when no outside price is given.
* Resident unlimited: the annual board fee is split evenly across two terms, minus the
  BoardPlus dollars loaded each semester (treated as fully spent, i.e. worth face value).
* Non-resident 5/10/21: the plan price is paid per term. Each week the student uses up
  to N swipes, on their most expensive meals first; unused swipes are forfeited that
  week. Meals beyond N in a week are paid at guest rates.
* GradPlus: the term's balance is paid up front. Meals bought from the balance get the
  plan discount; once the balance runs out, the rest is paid at full price. Unspent fall
  balance rolls over to spring (carry_out); unspent spring balance is forfeited. A
  term's cost is plan charge + carry_in - carry_out + extra cash, so fall + spring sums
  to the cash actually paid over the year. GradPlus is spent at HUDS cafes, so every
  meal is priced at cafe_meal_price. Its default, CAFE_MEAL_PRICE_ESTIMATE, is a
  placeholder ESTIMATE, not a collected price; results using it say so in TermCost.notes.
* No plan: every meal at the outside price (cost_outside). cost_no_plan() is the old
  guest-rate baseline, kept only for the archived comparison.
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "huds_prices.csv"
MEAL_TYPES = ("breakfast", "lunch", "brunch", "dinner")
MAX_PER_WEEK = {"breakfast": 7, "lunch": 5, "brunch": 2, "dinner": 7}
NON_RESIDENT_TIERS = (5, 10, 21)
TERMS = ("fall", "spring")
GRADPLUS_TIERS = ("regular", "deluxe")

# ESTIMATE -- the one price in this module not read from data/huds_prices.csv.
# Placeholder until real HUDS cafe prices are collected (HUDS describes GradPlus meals as
# "$10-15"). Replace with collected data, then drop the estimate note in cost_gradplus.
CAFE_MEAL_PRICE_ESTIMATE = 12.50
CAFE_ESTIMATE_NOTE = f"cafe_meal_price ${CAFE_MEAL_PRICE_ESTIMATE:.2f} is a placeholder ESTIMATE, not a collected price"


@dataclass(frozen=True)
class WeeklyPattern:
    """Meals eaten at HUDS per week, by meal period."""

    breakfast: float = 0
    lunch: float = 0
    brunch: float = 0
    dinner: float = 0

    def __post_init__(self):
        for meal in MEAL_TYPES:
            n = getattr(self, meal)
            if not 0 <= n <= MAX_PER_WEEK[meal]:
                raise ValueError(f"{meal}={n} per week is outside 0..{MAX_PER_WEEK[meal]}")

    def counts(self) -> Dict[str, float]:
        return {meal: getattr(self, meal) for meal in MEAL_TYPES}

    @property
    def total(self) -> float:
        return sum(self.counts().values())


@dataclass(frozen=True)
class Prices:
    """All prices the model needs, as read from data/huds_prices.csv."""

    resident_board_fee_per_year: float
    boardplus_per_semester: float
    guest_rates: Dict[str, float]  # incl. tax; keys: breakfast_houses, breakfast_annenberg_quincy, lunch, brunch, dinner
    non_resident_per_term: Dict[int, float]  # meals/week tier -> USD per term
    gradplus_per_term: Dict[str, Dict[str, float]]  # tier -> term -> USD balance
    gradplus_discount: float  # fraction, e.g. 0.10

    def meal_prices(self, breakfast_venue: str = "houses") -> Dict[str, float]:
        return {
            "breakfast": self.guest_rates[f"breakfast_{breakfast_venue}"],
            "lunch": self.guest_rates["lunch"],
            "brunch": self.guest_rates["brunch"],
            "dinner": self.guest_rates["dinner"],
        }


@dataclass(frozen=True)
class TermCost:
    plan: str
    meals_eaten: float
    plan_charge: float  # what the plan itself costs this term
    extra_cash: float  # meals paid for outside the plan
    total_cost: float
    cost_per_meal: Optional[float]  # None when no meals are eaten
    credits: float = 0  # value returned with the plan (resident BoardPlus)
    unused: float = 0  # forfeited swipes (non-resident) or forfeited dollars (GradPlus)
    carry_out: float = 0  # GradPlus fall balance rolling into spring
    notes: str = ""  # caveats, e.g. estimated prices
    details: Dict[str, float] = field(default_factory=dict)


def _result(plan, meals, plan_charge, extra_cash, total, **kw) -> TermCost:
    return TermCost(plan=plan, meals_eaten=meals, plan_charge=plan_charge, extra_cash=extra_cash,
                    total_cost=total, cost_per_meal=(total / meals) if meals else None, **kw)


def _check_weeks(weeks: float):
    if weeks <= 0:
        raise ValueError(f"weeks must be positive, got {weeks}")


def _list_price_per_week(pattern: WeeklyPattern, meal_prices: Dict[str, float]) -> float:
    return sum(n * meal_prices[meal] for meal, n in pattern.counts().items())


# ---------------------------------------------------------------------------- plans


def flat_prices(price: float) -> Dict[str, float]:
    """The same outside price for every meal type."""
    if price < 0:
        raise ValueError(f"price must be non-negative, got {price}")
    return {m: float(price) for m in MEAL_TYPES}


def cost_outside(pattern: WeeklyPattern, weeks: float, outside_price: float) -> TermCost:
    """No plan: every meal in the pattern is eaten out or cooked at `outside_price` per meal."""
    _check_weeks(weeks)
    total = _list_price_per_week(pattern, flat_prices(outside_price)) * weeks
    return _result("no plan (eat out or cook)", pattern.total * weeks, 0.0, total, total)


def cost_no_plan(pattern: WeeklyPattern, weeks: float, prices: Prices,
                 breakfast_venue: str = "houses") -> TermCost:
    """Old baseline (reference only): pay the HUDS guest rate for every meal."""
    _check_weeks(weeks)
    total = _list_price_per_week(pattern, prices.meal_prices(breakfast_venue)) * weeks
    return _result("no plan (guest rates)", pattern.total * weeks, 0.0, total, total)


def cost_cash_at_cafe(pattern: WeeklyPattern, weeks: float, cafe_meal_price: Optional[float] = None) -> TermCost:
    """Grad baseline: pay cash at a HUDS cafe for every meal (no plan, no discount)."""
    _check_weeks(weeks)
    notes = ""
    if cafe_meal_price is None:
        cafe_meal_price, notes = CAFE_MEAL_PRICE_ESTIMATE, CAFE_ESTIMATE_NOTE
    total = pattern.total * cafe_meal_price * weeks
    return _result("no plan (cash at cafe)", pattern.total * weeks, 0.0, total, total, notes=notes)


def cost_resident_unlimited(pattern: WeeklyPattern, weeks: float, prices: Prices,
                            count_boardplus: bool = True) -> TermCost:
    """Mandatory unlimited plan: half the annual board fee per term, less that term's BoardPlus.

    count_boardplus=False treats BoardPlus as worth nothing (a student who never spends it).
    """
    _check_weeks(weeks)
    charge = prices.resident_board_fee_per_year / 2
    credit = prices.boardplus_per_semester if count_boardplus else 0.0
    return _result("resident unlimited", pattern.total * weeks, charge, 0.0, charge - credit, credits=credit)


def _swipe_week(counts: Dict[str, float], swipes: float, meal_prices: Dict[str, float]):
    """One week on a swipe plan: (cash paid for meals beyond the swipes, swipes left unused).

    Swipes go to the most expensive meals first; whatever is left over is paid in cash.
    """
    swipes_left = swipes
    overflow = 0.0
    for meal in sorted(MEAL_TYPES, key=lambda m: meal_prices[m], reverse=True):
        covered = min(counts[meal], swipes_left)
        swipes_left -= covered
        overflow += (counts[meal] - covered) * meal_prices[meal]
    return overflow, swipes_left


def cost_non_resident(pattern: WeeklyPattern, weeks: float, prices: Prices, meals_per_week: int,
                      breakfast_venue: str = "houses", first_week_fraction: float = 0.0,
                      full_first_week_swipes: bool = False,
                      outside_prices: Optional[Dict[str, float]] = None) -> TermCost:
    """Non-resident N-meals/week plan with weekly forfeiture.

    Meals beyond the week's swipes are eaten out or cooked at `outside_prices` (per meal type).
    If outside_prices is None they are priced at HUDS guest rates instead -- the archived
    guest-rate model, kept for comparison.

    weeks may include a short first week (first_week_fraction of a week, e.g. 4/7 for a term
    starting on a Wednesday). By default it gets the same fraction of the weekly swipes, which
    is the same as treating all weeks alike. With full_first_week_swipes=True it gets the
    whole weekly allowance instead, with only that fraction of the week's meals to spend it on.
    """
    _check_weeks(weeks)
    if meals_per_week not in prices.non_resident_per_term:
        raise ValueError(f"no non-resident plan with {meals_per_week} meals/week")
    if not 0 <= first_week_fraction < 1 or first_week_fraction > weeks:
        raise ValueError(f"first_week_fraction must be in [0, 1) and within the term, got {first_week_fraction}")
    meal_prices = outside_prices if outside_prices is not None else prices.meal_prices(breakfast_venue)

    overflow_per_week, left_per_week = _swipe_week(pattern.counts(), meals_per_week, meal_prices)
    if full_first_week_swipes and first_week_fraction:
        short_counts = {m: n * first_week_fraction for m, n in pattern.counts().items()}
        short_overflow, short_left = _swipe_week(short_counts, meals_per_week, meal_prices)
        full_weeks = weeks - first_week_fraction
        extra = overflow_per_week * full_weeks + short_overflow
        unused = left_per_week * full_weeks + short_left
    else:
        extra = overflow_per_week * weeks
        unused = left_per_week * weeks

    charge = prices.non_resident_per_term[meals_per_week]
    return _result(f"non-resident {meals_per_week}/week", pattern.total * weeks, charge, extra, charge + extra,
                   unused=unused,
                   details={"swipes_used_per_week": meals_per_week - left_per_week,
                            "swipes_forfeited_per_week": left_per_week})


def cost_gradplus(pattern: WeeklyPattern, weeks: float, prices: Prices, tier: str, term: str,
                  carry_in: float = 0.0, cafe_meal_price: Optional[float] = None) -> TermCost:
    """GradPlus declining balance with discount, fall-to-spring rollover and year-end forfeiture.

    carry_in is the unspent fall balance (pass the fall result's carry_out into spring).
    cafe_meal_price is the list price of one cafe meal, applied to every meal type. If
    omitted, CAFE_MEAL_PRICE_ESTIMATE is used and the result's notes flag it as an estimate.
    """
    _check_weeks(weeks)
    if tier not in GRADPLUS_TIERS or term not in TERMS:
        raise ValueError(f"tier must be one of {GRADPLUS_TIERS} and term one of {TERMS}")
    if term == "fall" and carry_in:
        raise ValueError("carry_in only applies to spring")
    notes = ""
    if cafe_meal_price is None:
        cafe_meal_price, notes = CAFE_MEAL_PRICE_ESTIMATE, CAFE_ESTIMATE_NOTE
    if cafe_meal_price < 0:
        raise ValueError(f"cafe_meal_price must be non-negative, got {cafe_meal_price}")

    charge = prices.gradplus_per_term[tier][term]
    balance = charge + carry_in
    list_total = pattern.total * cafe_meal_price * weeks
    discounted_total = list_total * (1 - prices.gradplus_discount)

    if discounted_total <= balance:
        spent, extra = discounted_total, 0.0
    else:
        # The balance buys balance / (1 - d) dollars of food at list price; the rest is paid in full.
        spent = balance
        extra = list_total - balance / (1 - prices.gradplus_discount)
    leftover = balance - spent
    carry_out = leftover if term == "fall" else 0.0
    forfeited = leftover if term == "spring" else 0.0

    total = charge + carry_in - carry_out + extra
    return _result(f"GradPlus {tier} ({term})", pattern.total * weeks, charge, extra, total,
                   unused=forfeited, carry_out=carry_out, notes=notes,
                   details={"balance_available": balance, "balance_spent": spent, "list_price_of_meals": list_total,
                            "cafe_meal_price": cafe_meal_price})


# ---------------------------------------------------------------------------- price loading


def load_prices(csv_path: Path = DEFAULT_CSV, year: str = "2026-27") -> Prices:
    """Read every price the model needs from the step-1 CSV. Raises if any is missing."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = {r["item"]: r["value"] for r in csv.DictReader(f)}
    fy = "FY" + year[2:4] + "-" + year[-2:]  # "2026-27" -> "FY26-27"

    def get(item: str) -> float:
        if not rows.get(item):
            raise KeyError(f"{csv_path} has no value for {item!r}")
        return float(rows[item])

    guest: Dict[str, float] = {}
    pattern = re.compile(rf"Guest meal {re.escape(year)}: (Breakfast|Brunch|Lunch|Dinner) \((.+)\), incl\. tax")
    for item in rows:
        m = pattern.fullmatch(item)
        if not m:
            continue
        meal, when = m.group(1).lower(), m.group(2)
        if meal == "breakfast":
            meal = "breakfast_annenberg_quincy" if "Annenberg & Quincy" in when else "breakfast_houses"
        guest[meal] = get(item)
    expected = {"breakfast_houses", "breakfast_annenberg_quincy", "lunch", "brunch", "dinner"}
    if set(guest) != expected:
        raise KeyError(f"guest rates for {year}: found {sorted(guest)}, expected {sorted(expected)}")

    return Prices(
        resident_board_fee_per_year=get(f"Harvard College {year} cost of attendance: Board fee (listed as 'Food')"),
        boardplus_per_semester=get("Resident plan: BoardPlus per semester"),
        guest_rates=guest,
        non_resident_per_term={n: get(f"Non-resident {n} meals/week plan {fy}") for n in NON_RESIDENT_TIERS},
        gradplus_per_term={
            tier: {
                "fall": get(f"GradPlus {tier.title()} {year}: fall 20{year[2:4]} semester amount"),
                "spring": get(f"GradPlus {tier.title()} {year}: spring 20{year[-2:]} semester amount"),
            }
            for tier in GRADPLUS_TIERS
        },
        gradplus_discount=get("GradPlus: discount on purchases made with the plan") / 100,
    )


# ---------------------------------------------------------------------------- term calendar

# Dining halls close for spring break (HUDS FAQ: "dining hall closures such as spring break"),
# but the saved pages don't give its dates, so one whole week is taken off spring.
SPRING_BREAK_WEEKS = 1
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _parse_term(text: str, start_year: int, end_year: int):
    """'Sept 2 - Dec 19' -> (date, date)."""
    m = re.fullmatch(r"\s*([A-Za-z]+)\.? (\d+)\s*-\s*([A-Za-z]+)\.? (\d+)\s*", text)
    if not m:
        raise ValueError(f"can't parse term dates {text!r}")
    first = date(start_year, _MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
    last = date(end_year, _MONTHS[m.group(3)[:3].lower()], int(m.group(4)))
    return first, last


@lru_cache(maxsize=None)
def load_term_weeks(csv_path: Path = DEFAULT_CSV, year: str = "2026-27") -> Dict[str, float]:
    """Weeks of dining per term, from the non-resident term dates in the CSV.

    Each term counts every day from its first to its last day inclusive, divided by 7, so a
    short first week counts as a fraction of a week (fall starts on a Wednesday: 4/7). Spring
    then loses SPRING_BREAK_WEEKS. Returns e.g. {"fall": 15.571, "spring": 14.857}.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = {r["item"]: r["value"] for r in csv.DictReader(f)}
    fy = "FY" + year[2:4] + "-" + year[-2:]
    y0, y1 = 2000 + int(year[2:4]), 2000 + int(year[-2:])
    weeks = {}
    for term, (a, b) in {"fall": (y0, y0), "spring": (y1, y1)}.items():
        first, last = _parse_term(rows[f"Non-resident plans {fy}: {term} term dates"], a, b)
        weeks[term] = ((last - first).days + 1) / 7
    weeks["spring"] -= SPRING_BREAK_WEEKS
    return weeks


@lru_cache(maxsize=None)
def load_first_week_fractions(csv_path: Path = DEFAULT_CSV, year: str = "2026-27") -> Dict[str, float]:
    """Length of each term's short first week, as a fraction of a week.

    Swipes reset after Saturday dinner, so the first week runs from the first day of term to
    the first Saturday. Fall 2026 starts on a Wednesday (4/7), spring 2027 on a Monday (6/7).
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = {r["item"]: r["value"] for r in csv.DictReader(f)}
    fy = "FY" + year[2:4] + "-" + year[-2:]
    y0, y1 = 2000 + int(year[2:4]), 2000 + int(year[-2:])
    fractions = {}
    for term, y in {"fall": y0, "spring": y1}.items():
        first, _ = _parse_term(rows[f"Non-resident plans {fy}: {term} term dates"], y, y)
        days_to_saturday = (5 - first.weekday()) % 7 + 1  # weekday(): Monday=0 ... Saturday=5
        fractions[term] = (days_to_saturday % 7) / 7  # a term starting on a Sunday has no short week
    return fractions
