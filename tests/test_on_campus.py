"""Hand-worked checks for src/on_campus.py on the real 2026-27 calendar.

Weeks of dining: fall 109/7 + spring (111/7 - 1) = 213/7 = 30.43 weeks.
Year cost: 2 x 4471 = 8942, less 2 x 65 BoardPlus = 8812.
"""

import pytest

from on_campus import break_even_meals_per_week, resident_cost_per_meal, resident_year
from test_model import PRICES

WEEKS = 213 / 7


def test_every_meal():
    # 21 x 213/7 = 639 meals; 8812 / 639 = 13.7903
    cost, meals = resident_year(21, PRICES)
    assert cost == 8812 and meals == pytest.approx(639)
    assert resident_cost_per_meal(21, PRICES) == pytest.approx(13.7903, abs=1e-4)


def test_boardplus_unspent():
    # 8942 / 639 = 13.9937
    assert resident_cost_per_meal(21, PRICES, count_boardplus=False) == pytest.approx(13.9937, abs=1e-4)


def test_half_the_meals_doubles_cost_per_meal():
    assert resident_cost_per_meal(10.5, PRICES) == pytest.approx(2 * resident_cost_per_meal(21, PRICES))


def test_break_even_against_guest_prices():
    # Dinner: 8812 / (21.40 x 30.43) = 13.53 meals/week; lunch: 8812 / (17.30 x 30.43) = 16.74.
    assert break_even_meals_per_week(21.40, PRICES) == pytest.approx(8812 / (21.40 * WEEKS))
    assert break_even_meals_per_week(21.40, PRICES) == pytest.approx(13.53, abs=0.01)
    assert break_even_meals_per_week(17.30, PRICES) == pytest.approx(16.74, abs=0.01)
    # Breakfast: 27.1 meals/week -- more than the 21 on offer, so never cheaper than a guest breakfast.
    assert break_even_meals_per_week(10.84, PRICES) > 21


def test_no_meals():
    assert resident_cost_per_meal(0, PRICES) is None


def test_out_of_range():
    with pytest.raises(ValueError):
        resident_year(22, PRICES)


# ---------------------------------------------------------------------------- resident plan = 21-meal plan

from decision_map import annual_costs  # noqa: E402
from model import WeeklyPattern, cost_non_resident, cost_resident_unlimited, flat_prices  # noqa: E402

PATTERNS = [WeeklyPattern(breakfast=7, lunch=5, brunch=2, dinner=7), WeeklyPattern(lunch=5, dinner=7),
            WeeklyPattern(breakfast=2.5, lunch=1, brunch=0.5, dinner=3), WeeklyPattern()]


def test_resident_price_equals_21_meal_plan():
    # 8942 / 2 = 4471 a term, less 65 BoardPlus = 4406 = the 21-meal plan's price per term.
    assert PRICES.resident_board_fee_per_year == 8942
    assert PRICES.resident_board_fee_per_year / 2 - PRICES.boardplus_per_semester == pytest.approx(4406)
    assert PRICES.non_resident_per_term[21] == 4406


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("outside", [None, 5.15, 30.0])
@pytest.mark.parametrize("full_first_week", [False, True])
def test_resident_costs_the_same_as_21_meal_plan(pattern, outside, full_first_week):
    # One swipe per meal period and at most 21 meal periods a week, so 21 swipes always cover
    # every HUDS meal: no extra cash, whatever the pattern, outside price or first-week rule.
    nr21 = cost_non_resident(pattern, 15 + 4 / 7, PRICES, 21, first_week_fraction=4 / 7,
                             full_first_week_swipes=full_first_week,
                             outside_prices=flat_prices(outside) if outside is not None else None)
    resident = cost_resident_unlimited(pattern, 15 + 4 / 7, PRICES)
    assert nr21.extra_cash == 0
    assert nr21.total_cost == pytest.approx(resident.total_cost) == pytest.approx(4406)


@pytest.mark.parametrize("meals_out,breakfasts_skipped,weekends_away", [(0, 0, 0), (4, 3, 2), (14, 7, 10), (7, 0, 5)])
def test_resident_equals_21_meal_plan_per_year(meals_out, breakfasts_skipped, weekends_away):
    for outside in (None, 12.0):
        c = annual_costs(meals_out, breakfasts_skipped, weekends_away, PRICES, ["resident", "nr21"],
                         outside_price=outside)
        assert c["resident"] == pytest.approx(c["nr21"]) == pytest.approx(8812)


def test_resident_with_boardplus_unspent_costs_130_more():
    assert resident_year(14, PRICES, count_boardplus=False)[0] - resident_year(14, PRICES)[0] == pytest.approx(130)


def test_real_data_resident_equals_21_meal_plan():
    # The same check on the prices parsed from the HUDS pages (data/huds_prices.csv).
    from model import load_prices

    real = load_prices()
    assert real.resident_board_fee_per_year / 2 - real.boardplus_per_semester == pytest.approx(
        real.non_resident_per_term[21])
