"""On-campus undergraduates: what the mandatory unlimited plan costs per meal actually eaten.

On-campus undergrads can't choose a plan, so instead of a decision map they get a chart of
cost per meal eaten against meals eaten per week, compared with HUDS guest prices.

BoardPlus ($65 per semester, $130 per year) is shown both ways: credited at face value
(fully spent) and not credited (never spent). The $65 is listed on the HUDS FAQ next to
2025-26 dates and is assumed to still apply in 2026-27.
"""

from typing import Dict, Optional

from model import MAX_PER_WEEK, Prices, WeeklyPattern, cost_resident_unlimited, load_term_weeks

FULL_WEEK = sum(MAX_PER_WEEK.values())  # 21 meal periods


def resident_year(meals_per_week: float, prices: Prices, term_weeks: Optional[Dict[str, float]] = None,
                  count_boardplus: bool = True):
    """(cost per year, meals eaten per year) on the unlimited plan."""
    term_weeks = term_weeks or load_term_weeks()
    if not 0 <= meals_per_week <= FULL_WEEK:
        raise ValueError(f"meals_per_week must be 0..{FULL_WEEK}")
    # The plan's cost doesn't depend on which meals are eaten, so spread them evenly over the week.
    share = meals_per_week / FULL_WEEK
    pattern = WeeklyPattern(**{m: n * share for m, n in MAX_PER_WEEK.items()})
    terms = [cost_resident_unlimited(pattern, w, prices, count_boardplus) for w in term_weeks.values()]
    return sum(t.total_cost for t in terms), sum(t.meals_eaten for t in terms)


def resident_cost_per_meal(meals_per_week: float, prices: Prices, **kw) -> Optional[float]:
    cost, meals = resident_year(meals_per_week, prices, **kw)
    return cost / meals if meals else None


def break_even_meals_per_week(guest_price: float, prices: Prices, term_weeks: Optional[Dict[str, float]] = None,
                              count_boardplus: bool = True) -> float:
    """Meals per week above which the plan costs less per meal than `guest_price`."""
    term_weeks = term_weeks or load_term_weeks()
    cost, _ = resident_year(0, prices, term_weeks, count_boardplus)
    return cost / (guest_price * sum(term_weeks.values()))


def plot_on_campus(prices: Prices, term_weeks: Optional[Dict[str, float]] = None):
    import matplotlib.pyplot as plt
    from matplotlib import patheffects

    from decision_map import INK, MUTED, SURFACE

    term_weeks = term_weeks or load_term_weeks()
    plan_color = "#2a78d6"
    grid_color, axis_color = "#e1e0d9", "#c3c2b7"
    x_min, y_max = 4, 50
    xs = [x_min + i * (FULL_WEEK - x_min) / 200 for i in range(201)]

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=SURFACE, layout="constrained")
    ax.set_facecolor(SURFACE)
    for count, style, label in [(True, "-", "Unlimited plan, BoardPlus spent (\\$4,406/term)"),
                                (False, (0, (4, 3)), "Unlimited plan, BoardPlus unspent (\\$4,471/term)")]:
        ys = [resident_cost_per_meal(x, prices, term_weeks=term_weeks, count_boardplus=count) for x in xs]
        ax.plot(xs, ys, color=plan_color, linewidth=2 if count else 1.5, linestyle=style,
                alpha=1 if count else 0.7, label=label, zorder=3)

    halo = [patheffects.withStroke(linewidth=3, foreground=SURFACE)]
    refs = [("Guest dinner", prices.guest_rates["dinner"]),
            ("Guest lunch or brunch", prices.guest_rates["lunch"]),
            ("Guest breakfast (Houses)", prices.guest_rates["breakfast_houses"])]
    for name, price in refs:
        ax.axhline(price, color=MUTED, linewidth=1, linestyle=(0, (1, 2)), zorder=2)
        ax.text(x_min + 0.15, price + 0.6, f"{name} \\${price:.2f}", color=MUTED, fontsize=9, path_effects=halo)

    for name, price in refs[:2]:
        m = break_even_meals_per_week(price, prices, term_weeks)
        if m <= FULL_WEEK:
            ax.plot(m, price, "o", markersize=8, color=plan_color, markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
            ax.annotate(f"{m:.1f} meals/wk", (m, price), xytext=(8, 8), textcoords="offset points",
                        fontsize=9, color=INK, path_effects=halo)
    full = resident_cost_per_meal(FULL_WEEK, prices, term_weeks=term_weeks)
    ax.plot(FULL_WEEK, full, "o", markersize=8, color=plan_color, markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    ax.annotate(f"Every meal: \\${full:.2f}", (FULL_WEEK, full), xytext=(-8, -16), textcoords="offset points",
                ha="right", fontsize=9, color=INK, path_effects=halo)

    ax.set_xlim(x_min, FULL_WEEK + 0.3)
    ax.set_ylim(0, y_max)
    ax.set_xticks(range(x_min, FULL_WEEK + 1))
    ax.set_xlabel("Meals eaten at HUDS per week", color=MUTED)
    ax.set_ylabel("Cost per meal eaten (USD)", color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    ax.grid(axis="y", color=grid_color, linewidth=0.8)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(axis_color)
    ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK)
    weeks = sum(term_weeks.values())
    fig.suptitle("On-campus undergraduates: what the unlimited plan costs per meal you actually eat",
                 color=INK, fontsize=12, x=0.01, ha="left")
    ax.set_title(f"2026-27 board fee \\${prices.resident_board_fee_per_year:,.0f}/yr over {weeks:.1f} weeks of dining "
                 f"(fall {term_weeks['fall']:.1f}, spring {term_weeks['spring']:.1f}). "
                 f"Below {x_min} meals/wk the cost per meal runs off the top of the chart.",
                 color=MUTED, fontsize=9, loc="left")
    return fig
