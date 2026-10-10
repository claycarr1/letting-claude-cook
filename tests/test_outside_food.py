"""Hand-worked checks for the current model (src/outside_food.py): no guest meals; every meal not
eaten at HUDS is eaten out or cooked at an outside price. Real 2026-27 calendar: 213/7 = 30.43
weeks of dining, so 21 meals a week = 639 meals a year. 2 weekends away per term = 4 away weeks a
year, each missing 6 weekend meals at HUDS (2 breakfasts, 2 brunches, 2 dinners)."""

import pytest

from model import WeeklyPattern, cost_non_resident, cost_outside, flat_prices
from outside_food import cheapest, hud_meals_per_year, per_semester, year_food_spending
from test_model import PRICES


def test_cost_outside():
    # 10 meals a week for 15 weeks at $12 = 1800.
    assert cost_outside(WeeklyPattern(lunch=5, dinner=5), 15, 12).total_cost == pytest.approx(1800)
    assert flat_prices(9) == {"breakfast": 9, "lunch": 9, "brunch": 9, "dinner": 9}
    with pytest.raises(ValueError):
        flat_prices(-1)


def test_swipe_plan_overflow_at_outside_price():
    # 5-meal plan, 7 dinners + 3 lunches a week for 15 weeks: 5 meals a week beyond the swipes,
    # eaten out at $15 -> 5 x 15 x 15 = 1125; total 1538 + 1125 = 2663.
    r = cost_non_resident(WeeklyPattern(lunch=3, dinner=7), 15, PRICES, 5, outside_prices=flat_prices(15))
    assert r.extra_cash == pytest.approx(1125)
    assert r.total_cost == pytest.approx(2663)


def test_hud_meals_per_year():
    # Missing nothing: 639 meals, less 6 weekend meals in each of 4 away weeks = 615.
    assert hud_meals_per_year(0) == pytest.approx(639 - 24)
    assert hud_meals_per_year(21) == 0


def test_every_meal_at_hud_ten_dollars():
    # No plan: all 639 meals at $10 = 6390.
    # 21-meal plan: 8812, plus the 24 away-weekend meals at $10 = 9052.
    c = year_food_spending(0, 10, PRICES)
    assert c["no_plan"] == pytest.approx(6390)
    assert c["nr21"] == pytest.approx(9052)
    assert cheapest(0, 10, PRICES)[0] == "no_plan"  # $10 meals: cheaper than a $13.79 swipe
    assert per_semester(c)["no_plan"] == pytest.approx(3195)


def test_ten_meal_plan_wins_for_ten_hud_meals_at_25():
    # Missing 11 meals a week -> 10 HUDS meals in a normal week (10/21 of every meal type).
    # Away week: 10/21 x (5 breakfasts + 5 lunches + 0 brunches + 5 dinners) = 50/7 meals.
    # 10-meal plan covers every HUDS meal: home weeks 10 x (213/7 - 4) + away 4 x 50/7 = 292.86 meals.
    # Everything else (639 - 292.86 = 346.14 meals) at $25 = 8653.57; total 6120 + 8653.57 = 14773.57.
    # No plan: 639 x 25 = 15975.
    c = year_food_spending(11, 25, PRICES)
    covered = 10 * (213 / 7 - 4) + 4 * 50 / 7
    assert c["nr10"] == pytest.approx(6120 + (639 - covered) * 25)
    assert c["no_plan"] == pytest.approx(15975)
    assert cheapest(11, 25, PRICES)[0] == "nr10"


def test_plans_never_win_below_their_swipe_cost():
    # A plan only pays off if a meal elsewhere costs more than one of its swipes ($13.79 on the
    # 21-meal plan, about $20 on the 5- and 10-meal plans). Below $13 no plan always wins.
    for missed in range(22):
        assert cheapest(missed, 13, PRICES)[0] == "no_plan"
    # Above $20, the 5- and 10-meal plans start to win for middling HUDS use.
    assert cheapest(15, 30, PRICES)[0] == "nr5"   # 6 HUDS meals a week
    assert cheapest(0, 20, PRICES)[0] == "nr21"   # every meal at HUDS


def test_input_checks():
    with pytest.raises(ValueError):
        year_food_spending(22, 10, PRICES)


MEAL_PRICES = {"breakfast": 4, "lunch": 10, "brunch": 12, "dinner": 8}


def test_meal_type_prices_equal_flat_when_equal():
    flat = year_food_spending(9, 11, PRICES)
    by_type = year_food_spending(9, {m: 11 for m in MEAL_PRICES}, PRICES)
    assert by_type == pytest.approx(flat)


def test_meal_type_prices_by_hand():
    # Nothing at HUDS: no plan pays 213/7 weeks x (7x4 + 5x10 + 2x12 + 7x8 = 158) a week.
    assert year_food_spending(21, MEAL_PRICES, PRICES)["no_plan"] == pytest.approx(213 / 7 * 158)
    # Everything at HUDS on the 21-meal plan: 8812, plus the 4 away weekends' 2 breakfasts,
    # 2 brunches and 2 dinners eaten elsewhere: 4 x (8 + 24 + 16) = 192.
    assert year_food_spending(0, MEAL_PRICES, PRICES)["nr21"] == pytest.approx(8812 + 192)


def test_which_meals_are_skipped_matters_with_meal_type_prices():
    # 5-meal plan, 14 HUDS meals a week: skipping lunches (the $10-12 meals) leaves the plan's
    # swipes on dinners; skipping dinners leaves them on lunches. Same plan, different bills.
    lunches = year_food_spending(7, MEAL_PRICES, PRICES, meals_out_from="lunches_first")["nr5"]
    dinners = year_food_spending(7, MEAL_PRICES, PRICES, meals_out_from="dinners_first")["nr5"]
    assert lunches != pytest.approx(dinners)
    with pytest.raises(ValueError):
        year_food_spending(7, {"lunch": 10}, PRICES)
