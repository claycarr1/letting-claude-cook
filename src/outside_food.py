"""Current model (from 2026-10-08): off-campus undergrads choosing between a non-resident plan and
no plan, where every meal not eaten at HUDS is eaten out or cooked at an "outside price".

Everyone eats 21 meals a week; only where they eat changes. A student who misses `missed` HUDS
meals a week eats them elsewhere at the outside price. Under a plan, the HUDS meals beyond the
week's swipes are also eaten elsewhere. With no plan, all 21 are. The outside price is a blend of
cooking and eating out; until real prices are collected it is a variable (about $3-$40).

year_food_spending() gives the whole food bill per academic year; per_semester() halves it.
Every cost comes from src/model.py via src/decision_map.annual_costs.
"""

from typing import Dict, List, Optional, Sequence, Tuple

from charts import habits_for_meals
from decision_map import GROUPS, PLAN_COLORS, PLAN_LABELS, SHORT_LABELS, annual_costs, habits_to_patterns
from model import MAX_PER_WEEK, Prices, load_term_weeks

FULL_WEEK = sum(MAX_PER_WEEK.values())  # 21 meals a week, every week
GROUP = "undergrad_offcampus_outside"
PLANS = GROUPS[GROUP]  # no_plan, nr5, nr10, nr21
WEEKENDS_AWAY = 2
PRICE_RANGE = (3.0, 40.0)

# PLACEHOLDERS -- not data. Positions for the chart markers until the hand-collected restaurant
# prices and the USDA/BLS cooking cost are in; replace them with the collected values.
PRICE_MARKERS = [("Cooking", 5.0), ("Cheap takeout", 13.0), ("Sit-down meal", 30.0)]
MARKERS_ARE_PLACEHOLDERS = True


def hud_meals_per_year(missed: float, weekends_away: int = WEEKENDS_AWAY,
                       term_weeks: Optional[Dict[str, float]] = None) -> float:
    """HUDS meals the student would eat in a year (before any swipe limit)."""
    term_weeks = term_weeks or load_term_weeks()
    mo, bs = habits_for_meals(FULL_WEEK - missed)
    normal, away = habits_to_patterns(mo, bs)
    return sum(normal.total * (w - weekends_away) + away.total * weekends_away for w in term_weeks.values())


def year_food_spending(missed: float, outside_price: float, prices: Prices, weekends_away: int = WEEKENDS_AWAY,
                       plans: Sequence[str] = PLANS) -> Dict[str, float]:
    """Total food spending per academic year under each option, for a student who misses `missed`
    HUDS meals a week (every meal type cut evenly) and pays `outside_price` for each meal not
    eaten at HUDS."""
    if not 0 <= missed <= FULL_WEEK:
        raise ValueError(f"missed must be 0..{FULL_WEEK}")
    mo, bs = habits_for_meals(FULL_WEEK - missed)
    hud_costs = annual_costs(mo, bs, weekends_away, prices, list(plans), outside_price=outside_price)
    # Meals eaten elsewhere whatever the option: the ones missed, plus weekend meals away.
    weeks = sum(load_term_weeks().values())
    always_elsewhere = (FULL_WEEK * weeks - hud_meals_per_year(missed, weekends_away)) * outside_price
    return {p: hud_costs[p] + always_elsewhere for p in plans}


def per_semester(year_costs: Dict[str, float]) -> Dict[str, float]:
    """Average semester (half the academic year)."""
    return {p: v / 2 for p, v in year_costs.items()}


def cheapest(missed: float, outside_price: float, prices: Prices, **kw) -> Tuple[str, float]:
    """(cheapest option, how much more the runner-up costs per year)."""
    c = year_food_spending(missed, outside_price, prices, **kw)
    ranked = sorted(PLANS, key=lambda p: (c[p], PLANS.index(p)))
    return ranked[0], c[ranked[1]] - c[ranked[0]]


def spending_grid(prices: Prices, xs: Sequence[float], ys: Sequence[float], weekends_away: int = WEEKENDS_AWAY):
    """{plan: rows[y][x] of semester spending} for every outside price x and meals missed y."""
    out = {p: [] for p in PLANS}
    for y in ys:
        rows = {p: [] for p in PLANS}
        for x in xs:
            c = per_semester(year_food_spending(y, x, prices, weekends_away))
            for p in PLANS:
                rows[p].append(c[p])
        for p in PLANS:
            out[p].append(rows[p])
    return out


# ---------------------------------------------------------------------------- drafts of the chart

SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]  # blue ramp, light to dark
PLAN_COLORS_NOW = {**PLAN_COLORS, "nr10": "#eda100"}
PANEL_TITLES = {"no_plan": "No plan (eat out or cook)", "nr5": "5-meal plan", "nr10": "10-meal plan",
                "nr21": "21-meal plan"}
X_LABEL = "Cost of a meal not eaten at HUDS (blend of cooking and eating out)"
Y_LABEL = "HUDS meals missed per week"


def _axes(n=150, ny=22):
    xs = [PRICE_RANGE[0] + i * (PRICE_RANGE[1] - PRICE_RANGE[0]) / (n - 1) for i in range(n)]
    ys = list(range(ny))
    return xs, ys


def _edges(vals):
    step = vals[1] - vals[0]
    return [v - step / 2 for v in vals] + [vals[-1] + step / 2]


def _markers(ax, labels=True, ink=INK):
    from matplotlib import patheffects

    for name, price in PRICE_MARKERS:
        ax.axvline(price, color=ink, linewidth=1, linestyle=(0, (4, 3)), alpha=0.8, zorder=4)
        if labels:
            tag = f"{name}\n~${price:.0f}" + ("?" if MARKERS_ARE_PLACEHOLDERS else "")
            ax.text(price, FULL_WEEK + 0.9, tag, ha="center", va="bottom", fontsize=8, color=ink,
                    path_effects=[patheffects.withStroke(linewidth=2.5, foreground=SURFACE)])


def _style(ax, show_y=True):
    ax.set_facecolor(SURFACE)
    ax.set_xlim(*PRICE_RANGE)
    ax.set_ylim(-0.5, FULL_WEEK + 0.5)
    ax.set_xticks([5, 10, 20, 30, 40], ["$5", "$10", "$20", "$30", "$40"])
    ax.set_yticks([0, 7, 14, 21])
    if not show_y:
        ax.set_yticklabels([])
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    for side in ax.spines.values():
        side.set_visible(False)


def cheapest_grid(prices: Prices, xs, ys, weekends_away: int = WEEKENDS_AWAY):
    return [[cheapest(y, x, prices, weekends_away=weekends_away)[0] for x in xs] for y in ys]


def _draw_cheapest(ax, grid, xs, ys, fontsize=9):
    from matplotlib import patheffects
    from matplotlib.colors import ListedColormap

    codes = [[PLANS.index(p) for p in row] for row in grid]
    ax.pcolormesh(_edges(xs), _edges(ys), codes, cmap=ListedColormap([PLAN_COLORS_NOW[p] for p in PLANS]),
                  vmin=-0.5, vmax=len(PLANS) - 0.5, shading="flat")
    # Dark lines along cell edges where the cheapest option changes (orange next to yellow needs
    # more than colour).
    from matplotlib.collections import LineCollection

    ex, ey = _edges(xs), _edges(ys)
    segs = []
    for j, row in enumerate(grid):
        for i in range(len(xs)):
            if i + 1 < len(xs) and row[i] != row[i + 1]:
                segs.append([(ex[i + 1], ey[j]), (ex[i + 1], ey[j + 1])])
            if j + 1 < len(ys) and row[i] != grid[j + 1][i]:
                segs.append([(ex[i], ey[j + 1]), (ex[i + 1], ey[j + 1])])
    ax.add_collection(LineCollection(segs, colors=INK, linewidths=1.2, capstyle="projecting"))
    for p in PLANS:
        pts = [(x, y) for row, y in zip(grid, ys) for x, q in zip(xs, row) if q == p]
        if len(pts) < 20:
            continue
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        x, y = min(pts, key=lambda q: ((q[0] - cx) / (xs[-1] - xs[0])) ** 2 + ((q[1] - cy) / (ys[-1] - ys[0])) ** 2)
        ax.text(x, y, SHORT_LABELS[p], ha="center", va="center", fontsize=fontsize, color=INK,
                path_effects=[patheffects.withStroke(linewidth=3, foreground=SURFACE)])


SHORT_X_LABEL = "Cost of a meal not eaten at HUDS"


def _panel_xlabels(fig):
    """Short x-axis label under every panel on the bottom row (figure-level labels collide with the footer)."""
    for ax in fig.axes:
        if ax.get_label() == "<colorbar>" or not ax.axison:
            continue
        ss = ax.get_subplotspec()
        if ss is not None and ss.is_last_row():
            ax.set_xlabel(SHORT_X_LABEL, color=MUTED, fontsize=9)


def _seq_cmap(n_bins: Optional[int] = None):
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("spend", SEQ, N=n_bins or 256)


def _footer(fig):
    note = ("Off-campus undergraduate, 21 meals a week, 2 weekends away per term, 2026-27 HUDS prices; "
            "spending per semester = half the academic year. x-axis: cost of a meal not eaten at HUDS, a "
            "blend of cooking and eating out.")
    if MARKERS_ARE_PLACEHOLDERS:
        note += " Marker prices are placeholders until real prices are collected."
    import textwrap

    # Wrap to the figure width (about 15 characters per inch at 8 pt) and reserve a strip of that
    # height at the bottom, in inches, so the note can't collide with the x-axis label.
    width_in, height_in = fig.get_size_inches()
    lines = textwrap.wrap(note, int(width_in * 15))
    strip = (0.08 + 0.16 * len(lines)) / height_in
    fig.get_layout_engine().set(rect=(0, strip, 1, 1 - strip))  # (left, bottom, width, height)
    fig.text(0.01, 0.01 / height_in * 4, "\n".join(lines), fontsize=8, color=MUTED, ha="left", va="bottom")


def draft_continuous(prices: Prices):
    """Draft A: one row, four spending panels on a shared continuous scale, plus the cheapest-option panel."""
    import matplotlib.pyplot as plt

    xs, ys = _axes()
    grid = spending_grid(prices, xs, ys)
    vmax = max(max(max(r) for r in grid[p]) for p in PLANS)
    fig, axes = plt.subplots(1, 5, figsize=(20, 5.2), facecolor=SURFACE, layout="constrained")
    for i, (ax, p) in enumerate(zip(axes, PLANS)):
        mesh = ax.pcolormesh(_edges(xs), _edges(ys), grid[p], cmap=_seq_cmap(), vmin=0, vmax=vmax, shading="flat")
        _style(ax, show_y=i == 0)
        _markers(ax)
        ax.set_title(PANEL_TITLES[p], fontsize=10, color=INK, loc="left", pad=28)
    cbar = fig.colorbar(mesh, ax=axes[:4], location="bottom", shrink=0.6, pad=0.02, aspect=50)
    cbar.set_label("Total food spending per semester", color=MUTED, fontsize=9)
    cbar.ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    cbar.ax.tick_params(colors=MUTED, labelsize=8)
    _draw_cheapest(axes[4], cheapest_grid(prices, xs, ys), xs, ys)
    _style(axes[4], show_y=False)
    _markers(axes[4])
    axes[4].set_title("Cheapest option", fontsize=10, color=INK, loc="left", pad=28, weight="bold")
    axes[0].set_ylabel(Y_LABEL, color=MUTED)
    _panel_xlabels(fig)
    fig.suptitle("Draft A: food spending per semester under each option, and which is cheapest",
                 color=INK, fontsize=13, x=0.01, ha="left")
    _footer(fig)
    return fig


def draft_binned(prices: Prices, step: float = 1000):
    """Draft B: 2 x 3 layout, spending in $1,000 bands with labelled contour lines."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm

    xs, ys = _axes()
    grid = spending_grid(prices, xs, ys)
    vmax = max(max(max(r) for r in grid[p]) for p in PLANS)
    levels = [step * i for i in range(int(vmax // step) + 2)]
    norm = BoundaryNorm(levels, 256)
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), facecolor=SURFACE, layout="constrained")
    flat = axes.ravel()
    for i, (ax, p) in enumerate(zip(flat, PLANS)):
        mesh = ax.pcolormesh(_edges(xs), _edges(ys), grid[p], cmap=_seq_cmap(), norm=norm, shading="flat")
        cs = ax.contour(xs, ys, grid[p], levels=levels[1::2], colors=SURFACE, linewidths=0.8)
        ax.clabel(cs, fmt=lambda v: f"${v / 1000:.0f}k", fontsize=7, colors=SURFACE)
        _style(ax, show_y=i % 3 == 0)
        _markers(ax)
        ax.set_title(PANEL_TITLES[p], fontsize=10, color=INK, loc="left", pad=28)
    _draw_cheapest(flat[4], cheapest_grid(prices, xs, ys), xs, ys)
    _style(flat[4], show_y=False)
    _markers(flat[4])
    flat[4].set_title("Cheapest option", fontsize=10, color=INK, loc="left", pad=28, weight="bold")
    flat[5].axis("off")
    cbar = fig.colorbar(mesh, ax=flat[5], location="left", fraction=0.08, pad=0.0)
    cbar.set_label("Total food spending per semester ($1,000 bands)", color=MUTED, fontsize=9)
    cbar.ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    cbar.ax.tick_params(colors=MUTED, labelsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel(Y_LABEL, color=MUTED)
    _panel_xlabels(fig)
    fig.suptitle("Draft B: same data in $1,000 bands with contour lines", color=INK, fontsize=13, x=0.01, ha="left")
    _footer(fig)
    return fig


def draft_extra_cost(prices: Prices):
    """Draft C: each option coloured by how much more it costs per semester than the cheapest option
    (0 = this option is the cheapest there), shared scale, plus the cheapest-option panel."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm

    xs, ys = _axes()
    grid = spending_grid(prices, xs, ys)
    best = [[min(grid[p][j][i] for p in PLANS) for i in range(len(xs))] for j in range(len(ys))]
    extra = {p: [[grid[p][j][i] - best[j][i] for i in range(len(xs))] for j in range(len(ys))] for p in PLANS}
    bounds = [0, 1, 100, 250, 500, 1000, 2000, 4000, 8000]
    norm = BoundaryNorm(bounds, 256, extend="max")
    fig, axes = plt.subplots(1, 5, figsize=(20, 5.2), facecolor=SURFACE, layout="constrained")
    for i, (ax, p) in enumerate(zip(axes, PLANS)):
        mesh = ax.pcolormesh(_edges(xs), _edges(ys), extra[p], cmap=_seq_cmap(), norm=norm, shading="flat")
        _style(ax, show_y=i == 0)
        _markers(ax)
        ax.set_title(PANEL_TITLES[p], fontsize=10, color=INK, loc="left", pad=28)
    cbar = fig.colorbar(mesh, ax=axes[:4], location="bottom", shrink=0.6, pad=0.02, aspect=50)
    cbar.set_label("How much more than the cheapest option, per semester (lightest = this is the cheapest)",
                   color=MUTED, fontsize=9)
    cbar.ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    cbar.ax.tick_params(colors=MUTED, labelsize=8)
    _draw_cheapest(axes[4], cheapest_grid(prices, xs, ys), xs, ys)
    _style(axes[4], show_y=False)
    _markers(axes[4])
    axes[4].set_title("Cheapest option", fontsize=10, color=INK, loc="left", pad=28, weight="bold")
    axes[0].set_ylabel(Y_LABEL, color=MUTED)
    _panel_xlabels(fig)
    fig.suptitle("Draft C: how much each option costs above the cheapest one", color=INK, fontsize=13,
                 x=0.01, ha="left")
    _footer(fig)
    return fig


def plot_main_map(prices: Prices):
    """The new main decision map: the cheapest-option panel on its own."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    xs, ys = _axes(n=220)
    grid = cheapest_grid(prices, xs, ys)
    fig, ax = plt.subplots(figsize=(10, 6.2), facecolor=SURFACE, layout="constrained")
    _draw_cheapest(ax, grid, xs, ys, fontsize=11)
    _style(ax)
    _markers(ax)
    ax.set_xlabel(X_LABEL, color=MUTED)
    ax.set_ylabel(Y_LABEL, color=MUTED)
    shown = {p for row in grid for p in row}
    handles = [Patch(facecolor=PLAN_COLORS_NOW[p], label=PLAN_LABELS[p]) for p in PLANS if p in shown]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9,
              labelcolor=INK, title="Cheapest option", title_fontsize=10, alignment="left")
    fig.suptitle("Decision map: cheapest option for an off-campus undergraduate", color=INK, fontsize=12,
                 x=0.01, ha="left")
    ax.set_title("Everyone eats 21 meals a week; meals not eaten at HUDS are eaten out or cooked at the price "
                 "on the x-axis.", color=MUTED, fontsize=9, loc="left", pad=30)
    _footer(fig)
    return fig


def write_grid_csv(prices: Prices, path, n=75):
    import csv

    xs, ys = _axes(n=n)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["meals_missed_per_week", "outside_price"] + [f"semester_{p}" for p in PLANS]
                   + ["cheapest", "runner_up_extra_per_year"])
        for y in ys:
            for x in xs:
                c = per_semester(year_food_spending(y, x, prices))
                best, gap = cheapest(y, x, prices)
                w.writerow([y, round(x, 2)] + [round(c[p], 2) for p in PLANS] + [best, round(gap, 2)])
