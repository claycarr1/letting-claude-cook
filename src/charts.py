"""Supporting charts for the report: yearly cost curves, cost per swipe, the gap map and the
Monte Carlo assumption effects. Every number comes from src/model.py via src/decision_map.py.
"""

from typing import Dict, List, Optional, Tuple

from decision_map import (
    BREAKFASTS_SKIPPED_RANGE,
    GROUPS,
    INK,
    MEALS_OUT_RANGE,
    MUTED,
    PLAN_COLORS,
    PLAN_LABELS,
    SHORT_LABELS,
    SURFACE,
    WEEKENDS_AWAY_RANGE,
    X_LABEL,
    Y_LABEL,
    annual_costs,
    grid,
)
from model import MAX_PER_WEEK, Prices, load_term_weeks

FULL_WEEK = sum(MAX_PER_WEEK.values())  # 21
OFF_CAMPUS = GROUPS["undergrad_offcampus"]
GRID_COLOR, AXIS_COLOR = "#e1e0d9", "#c3c2b7"


# ---------------------------------------------------------------------------- 1. yearly cost curves

def habits_for_meals(meals_per_week: float) -> Tuple[float, float]:
    """(meals_out, breakfasts_skipped) giving `meals_per_week` HUDS meals in a normal week, with
    every meal type cut in the same proportion ("spread out")."""
    if not 0 <= meals_per_week <= FULL_WEEK:
        raise ValueError(f"meals_per_week must be 0..{FULL_WEEK}")
    missing = 1 - meals_per_week / FULL_WEEK
    return MEALS_OUT_RANGE[1] * missing, BREAKFASTS_SKIPPED_RANGE[1] * missing


def yearly_costs(meals_per_week: float, prices: Prices, weekends_away: int = 2,
                 plans: List[str] = OFF_CAMPUS) -> Dict[str, float]:
    mo, bs = habits_for_meals(meals_per_week)
    return annual_costs(mo, bs, weekends_away, prices, plans)


def switch_points(prices: Prices, weekends_away: int = 2, plans: List[str] = OFF_CAMPUS,
                  step: float = 0.05) -> List[Tuple[float, str, str, float]]:
    """Where the cheapest option changes along the meals-per-week axis:
    [(meals_per_week, cheaper below, cheaper above, yearly cost there)], found by bisection."""
    def cheapest(x):
        c = yearly_costs(x, prices, weekends_away, plans)
        return min(plans, key=lambda p: (c[p], plans.index(p)))

    points = []
    n = round(FULL_WEEK / step)
    prev_x, prev = 0.0, cheapest(0.0)
    for i in range(1, n + 1):
        x = min(i * step, FULL_WEEK)
        cur = cheapest(x)
        if cur != prev:
            lo, hi = prev_x, x
            for _ in range(40):
                mid = (lo + hi) / 2
                c = yearly_costs(mid, prices, weekends_away, [prev, cur])
                lo, hi = (mid, hi) if c[prev] < c[cur] else (lo, mid)
            x_cross = (lo + hi) / 2
            points.append((x_cross, prev, cur, yearly_costs(x_cross, prices, weekends_away, [prev])[prev]))
        prev_x, prev = x, cur
    return points


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS_COLOR)


def _spread_labels(ys: List[float], min_gap: float) -> List[float]:
    """Nudge label positions apart so none are closer than min_gap, keeping their order."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < min_gap:
            out[b] = out[a] + min_gap
    return out


def plot_yearly_cost(prices: Prices, weekends_away: int = 2):
    import matplotlib.pyplot as plt
    from matplotlib import patheffects

    xs = [i * 0.25 for i in range(int(FULL_WEEK / 0.25) + 1)]
    curves = {p: [] for p in OFF_CAMPUS}
    for x in xs:
        c = yearly_costs(x, prices, weekends_away)
        for p in OFF_CAMPUS:
            curves[p].append(c[p])

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=SURFACE, layout="constrained")
    _style(ax)
    for p in OFF_CAMPUS:
        ax.plot(xs, curves[p], color=PLAN_COLORS[p], linewidth=2, zorder=3)
    halo = [patheffects.withStroke(linewidth=3, foreground=SURFACE)]
    ends = _spread_labels([curves[p][-1] for p in OFF_CAMPUS], min_gap=420)
    for p, y in zip(OFF_CAMPUS, ends):
        ax.text(FULL_WEEK + 0.3, y, PLAN_LABELS[p], va="center", fontsize=9, color=INK)
        ax.plot([FULL_WEEK, FULL_WEEK + 0.25], [curves[p][-1], y], color=PLAN_COLORS[p], linewidth=1)

    for x, below, above, cost in switch_points(prices, weekends_away):
        ax.plot(x, cost, "o", markersize=9, color=INK, markeredgecolor=SURFACE, markeredgewidth=2, zorder=5)
        # Label below-right of the dot, clear of the lines (which all rise to the right).
        ax.annotate(f"{x:.1f} meals/wk\n{SHORT_LABELS[below]} → {SHORT_LABELS[above]}", (x, cost),
                    xytext=(12, -34), textcoords="offset points", ha="left", fontsize=9, color=INK,
                    path_effects=halo)

    ax.set_xlim(0, FULL_WEEK)
    ax.set_xticks(range(0, FULL_WEEK + 1, 3))
    ax.set_xlabel("Meals eaten at HUDS per week (every meal type cut evenly)", color=MUTED)
    ax.set_ylabel("Cost per academic year (USD)", color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_ylim(bottom=0)
    fig.suptitle("Yearly cost of each option for an off-campus undergraduate", color=INK, fontsize=12,
                 x=0.01, ha="left")
    ax.set_title(f"2026-27 prices, {weekends_away} weekends away per term. Dots mark where the cheapest option changes.",
                 color=MUTED, fontsize=9, loc="left")
    return fig


# ---------------------------------------------------------------------------- 2. cost per swipe

def cost_per_swipe(prices: Prices, term_weeks: Optional[Dict[str, float]] = None) -> Dict[int, float]:
    """Yearly plan price / swipes available in a year, assuming every swipe is used."""
    weeks = sum((term_weeks or load_term_weeks()).values())
    return {n: 2 * price / (n * weeks) for n, price in sorted(prices.non_resident_per_term.items())}


def plot_swipe_cost(prices: Prices):
    import matplotlib.pyplot as plt

    swipes = cost_per_swipe(prices)
    plans = {5: "nr5", 10: "nr10", 21: "nr21"}
    bars = [(f"{n}-meal plan\n(one swipe)", v, PLAN_COLORS[plans[n]]) for n, v in swipes.items()]
    neutral = "#898781"
    bars += [("Guest breakfast\n(Houses)", prices.guest_rates["breakfast_houses"], neutral),
             ("Guest breakfast\n(Annenberg/Quincy)", prices.guest_rates["breakfast_annenberg_quincy"], neutral),
             ("Guest lunch\nor brunch", prices.guest_rates["lunch"], neutral),
             ("Guest dinner", prices.guest_rates["dinner"], neutral)]

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=SURFACE, layout="constrained")
    _style(ax)
    xs = [i + (0.6 if i >= 3 else 0) for i in range(len(bars))]  # gap between plans and guest prices
    for x, (label, value, color) in zip(xs, bars):
        ax.bar(x, value, width=0.62, color=color, zorder=3)
        ax.text(x, value + 0.4, f"${value:.2f}", ha="center", va="bottom", fontsize=9.5, color=INK)
    ax.set_xticks(xs, [b[0] for b in bars], fontsize=9, color=INK)
    ax.set_ylabel("USD", color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_ylim(0, max(b[1] for b in bars) * 1.15)
    ax.text(1, -0.2, "Off-campus plans", transform=ax.get_xaxis_transform(), ha="center", fontsize=9, color=MUTED)
    ax.text(4.6 + 0.9, -0.2, "Guest prices, incl. 7% tax", transform=ax.get_xaxis_transform(), ha="center",
            fontsize=9, color=MUTED)
    weeks = sum(load_term_weeks().values())
    fig.suptitle("What one swipe costs vs paying at the door", color=INK, fontsize=12, x=0.01, ha="left")
    ax.set_title(f"Swipe cost = yearly plan price / swipes available over {weeks:.1f} weeks, if every swipe is used. "
                 "A swipe saves money only on a meal that costs more than it.", color=MUTED, fontsize=9, loc="left")
    return fig


# ---------------------------------------------------------------------------- 3. gap map

GAP_BINS = [(0, 50), (50, 150), (150, 300), (300, 600), (600, 1200), (1200, float("inf"))]
GAP_COLORS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#0d366b"]  # sequential blue, light to dark


def gap_bin(gap: float) -> int:
    for i, (lo, hi) in enumerate(GAP_BINS):
        if lo <= gap < hi:
            return i
    raise ValueError(f"negative gap {gap}")


def _bin_label(lo, hi):
    return f"${lo:,}+" if hi == float("inf") else f"${lo:,}-{hi:,}"


def plot_gap_map(prices: Prices, group: str = "undergrad_offcampus"):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    from decision_map import GROUP_TITLES

    levels = list(range(WEEKENDS_AWAY_RANGE[1] + 1))
    ncols = 4
    nrows = -(-(len(levels) + 1) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 2.9 * nrows + 1.2), facecolor=SURFACE,
                             layout="constrained")
    axes = axes.ravel()
    nx, ny = MEALS_OUT_RANGE[1] + 1, BREAKFASTS_SKIPPED_RANGE[1] + 1
    for ax, we in zip(axes, levels):
        cells = grid(we, prices, group)
        for bs in range(ny):
            for mo in range(nx):
                ax.add_patch(Rectangle((mo, bs), 1, 1, facecolor=GAP_COLORS[gap_bin(cells[bs][mo].gap)],
                                       edgecolor=SURFACE, linewidth=0.6))
        # Dark lines where the cheapest option changes, so the plan regions stay visible.
        for bs in range(ny):
            for mo in range(nx):
                if mo + 1 < nx and cells[bs][mo].plan != cells[bs][mo + 1].plan:
                    ax.plot([mo + 1, mo + 1], [bs, bs + 1], color=INK, linewidth=1.6, solid_capstyle="butt")
                if bs + 1 < ny and cells[bs][mo].plan != cells[bs + 1][mo].plan:
                    ax.plot([mo, mo + 1], [bs + 1, bs + 1], color=INK, linewidth=1.6, solid_capstyle="butt")
        ax.set_xlim(0, nx)
        ax.set_ylim(0, ny)
        ax.set_aspect("equal")
        ax.set_title(f"{we} weekend{'s' if we != 1 else ''} away per term", fontsize=10, color=INK, loc="left")
        ax.set_xticks([x + 0.5 for x in range(0, nx, 2)], [str(x) for x in range(0, nx, 2)])
        ax.set_yticks([y + 0.5 for y in range(ny)], [str(y) for y in range(ny)])
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        for side in ax.spines.values():
            side.set_visible(False)
    for ax in axes[len(levels):]:
        ax.axis("off")
    handles = [Patch(facecolor=c, label=_bin_label(lo, hi)) for (lo, hi), c in zip(GAP_BINS, GAP_COLORS)]
    handles.append(Patch(facecolor=SURFACE, edgecolor=INK, linewidth=1.6, label="Boundary between plans"))
    axes[len(levels)].legend(handles=handles, loc="center left", frameon=False, fontsize=9, labelcolor=INK,
                             title="Saving vs the runner-up, per year", title_fontsize=10, alignment="left")
    fig.supxlabel(X_LABEL, color=MUTED, fontsize=10)
    fig.supylabel(Y_LABEL, color=MUTED, fontsize=10)
    fig.suptitle(f"How much the right choice saves: {GROUP_TITLES[group]}\n"
                 "Dollar gap per year between the cheapest and second-cheapest option, 2026-27 prices",
                 color=INK, fontsize=13, x=0.01, ha="left")
    return fig


# ---------------------------------------------------------------------------- 4. Monte Carlo assumption effects

ASSUMPTION_NAMES = {
    "meals out taken from": "Which meals are eaten elsewhere",
    "total weeks per year": "Weeks per term",
    "first week swipes": "Full or partial first-week swipes",
    "breakfast price": "House or Annenberg breakfast price",
}
SETTING_NAMES = {"dinners_first": "dinners first", "spread": "spread out", "annenberg_quincy": "Annenberg",
                 "houses": "House", "full": "full", "partial": "partial"}


def assumption_effects(agreement_by_assumption: Dict[str, Dict[str, float]]):
    """From monte_carlo_summary.json's agreement_by_assumption: for each assumption, the share of
    squares whose answer differs from the main map under each setting, and the difference between
    the settings that change it least and most (percentage points). Sorted biggest first."""
    out = []
    for key, by_setting in agreement_by_assumption.items():
        differ = {s: 1 - a for s, a in by_setting.items()}
        low = min(differ, key=differ.get)
        high = max(differ, key=differ.get)
        out.append({"assumption": ASSUMPTION_NAMES.get(key, key), "effect_pp": 100 * (differ[high] - differ[low]),
                    "low": (low, differ[low]), "high": (high, differ[high])})
    return sorted(out, key=lambda e: -e["effect_pp"])


def plot_assumption_effects(summary: dict):
    import matplotlib.pyplot as plt

    effects = assumption_effects(summary["agreement_by_assumption"])
    fig, ax = plt.subplots(figsize=(10, 4.2), facecolor=SURFACE, layout="constrained")
    _style(ax)
    ys = list(range(len(effects)))[::-1]
    for y, e in zip(ys, effects):
        ax.barh(y, e["effect_pp"], height=0.55, color="#2a78d6", zorder=3)

        def name(s):
            return SETTING_NAMES.get(s, f"{s} weeks/yr")
        detail = (f"{e['effect_pp']:.1f} pts  ({name(e['high'][0])}: {100 * e['high'][1]:.0f}% of squares differ, "
                  f"{name(e['low'][0])}: {100 * e['low'][1]:.0f}%)")
        ax.text(e["effect_pp"] + 0.2, y, detail, va="center", fontsize=9, color=INK)
    ax.set_yticks(ys, [e["assumption"] for e in effects], color=INK)
    ax.set_xlim(0, max(e["effect_pp"] for e in effects) * 2.1)
    ax.set_xlabel("Extra share of the map that changes answer (percentage points)", color=MUTED)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8)
    fig.suptitle("Which assumption moves the off-campus map most?", color=INK, fontsize=12, x=0.01, ha="left")
    ax.set_title(f"Monte Carlo, {summary['runs']:,} runs: how much more of the map changes answer "
                 "under one setting than the other", color=MUTED, fontsize=9, loc="left")
    return fig
