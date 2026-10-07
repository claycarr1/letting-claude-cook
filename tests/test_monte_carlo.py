"""Checks for src/monte_carlo.py. Small runs in one process so the tests stay fast."""

import pytest

from monte_carlo import (
    CELLS, WEEKS_RANGE, baseline_draw, cheapest_map, draw_assumptions, factor_effects, nr10_summary, run,
)
from on_campus import band, resident_cost_per_meal
from test_model import PRICES


def test_draws_are_reproducible_and_in_range():
    a, b = draw_assumptions(500, seed=7), draw_assumptions(500, seed=7)
    assert a == b
    assert a != draw_assumptions(500, seed=8)
    for d in a:
        assert WEEKS_RANGE[0] <= d.fall_weeks <= WEEKS_RANGE[1]
        assert WEEKS_RANGE[0] <= d.spring_weeks <= WEEKS_RANGE[1]
    assert any(d.fall_weeks != d.spring_weeks for d in a)  # drawn separately
    # 50/50 coins: with 500 draws each share should be well within 0.4-0.6.
    for share in [sum(d.full_first_week_swipes for d in a) / 500,
                  sum(d.meals_out_from == "dinners_first" for d in a) / 500,
                  sum(d.breakfast_venue == "annenberg_quincy" for d in a) / 500,
                  sum(d.boardplus_spent for d in a) / 500]:
        assert 0.4 < share < 0.6


def test_baseline_only_runs_are_fully_stable():
    result = run(PRICES, draws=[baseline_draw()] * 3, processes=1)
    assert all(result.stability(c) == 1 for c in CELLS)
    assert all(not result.alternatives[c] for c in CELLS)


def test_counts_match_a_direct_recount():
    draws = draw_assumptions(4, seed=11)
    result = run(PRICES, draws=draws, processes=1)
    maps = [cheapest_map(PRICES, d) for d in draws]
    for c in CELLS[::37]:
        assert result.agree[c] == sum(m[c] == result.baseline[c] for m in maps)
    assert result.nr10_cells == [sum(m[c] == "nr10" for c in CELLS) for m in maps]
    assert nr10_summary(result)["runs"] == 4
    assert set(factor_effects(result)) == {"first week swipes", "meals out taken from", "breakfast price",
                                           "total weeks per year"}


def test_example_student_flips_with_dinners_first():
    # From test_decision_map.test_example_student_dinners_first: the 5-meal plan on the main
    # map, paying as you go once meals out come off dinners first.
    base = baseline_draw()
    dinners = base.__class__(**{**base.__dict__, "meals_out_from": "dinners_first"})
    assert cheapest_map(PRICES, base)[(2, 4, 3)] == "nr5"
    assert cheapest_map(PRICES, dinners)[(2, 4, 3)] == "cash_guest"


def test_on_campus_band():
    # With every draw at the baseline the band collapses onto the main line.
    xs = [7, 14, 21]
    lo, hi = band(PRICES, [baseline_draw()] * 5, xs)
    assert lo == hi == pytest.approx([resident_cost_per_meal(x, PRICES) for x in xs])
    # Real draws: the band brackets the main line at 21 meals/week. Extremes by hand:
    # 8812 / (21 x 32) = 13.11 (longest terms, BoardPlus spent) to 8942 / (21 x 29) = 14.68.
    lo, hi = band(PRICES, draw_assumptions(400), [21])
    assert 13.11 <= lo[0] <= resident_cost_per_meal(21, PRICES) <= hi[0] <= 14.69
