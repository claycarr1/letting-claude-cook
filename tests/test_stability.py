"""Checks for the Monte Carlo stability check (src/stability.py)."""

import random

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

import style  # noqa: E402
from cooking import cooking_range  # noqa: E402
from outside_food import FULL_WEEK, cheapest  # noqa: E402
from restaurants import meal_type_prices  # noqa: E402
from stability import (  # noqa: E402
    CELLS, MEALS_OUT_FROM, TIP_RANGE, WEEKS_RANGE, agreement_by_assumption, baseline_draw, bootstrap_prices,
    cheapest_map, draw_assumptions, plot_assumption_effects, plot_meal_type_map, plot_stability, run,
    stability_class, summary,
)
from test_model import PRICES  # noqa: E402


def test_baseline_draw():
    b = baseline_draw()
    assert b.cooking_cost == pytest.approx(5.15, abs=0.01)
    assert b.eat_out["sit-down"] == pytest.approx(meal_type_prices("sit-down"))
    assert (b.tip, b.tip_on_tax, b.full_first_week_swipes, b.meals_out_from) == (0.18, False, False, "spread")
    # 40% cooking: 0.4 x 5.15 + 0.6 x the sit-down brunch average (17 + 19) / 2 x 1.25 = 22.50.
    assert b.outside_prices("sit-down", 0.4)["brunch"] == pytest.approx(0.4 * b.cooking_cost + 0.6 * 22.5)


def test_draws_reproducible_and_in_range():
    a, b = draw_assumptions(50, seed=7), draw_assumptions(50, seed=7)
    assert a == b
    lo, hi = min(cooking_range().values()), max(cooking_range().values())
    for d in a:
        assert WEEKS_RANGE[0] <= d.fall_weeks <= WEEKS_RANGE[1] and WEEKS_RANGE[0] <= d.spring_weeks <= WEEKS_RANGE[1]
        assert TIP_RANGE[0] <= d.tip <= TIP_RANGE[1]
        assert lo <= d.cooking_cost <= hi
        assert d.meals_out_from in MEALS_OUT_FROM
        assert d.eat_out["counter"]["brunch"] == d.eat_out["counter"]["lunch"]  # fallback
    assert {d.meals_out_from for d in a} == set(MEALS_OUT_FROM)


def test_bootstrap_of_identical_prices_is_that_price():
    meals = [{"service": "counter", "meal_type": m, "menu_price": "10"} for m in ("breakfast", "lunch", "dinner")]
    meals += [{"service": "sit-down", "meal_type": m, "menu_price": "20"} for m in ("breakfast", "lunch", "brunch", "dinner")]
    p = bootstrap_prices(meals, random.Random(1), tip=0.20, tip_on_tax=False)
    assert p["counter"] == pytest.approx({m: 10.70 for m in ("breakfast", "lunch", "brunch", "dinner")})
    assert p["sit-down"]["dinner"] == pytest.approx(20 * 1.27)


def test_cheapest_map_matches_direct_call():
    b = baseline_draw()
    cells = [("counter", 0.0, 21), ("sit-down", 0.0, 21), ("sit-down", 0.1, 7), ("sit-down", 1.0, 21)]
    m = cheapest_map(PRICES, b, cells)
    for s, c, e in cells:
        assert m[(s, c, e)] == cheapest(FULL_WEEK - e, b.outside_prices(s, c), PRICES)[0]
    assert m[("counter", 0.0, 21)] == "no_plan"   # counter meals average below a 21-meal swipe
    assert m[("sit-down", 0.0, 21)] == "nr21"     # sit-down meals cost more than a swipe
    assert m[("sit-down", 1.0, 21)] == "no_plan"  # cooking everything


def test_run_with_baseline_draws_is_fully_stable():
    cells = [("sit-down", 0.0, e) for e in range(0, 22, 3)]
    r = run(PRICES, draws=[baseline_draw()] * 3, processes=1, cells=cells)
    assert all(r.stability(c) == 1 for c in cells)
    assert r.contested() == []


def test_stability_class():
    assert [stability_class(s) for s in (1.0, 0.95, 0.94, 0.80, 0.79)] == ["solid", "solid", "mostly", "mostly",
                                                                           "toss-up"]


@pytest.fixture(scope="module")
def small_result():
    return run(PRICES, n=6, seed=3, processes=1)


def test_summary_and_effects(small_result):
    s = summary(small_result)
    assert s["squares"] == len(CELLS) == 2 * 21 * 22
    assert sum(s["classes"].values()) == s["squares"]
    assert set(agreement_by_assumption(small_result)) == {"weeks", "first_week", "meals_out_from", "tip",
                                                          "tip_on_tax", "cooking", "eat_out"}


@pytest.mark.parametrize("make", ["meal_type_map", "stability", "assumptions"])
def test_figure_rules(make, small_result):
    fig = {"meal_type_map": lambda: plot_meal_type_map(PRICES), "stability": lambda: plot_stability(small_result),
           "assumptions": lambda: plot_assumption_effects(small_result)}[make]()
    try:
        fig.canvas.draw()
        assert not [t.get_text() for t in style.all_text(fig) if t.get_fontsize() < style.MIN_TEXT]
        assert fig._suptitle.get_fontsize() >= 16
    finally:
        plt.close(fig)
