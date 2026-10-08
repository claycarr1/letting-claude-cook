"""Hand-worked checks for the numbers behind the supporting charts (src/charts.py).
Real 2026-27 calendar: 213/7 = 30.43 weeks of dining a year."""

import pytest

from charts import assumption_effects, cost_per_swipe, gap_bin, habits_for_meals, savings_vs_no_plan, yearly_costs
from test_model import PRICES

WEEKS = 213 / 7


def test_habits_for_meals():
    assert habits_for_meals(21) == (0, 0)
    assert habits_for_meals(0) == (14, 7)
    assert habits_for_meals(10.5) == pytest.approx((7, 3.5))  # half of every meal type
    with pytest.raises(ValueError):
        habits_for_meals(22)


def test_yearly_costs_every_meal_two_weekends_away():
    # 21-meal plan: 2 x 4406 = 8812 whatever is eaten.
    # Paying as you go: home week 346.78 for 185/7 weeks = 9164.90; away week (5 breakfasts,
    # 5 lunches, 5 dinners) = 54.20 + 86.50 + 107.00 = 247.70 for 4 weeks = 990.80; total 10155.70.
    c = yearly_costs(21, PRICES)
    assert c["nr21"] == 8812
    assert c["cash_guest"] == pytest.approx(10155.70, abs=0.02)


def test_savings_vs_no_plan():
    # Eating nothing at HUDS, each plan "saves" minus its whole yearly price.
    s0 = savings_vs_no_plan(0, PRICES)
    assert s0 == pytest.approx({"nr5": -3076, "nr10": -6120, "nr21": -8812})
    # Eating everything (2 weekends away): no plan costs 10155.70 (test above), so the 21-meal
    # plan saves 10155.70 - 8812 = 1343.70.
    assert savings_vs_no_plan(21, PRICES)["nr21"] == pytest.approx(1343.70, abs=0.02)
    # The 5-meal plan starts saving money at about 11.1 meals a week.
    assert savings_vs_no_plan(11.0, PRICES)["nr5"] < 0 < savings_vs_no_plan(11.2, PRICES)["nr5"]
    # The 10-meal plan never saves money, at any number of meals.
    assert all(savings_vs_no_plan(x / 2, PRICES)["nr10"] < 0 for x in range(43))


def test_cost_per_swipe():
    # Yearly price / (swipes a week x 30.43 weeks):
    # 5-meal: 3076 / 152.14 = 20.218; 10-meal: 6120 / 304.29 = 20.113; 21-meal: 8812 / 639 = 13.790
    s = cost_per_swipe(PRICES)
    assert s[5] == pytest.approx(3076 / (5 * WEEKS))
    assert s[5] == pytest.approx(20.218, abs=0.001)
    assert s[10] == pytest.approx(20.113, abs=0.001)
    assert s[21] == pytest.approx(13.790, abs=0.001)
    # Only a dinner costs more than a 5- or 10-meal swipe; a 21-meal swipe beats lunch and dinner.
    assert PRICES.guest_rates["lunch"] < s[10] < s[5] < PRICES.guest_rates["dinner"]
    assert PRICES.guest_rates["breakfast_annenberg_quincy"] < s[21] < PRICES.guest_rates["lunch"]


def test_gap_bins():
    assert [gap_bin(g) for g in (0, 49.99, 50, 150, 300, 600, 1199.99, 1200, 3076)] == [0, 0, 1, 2, 3, 4, 4, 5, 5]
    with pytest.raises(ValueError):
        gap_bin(-1)


def test_assumption_effects():
    effects = assumption_effects({
        "breakfast price": {"annenberg_quincy": 0.90, "houses": 0.91},
        "meals out taken from": {"dinners_first": 0.80, "spread": 0.95},
    })
    assert [e["assumption"] for e in effects] == ["Which meals are eaten elsewhere", "House or Annenberg breakfast price"]
    assert effects[0]["effect_pp"] == pytest.approx(15)  # 20% of squares differ vs 5%
    assert effects[0]["high"][0] == "dinners_first" and effects[0]["low"][0] == "spread"
    assert effects[1]["effect_pp"] == pytest.approx(1)
