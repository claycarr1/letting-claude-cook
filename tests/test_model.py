"""Hand-worked checks for src/model.py.

Prices are pinned in PRICES below (2026-27 values from data/huds_prices.csv), and
test_load_prices_matches_csv checks the CSV still says exactly this. The expected
numbers in each test are worked out by hand in the comments.
"""

import pytest

from model import (
    CAFE_MEAL_PRICE_ESTIMATE,
    Prices,
    WeeklyPattern,
    cost_cash_at_cafe,
    cost_gradplus,
    cost_no_plan,
    cost_non_resident,
    cost_resident_unlimited,
    load_prices,
)

PRICES = Prices(
    resident_board_fee_per_year=8942.0,
    boardplus_per_semester=65.0,
    guest_rates={"breakfast_houses": 10.84, "breakfast_annenberg_quincy": 12.90,
                 "lunch": 17.30, "brunch": 17.30, "dinner": 21.40},
    non_resident_per_term={5: 1538.0, 10: 3060.0, 21: 4406.0},
    gradplus_per_term={"regular": {"fall": 400.0, "spring": 500.0},
                       "deluxe": {"fall": 600.0, "spring": 750.0}},
    gradplus_discount=0.10,
)
WEEKS = 15
EVERY_MEAL = WeeklyPattern(breakfast=7, lunch=5, brunch=2, dinner=7)  # all 21 meal periods
HALF_OF_MEALS = WeeklyPattern(breakfast=3.5, lunch=2.5, brunch=1, dinner=3.5)  # 10.5 per week


def test_load_prices_matches_csv():
    assert load_prices() == PRICES


# ---------------------------------------------------------------- resident unlimited

def test_resident_every_meal():
    # 8942 / 2 = 4471 per term, less 65 BoardPlus = 4406; 21 x 15 = 315 meals; 4406 / 315 = 13.9873
    r = cost_resident_unlimited(EVERY_MEAL, WEEKS, PRICES)
    assert r.plan_charge == 4471 and r.credits == 65
    assert r.total_cost == 4406
    assert r.meals_eaten == 315
    assert r.cost_per_meal == pytest.approx(13.9873, abs=1e-4)


def test_resident_half_of_meals():
    # 10.5 x 15 = 157.5 meals; 4406 / 157.5 = 27.9746
    r = cost_resident_unlimited(HALF_OF_MEALS, WEEKS, PRICES)
    assert r.total_cost == 4406
    assert r.cost_per_meal == pytest.approx(27.9746, abs=1e-4)


def test_resident_no_meals_has_no_cost_per_meal():
    r = cost_resident_unlimited(WeeklyPattern(), WEEKS, PRICES)
    assert r.total_cost == 4406 and r.cost_per_meal is None


# ---------------------------------------------------------------- non-resident tiers

def test_non_resident_10_every_swipe():
    # 7 dinners + 3 lunches = 10 swipes/week, none forfeited.
    # 3060 / (10 x 15 = 150 meals) = 20.40
    r = cost_non_resident(WeeklyPattern(lunch=3, dinner=7), WEEKS, PRICES, 10)
    assert r.total_cost == 3060 and r.extra_cash == 0 and r.unused == 0
    assert r.cost_per_meal == pytest.approx(20.40)


def test_non_resident_10_half_of_swipes():
    # 5 dinners/week, 5 swipes forfeited each week -> 75 forfeited over the term.
    # 3060 / (5 x 15 = 75 meals) = 40.80
    r = cost_non_resident(WeeklyPattern(dinner=5), WEEKS, PRICES, 10)
    assert r.total_cost == 3060 and r.unused == 75
    assert r.cost_per_meal == pytest.approx(40.80)


def test_non_resident_21_every_swipe():
    # 4406 / 315 = 13.9873
    r = cost_non_resident(EVERY_MEAL, WEEKS, PRICES, 21)
    assert r.unused == 0
    assert r.cost_per_meal == pytest.approx(13.9873, abs=1e-4)


def test_non_resident_21_half_of_swipes():
    # 10.5 swipes used, 10.5 forfeited per week -> 157.5 forfeited; 4406 / 157.5 = 27.9746
    r = cost_non_resident(HALF_OF_MEALS, WEEKS, PRICES, 21)
    assert r.unused == pytest.approx(157.5)
    assert r.cost_per_meal == pytest.approx(27.9746, abs=1e-4)


def test_non_resident_5_overflow_paid_at_guest_rates():
    # 7 dinners + 3 lunches but only 5 swipes: swipes go to 5 dinners (the dearest meal).
    # Cash per week: 2 dinners x 21.40 + 3 lunches x 17.30 = 42.80 + 51.90 = 94.70
    # Term: 1538 + 94.70 x 15 = 1538 + 1420.50 = 2958.50; / 150 meals = 19.7233
    r = cost_non_resident(WeeklyPattern(lunch=3, dinner=7), WEEKS, PRICES, 5)
    assert r.extra_cash == pytest.approx(1420.50)
    assert r.total_cost == pytest.approx(2958.50)
    assert r.cost_per_meal == pytest.approx(19.7233, abs=1e-4)


def test_non_resident_swipes_go_to_dearest_meals_first():
    # 5 lunches (17.30) + 7 breakfasts (10.84) on the 5-meal plan: swipes cover the lunches,
    # breakfasts are paid in cash: 7 x 10.84 = 75.88 per week.
    r = cost_non_resident(WeeklyPattern(breakfast=7, lunch=5), 1, PRICES, 5)
    assert r.extra_cash == pytest.approx(75.88)


# ---------------------------------------------------------------- no plan

def test_no_plan_guest_rates():
    # 7 x 21.40 + 3 x 17.30 = 149.80 + 51.90 = 201.70 per week; x 15 = 3025.50; / 150 = 20.17
    r = cost_no_plan(WeeklyPattern(lunch=3, dinner=7), WEEKS, PRICES)
    assert r.total_cost == pytest.approx(3025.50)
    assert r.cost_per_meal == pytest.approx(20.17)


def test_no_plan_every_meal():
    # 7 x 10.84 + 5 x 17.30 + 2 x 17.30 + 7 x 21.40 = 75.88 + 86.50 + 34.60 + 149.80 = 346.78
    # x 15 = 5201.70; / 315 = 16.5133
    r = cost_no_plan(EVERY_MEAL, WEEKS, PRICES)
    assert r.total_cost == pytest.approx(5201.70)
    assert r.cost_per_meal == pytest.approx(16.5133, abs=1e-4)


def test_no_plan_annenberg_breakfast_rate():
    # 1 breakfast/week x 10 weeks x 12.90 = 129.00
    r = cost_no_plan(WeeklyPattern(breakfast=1), 10, PRICES, breakfast_venue="annenberg_quincy")
    assert r.total_cost == pytest.approx(129.00)


# ---------------------------------------------------------------- GradPlus
# GradPlus meals are priced at cafe_meal_price; the default is the $12.50 ESTIMATE.

def test_gradplus_spends_every_dollar():
    # Cafe meal priced 400/9 = 44.44 so 10 meals list at 444.44 and cost 400.00 after 10% off:
    # the Regular fall balance is used exactly. Cost 400, nothing carried, 40.00 per meal.
    r = cost_gradplus(WeeklyPattern(dinner=1), 10, PRICES, "regular", "fall", cafe_meal_price=400 / 9)
    assert r.total_cost == pytest.approx(400)
    assert r.carry_out == pytest.approx(0) and r.extra_cash == pytest.approx(0)
    assert r.cost_per_meal == pytest.approx(40.00)


def test_gradplus_spends_half_and_forfeits_the_rest():
    # Deluxe spring, 10 meals listing at 41.67 each = 416.67, discounted to 375.00 = half of 750.
    # The other 375 is forfeited at year end. Cost 750 for 10 meals = 75.00 per meal.
    r = cost_gradplus(WeeklyPattern(dinner=1), 10, PRICES, "deluxe", "spring", cafe_meal_price=375 / 9)
    assert r.unused == pytest.approx(375)
    assert r.total_cost == pytest.approx(750)
    assert r.cost_per_meal == pytest.approx(75.00)


def test_gradplus_fall_rolls_over_and_spring_forfeits():
    # Regular, 1 cafe meal/week for 15 weeks each term at the 12.50 estimate.
    # Fall: list 15 x 12.50 = 187.50, discounted 168.75; leftover 400 - 168.75 = 231.25 rolls over.
    #       Fall cost = 400 - 231.25 = 168.75 -> 11.25 per meal.
    # Spring: balance 500 + 231.25 = 731.25; spends 168.75; 562.50 forfeited.
    #       Spring cost = 500 + 231.25 = 731.25 -> 48.75 per meal.
    # Year: 168.75 + 731.25 = 900 = 400 + 500 actually paid.
    lunch = WeeklyPattern(lunch=1)
    fall = cost_gradplus(lunch, WEEKS, PRICES, "regular", "fall")
    assert fall.carry_out == pytest.approx(231.25)
    assert fall.total_cost == pytest.approx(168.75)
    assert fall.cost_per_meal == pytest.approx(11.25)

    spring = cost_gradplus(lunch, WEEKS, PRICES, "regular", "spring", carry_in=fall.carry_out)
    assert spring.unused == pytest.approx(562.50)
    assert spring.total_cost == pytest.approx(731.25)
    assert spring.cost_per_meal == pytest.approx(48.75)
    assert fall.total_cost + spring.total_cost == pytest.approx(900)


def test_gradplus_overflow_paid_at_full_price():
    # Deluxe fall, 5 meals/week x 15 = 75 meals listing at 75 x 12.50 = 937.50.
    # 600 of balance buys 600 / 0.9 = 666.67 of list-price food; the other 270.83 is paid in full.
    # Total 600 + 270.83 = 870.83 (vs 937.50 paying cash: saves 10% of 666.67) -> 11.6111 per meal.
    r = cost_gradplus(WeeklyPattern(dinner=5), WEEKS, PRICES, "deluxe", "fall")
    assert r.extra_cash == pytest.approx(270.8333, abs=1e-4)
    assert r.total_cost == pytest.approx(870.8333, abs=1e-4)
    assert r.cost_per_meal == pytest.approx(11.6111, abs=1e-4)
    assert r.carry_out == 0


def test_gradplus_default_cafe_price_is_flagged_as_estimate():
    r = cost_gradplus(WeeklyPattern(lunch=1), WEEKS, PRICES, "regular", "fall")
    assert CAFE_MEAL_PRICE_ESTIMATE == 12.50
    assert r.details["cafe_meal_price"] == 12.50
    assert "ESTIMATE" in r.notes


def test_gradplus_explicit_cafe_price_is_not_flagged():
    r = cost_gradplus(WeeklyPattern(lunch=1), WEEKS, PRICES, "regular", "fall", cafe_meal_price=11.00)
    assert r.notes == ""
    # 15 x 11.00 = 165.00, discounted 148.50
    assert r.details["balance_spent"] == pytest.approx(148.50)


def test_gradplus_cafe_price_same_for_every_meal_type():
    a = cost_gradplus(WeeklyPattern(breakfast=2), WEEKS, PRICES, "regular", "fall")
    b = cost_gradplus(WeeklyPattern(dinner=2), WEEKS, PRICES, "regular", "fall")
    assert a.total_cost == pytest.approx(b.total_cost)


def test_cash_at_cafe_baseline():
    # 5 meals/week x 15 weeks x 12.50 = 937.50, flagged as an estimate; GradPlus Deluxe on the same
    # pattern (test above) costs 870.83, i.e. 66.67 less = 10% of the 666.67 the balance covers.
    r = cost_cash_at_cafe(WeeklyPattern(dinner=5), WEEKS)
    assert r.total_cost == pytest.approx(937.50)
    assert "ESTIMATE" in r.notes
    assert cost_cash_at_cafe(WeeklyPattern(dinner=5), WEEKS, cafe_meal_price=10).total_cost == pytest.approx(750)


# ---------------------------------------------------------------- input checks

def test_pattern_rejects_more_meals_than_served():
    with pytest.raises(ValueError):
        WeeklyPattern(lunch=6)  # lunch is Mon-Fri only


def test_weeks_must_be_positive():
    with pytest.raises(ValueError):
        cost_no_plan(EVERY_MEAL, 0, PRICES)


def test_gradplus_fall_cannot_take_carry_in():
    with pytest.raises(ValueError):
        cost_gradplus(EVERY_MEAL, WEEKS, PRICES, "regular", "fall", carry_in=10)


def test_unknown_non_resident_tier():
    with pytest.raises(ValueError):
        cost_non_resident(EVERY_MEAL, WEEKS, PRICES, 7)


def test_gradplus_rejects_negative_cafe_price():
    with pytest.raises(ValueError):
        cost_gradplus(EVERY_MEAL, WEEKS, PRICES, "regular", "fall", cafe_meal_price=-1)
