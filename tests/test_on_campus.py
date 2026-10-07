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
