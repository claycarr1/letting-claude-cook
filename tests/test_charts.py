"""Hand-worked checks for the numbers behind the supporting charts (src/charts.py).
Real 2026-27 calendar: 213/7 = 30.43 weeks of dining a year."""

import pytest

from charts import (
    _spread_labels,
    assumption_effects,
    cost_per_swipe,
    gap_bin,
    grad_switch_points,
    grad_year_costs,
    habits_for_meals,
    meal_type_savings,
    savings_vs_no_plan,
    yearly_costs,
)
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


# ---------------------------------------------------------------- graduate students

FALL_SHARE = 109 / 213  # fall's share of the year's 213/7 weeks of dining (spending is spread evenly)


def test_grad_costs_at_zero_spending():
    assert grad_year_costs(0, PRICES) == pytest.approx({"cash_cafe": 0, "gp_regular": 900, "gp_deluxe": 1350})


def test_grad_switch_points_by_hand():
    # Regular: fall's $400 buys 400/0.9 = 444.44 of food. Above S = 444.44/FALL_SHARE = 868.5 a year,
    # the rest of fall is paid in full, while spring's $500 isn't used up until S = 555.56/(1-FALL_SHARE)
    # = 1137.6. In between, Regular costs 400 + (FALL_SHARE x S - 444.44) + 500 = 455.56 + FALL_SHARE x S,
    # which equals paying cash (S) at S = 455.56 / (1 - FALL_SHARE) = 932.97.
    # Above 1137.6 Regular covers all 1,000 of food at 10% off, so it costs S - 100.
    # Deluxe: fall's 600 buys 666.67, spring's 750 buys 833.33. Between S = 1302.9 and 1706.6 it costs
    # 600 + (FALL_SHARE x S - 666.67) + 750 = 683.33 + FALL_SHARE x S, which equals S - 100 at
    # S = 783.33 / (1 - FALL_SHARE) = 1604.2.
    points = grad_switch_points(PRICES)
    assert [(b, a) for _, b, a in points] == [("cash_cafe", "gp_regular"), ("gp_regular", "gp_deluxe")]
    assert points[0][0] == pytest.approx((400 + 500 - 400 / 0.9) / (1 - FALL_SHARE), abs=0.05)
    assert points[1][0] == pytest.approx((600 + 750 - 600 / 0.9 + 100) / (1 - FALL_SHARE), abs=0.05)
    for s, below, above in points:
        c = grad_year_costs(s, PRICES)
        assert c[below] == pytest.approx(c[above], abs=0.05)


def test_grad_costs_do_not_depend_on_cafe_price():
    # Spending is converted to meals at the estimated cafe price and back, so the price cancels:
    # at S = 2000 both plans are fully used, Regular = 2000 - 100, Deluxe = 2000 - 150.
    assert grad_year_costs(2000, PRICES) == pytest.approx({"cash_cafe": 2000, "gp_regular": 1900, "gp_deluxe": 1850})


# ---------------------------------------------------------------- which meals you skip

def test_meal_type_savings():
    # Every meal, 2 weekends away (test above): no plan 10155.70. 5-meal plan: home weeks pay cash for
    # 2 dinners + 5 lunches + 2 brunches + 7 breakfasts = 239.78 x 185/7 = 6337.04; away weeks for
    # 5 lunches + 5 breakfasts = 140.70 x 4 = 562.80; total 3076 + 6899.84 = 9975.84. Saving 179.86.
    for kind in ("breakfasts", "lunches", "dinners"):
        assert meal_type_savings(0, kind, PRICES) == pytest.approx(179.86, abs=0.02)
    # Skipping breakfasts or lunches: those meals were paid in cash under both options, so the saving
    # doesn't move.
    for x in (1, 3.5, 7):
        assert meal_type_savings(x, "breakfasts", PRICES) == pytest.approx(179.86, abs=0.02)
        assert meal_type_savings(x, "lunches", PRICES) == pytest.approx(179.86, abs=0.02)
    # Skipping all 7 dinners: the swipes go on 5 lunches instead.
    #   Home week: 5-meal plan cash for 2 brunches + 7 breakfasts = 110.48; no plan 75.88 + 86.50 + 34.60 = 196.98.
    #   Away week: 5-meal plan cash for 5 breakfasts = 54.20; no plan 54.20 + 86.50 = 140.70.
    #   5-meal plan 3076 + 110.48 x 185/7 + 54.20 x 4 = 6212.63; no plan 196.98 x 185/7 + 140.70 x 4 = 5768.70.
    assert meal_type_savings(7, "dinners", PRICES) == pytest.approx(5768.70 - 6212.63, abs=0.05)
    with pytest.raises(ValueError):
        meal_type_savings(8, "dinners", PRICES)


def test_spread_labels_keeps_groups_centred():
    # Two labels at the same height move apart by min_gap, centred on where they were.
    assert _spread_labels([10, 10, 100], 6) == pytest.approx([7, 13, 100])
    assert _spread_labels([0, 50], 6) == [0, 50]
