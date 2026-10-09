"""Checks that every current figure follows the rules in src/style.py (text at least 12 pt, a
main title of at least 16 pt, no footnote text in the image), plus the helpers behind the new
off-campus figures."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

import style  # noqa: E402
from charts import plot_grad_spending, plot_swipe_cost  # noqa: E402
from on_campus import plot_on_campus  # noqa: E402
from outside_food import (  # noqa: E402
    extra_cost_band,
    lowest_winning_price,
    plot_extra_cost,
    plot_lead,
    plot_main_map,
    plot_on_campus_extra,
    plot_spending,
)
from test_model import PRICES  # noqa: E402

FIGURES = [plot_lead, plot_main_map, plot_spending, plot_extra_cost, plot_swipe_cost, plot_on_campus_extra,
           plot_grad_spending, plot_on_campus]


@pytest.mark.parametrize("make", FIGURES, ids=lambda f: f.__name__)
def test_figure_rules(make):
    fig = make(PRICES)
    try:
        fig.canvas.draw()
        texts = style.all_text(fig)
        small = [(t.get_text(), t.get_fontsize()) for t in texts if t.get_fontsize() < style.MIN_TEXT]
        assert not small
        assert fig._suptitle is not None and fig._suptitle.get_fontsize() >= 16
        # No footnote: the only text placed on the figure itself (not in an axes) is the title and
        # a shared x-axis label.
        allowed = {id(fig._suptitle), id(fig._supxlabel)}
        assert all(id(t) in allowed for t in fig.texts if t.get_visible() and t.get_text().strip())
    finally:
        plt.close(fig)


def test_extra_cost_band():
    assert extra_cost_band(0) == 0
    assert extra_cost_band(0.001) == 0  # rounding noise still counts as the cheapest
    assert extra_cost_band(1) == 1
    assert extra_cost_band(249.99) == 1
    assert extra_cost_band(250) == 2
    assert extra_cost_band(1000) == 3
    assert extra_cost_band(3999) == 3
    assert extra_cost_band(4000) == 4
    with pytest.raises(ValueError):
        extra_cost_band(-1)


def test_lowest_winning_price():
    # The 21-meal plan first wins for someone eating every meal at HUDS. 21-meal plan per year:
    # 8812 + 24 away-weekend meals at p; no plan: 639 p. Equal at p = 8812 / 615 = 14.33.
    assert lowest_winning_price("nr21", PRICES) == pytest.approx(8812 / 615, abs=0.01)
    assert lowest_winning_price("no_plan", PRICES) == 3.0  # cheapest at the bottom of the range
    # The 5- and 10-meal plans can't win below their swipe cost (about $20).
    assert lowest_winning_price("nr5", PRICES) > 20
    assert lowest_winning_price("nr10", PRICES) > 20
