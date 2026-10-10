"""Current model (from 2026-10-08): off-campus undergrads choosing between a non-resident plan and
no plan, where every meal not eaten at HUDS is eaten out or cooked at an "outside price".

Everyone eats 21 meals a week; only where they eat changes. A student who misses `missed` HUDS
meals a week eats them elsewhere at the outside price. Under a plan, the HUDS meals beyond the
week's swipes are also eaten elsewhere. With no plan, all 21 are. The outside price is a blend of
cooking and eating out; until real prices are collected it is a variable (about $3-$40).

year_food_spending() gives the whole food bill per academic year; per_semester() halves it.
Every cost comes from src/model.py via src/decision_map.annual_costs.
"""

from typing import Dict, List, Optional, Sequence, Tuple, Union

from charts import habits_for_meals
from cooking import cooking_cost_per_meal
from restaurants import average_price
from decision_map import GROUPS, NR21_NAME, PLAN_COLORS, PLAN_LABELS, SHORT_LABELS, annual_costs, habits_to_patterns
from model import MAX_PER_WEEK, Prices, load_term_weeks, outside_prices_for

FULL_WEEK = sum(MAX_PER_WEEK.values())  # 21 meals a week, every week
GROUP = "undergrad_offcampus_outside"
PLANS = GROUPS[GROUP]  # no_plan, nr5, nr10, nr21
WEEKENDS_AWAY = 2
PRICE_RANGE = (3.0, 40.0)

# Chart markers, all from data. Cooking: USDA moderate-cost plan for a student cooking alone,
# adjusted to Northeast prices (src/cooking.py). Cheap takeout and sit-down: mean out-the-door
# price of the hand-collected counter-service and sit-down meals (src/restaurants.py).
PRICE_MARKERS = [("Cooking", cooking_cost_per_meal()), ("Cheap takeout", average_price("counter")),
                 ("Sit-down", average_price("sit-down"))]
PLACEHOLDER_MARKERS = set()  # names of markers that are still placeholders (shown as "~$13?")


def hud_meals_by_type(missed: float, weekends_away: int = WEEKENDS_AWAY,
                      term_weeks: Optional[Dict[str, float]] = None,
                      meals_out_from: str = "spread") -> Dict[str, float]:
    """{meal type: HUDS meals the student would eat in a year} (before any swipe limit).
    Breakfasts are cut in proportion; lunches, brunches and dinners as `meals_out_from` says."""
    term_weeks = term_weeks or load_term_weeks()
    mo, bs = habits_for_meals(FULL_WEEK - missed)
    normal, away = habits_to_patterns(mo, bs, meals_out_from)
    n, a = normal.counts(), away.counts()
    return {m: sum(n[m] * (w - weekends_away) + a[m] * weekends_away for w in term_weeks.values())
            for m in MAX_PER_WEEK}


def hud_meals_per_year(missed: float, weekends_away: int = WEEKENDS_AWAY,
                       term_weeks: Optional[Dict[str, float]] = None, meals_out_from: str = "spread") -> float:
    """HUDS meals the student would eat in a year (before any swipe limit)."""
    return sum(hud_meals_by_type(missed, weekends_away, term_weeks, meals_out_from).values())


def year_food_spending(missed: float, outside_price: Union[float, Dict[str, float]], prices: Prices,
                       weekends_away: int = WEEKENDS_AWAY, plans: Sequence[str] = PLANS,
                       term_weeks: Optional[Dict[str, float]] = None, meals_out_from: str = "spread",
                       full_first_week_swipes: bool = False) -> Dict[str, float]:
    """Total food spending per academic year under each option, for a student who misses `missed`
    HUDS meals a week and pays `outside_price` for each meal not eaten at HUDS: one price, or
    {meal type: price} (breakfast, lunch, brunch, dinner)."""
    if not 0 <= missed <= FULL_WEEK:
        raise ValueError(f"missed must be 0..{FULL_WEEK}")
    term_weeks = term_weeks or load_term_weeks()
    price = outside_prices_for(outside_price)
    mo, bs = habits_for_meals(FULL_WEEK - missed)
    hud_costs = annual_costs(mo, bs, weekends_away, prices, list(plans), term_weeks=term_weeks,
                             meals_out_from=meals_out_from, full_first_week_swipes=full_first_week_swipes,
                             outside_price=price)
    # Meals eaten elsewhere whatever the option: the ones missed, plus weekend meals away.
    weeks = sum(term_weeks.values())
    hud = hud_meals_by_type(missed, weekends_away, term_weeks, meals_out_from)
    always_elsewhere = sum((MAX_PER_WEEK[m] * weeks - hud[m]) * price[m] for m in MAX_PER_WEEK)
    return {p: hud_costs[p] + always_elsewhere for p in plans}


def per_semester(year_costs: Dict[str, float]) -> Dict[str, float]:
    """Average semester (half the academic year)."""
    return {p: v / 2 for p, v in year_costs.items()}


def cheapest(missed: float, outside_price: float, prices: Prices, **kw) -> Tuple[str, float]:
    """(cheapest option, how much more the runner-up costs per year)."""
    c = year_food_spending(missed, outside_price, prices, **kw)
    ranked = sorted(PLANS, key=lambda p: (c[p], PLANS.index(p)))
    return ranked[0], c[ranked[1]] - c[ranked[0]]


def lowest_winning_price(plan: str, prices: Prices, lo: float = PRICE_RANGE[0], hi: float = 60.0) -> Optional[float]:
    """Lowest outside price (to the cent) at which `plan` is the cheapest option for some whole
    number of HUDS meals a week, or None if it never wins up to `hi`."""
    def wins(price):
        return any(cheapest(FULL_WEEK - eaten, price, prices)[0] == plan for eaten in range(FULL_WEEK + 1))

    if not wins(hi):
        return None
    if wins(lo):
        return lo
    while hi - lo > 0.005:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if wins(mid) else (mid, hi)
    return round(hi, 2)


# ---------------------------------------------------------------------------- figures
# Rules for every figure are in src/style.py: text >= 12 pt, takeaway title, no footnote (the
# setup goes in the caption in report.md). The y-axis is meals eaten at HUDS (21 - missed).

SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
PLAN_COLORS_NOW = {**PLAN_COLORS, "nr10": "#eda100"}
LABEL_INK = {"nr10": "#9a6a00"}  # the yellow, darkened for text on the light surface
PANEL_TITLES = {"no_plan": "No plan (eat out or cook)", "nr5": "5-meal plan", "nr10": "10-meal plan",
                "nr21": NR21_NAME}
X_LABEL = "Average cost of a meal not eaten at HUDS (cooking and eating out mixed)"
Y_LABEL = "Meals you'd eat at HUDS per week (if you had swipes)"
SWIPES = {"nr5": 5, "nr10": 10}  # weekly swipes, marked on those plans' panels

# Five steps of one blue, light to dark (spending chart and extra-cost chart).
SEQ5 = ["#cde2fb", "#8fbcf1", "#3987e5", "#1d5aa8", "#0d366b"]
EXTRA_BOUNDS = [0, 0.005, 250, 1000, 4000, float("inf")]  # per semester
EXTRA_LABELS = ["$0 (cheapest)", "Under $250", "$250-1,000", "$1,000-4,000", "$4,000+"]


def _axes(n=150):
    xs = [PRICE_RANGE[0] + i * (PRICE_RANGE[1] - PRICE_RANGE[0]) / (n - 1) for i in range(n)]
    eaten = list(range(FULL_WEEK + 1))
    return xs, eaten


def _edges(vals):
    step = vals[1] - vals[0]
    return [v - step / 2 for v in vals] + [vals[-1] + step / 2]


def spending_grid(prices: Prices, xs: Sequence[float], eaten: Sequence[float], weekends_away: int = WEEKENDS_AWAY):
    """{plan: rows[y][x] of semester spending} for every outside price x and HUDS meals eaten y."""
    out = {p: [] for p in PLANS}
    for y in eaten:
        rows = {p: [] for p in PLANS}
        for x in xs:
            c = per_semester(year_food_spending(FULL_WEEK - y, x, prices, weekends_away))
            for p in PLANS:
                rows[p].append(c[p])
        for p in PLANS:
            out[p].append(rows[p])
    return out


def cheapest_grid(prices: Prices, xs, eaten, weekends_away: int = WEEKENDS_AWAY):
    return [[cheapest(FULL_WEEK - y, x, prices, weekends_away=weekends_away)[0] for x in xs] for y in eaten]


def extra_cost_band(extra: float) -> int:
    """Index into EXTRA_LABELS for an option costing `extra` more per semester than the cheapest."""
    if extra < 0:
        raise ValueError(f"negative extra cost {extra}")
    return next(i for i, hi in enumerate(EXTRA_BOUNDS[1:]) if extra < hi)


def marker_price_text(name, price):
    """"$5.15" for a collected price, "~$13?" for a placeholder."""
    return f"~${price:.0f}?" if name in PLACEHOLDER_MARKERS else f"${price:.2f}"


def _two_lines(label):
    """'21-meal plan (= on-campus unlimited plan)' -> two lines, for direct labels."""
    return label.replace(" (", "\n(", 1)


def _marker_label(name, price):
    return f"{name}\n{marker_price_text(name, price)}"


def _price_axis(ax, markers=True):
    """x-axis: dollar ticks, with the cooking / takeout / sit-down markers as small labels on a
    second line under them (no lines across the plot)."""
    import style

    ax.set_xlim(*PRICE_RANGE)
    ax.set_xticks([10, 20, 30, 40], ["$10", "$20", "$30", "$40"])
    ax.tick_params(axis="x", which="major", colors=MUTED, labelsize=style.TICK, length=0, pad=4)
    if markers:
        ax.xaxis.remove_overlapping_locs = False  # keep the $30 marker, which sits on a dollar tick
        ax.set_xticks([p for _, p in PRICE_MARKERS], [_marker_label(n, p) for n, p in PRICE_MARKERS], minor=True)
        ax.tick_params(axis="x", which="minor", colors=INK, labelcolor=MUTED, labelsize=style.TICK, length=5,
                       width=1.2, direction="out", pad=22)
        for t in ax.get_xticklabels(minor=True):
            t.set_fontstyle("italic")


def _eaten_axis(ax, show_labels=True):
    import style

    ax.set_ylim(-0.5, FULL_WEEK + 0.5)
    ax.set_yticks([0, 7, 14, 21])
    if not show_labels:
        ax.set_yticklabels([])
    ax.tick_params(axis="y", colors=MUTED, labelsize=style.TICK, length=0)


def _frameless(ax):
    ax.set_facecolor(SURFACE)
    for side in ax.spines.values():
        side.set_visible(False)


def _region_edges(mask, xs, ys):
    """Line segments along cell edges between True and False cells of mask[y][x] (and around the
    grid edge where True)."""
    ex, ey = _edges(xs), _edges(ys)
    segs = []
    for j in range(len(ys)):
        for i in range(len(xs)):
            if i + 1 < len(xs) and mask[j][i] != mask[j][i + 1]:
                segs.append([(ex[i + 1], ey[j]), (ex[i + 1], ey[j + 1])])
            if j + 1 < len(ys) and mask[j][i] != mask[j + 1][i]:
                segs.append([(ex[i], ey[j + 1]), (ex[i + 1], ey[j + 1])])
    return segs


def _label_point(pts, xs, ys):
    """The point of `pts` nearest their centre (scaled to the axes), for a region label."""
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    return min(pts, key=lambda q: ((q[0] - cx) / (xs[-1] - xs[0])) ** 2 + ((q[1] - cy) / (ys[-1] - ys[0])) ** 2)


def _halo(width=3):
    from matplotlib import patheffects

    return [patheffects.withStroke(linewidth=width, foreground=SURFACE)]


def _draw_cheapest(ax, grid, xs, ys, fontsize=14):
    from matplotlib.collections import LineCollection
    from matplotlib.colors import ListedColormap

    codes = [[PLANS.index(p) for p in row] for row in grid]
    ax.pcolormesh(_edges(xs), _edges(ys), codes, cmap=ListedColormap([PLAN_COLORS_NOW[p] for p in PLANS]),
                  vmin=-0.5, vmax=len(PLANS) - 0.5, shading="flat")
    # Dark lines where the cheapest option changes (orange next to yellow needs more than colour).
    segs = []
    for p in PLANS:
        segs += _region_edges([[q == p for q in row] for row in grid], xs, ys)
    ax.add_collection(LineCollection(segs, colors=INK, linewidths=1.4, capstyle="projecting"))
    for p in PLANS:
        pts = [(x, y) for row, y in zip(grid, ys) for x, q in zip(xs, row) if q == p]
        if len(pts) < 20:
            continue
        x, y = _label_point(pts, xs, ys)
        ax.text(x, y, _two_lines(SHORT_LABELS[p]), ha="center", va="center", fontsize=fontsize, color=INK,
                weight="bold", path_effects=_halo())


def plot_main_map(prices: Prices):
    """The decision map: the cheapest option by outside price and HUDS meals eaten per week."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    import style

    xs, ys = _axes(n=220)
    grid = cheapest_grid(prices, xs, ys)
    fig, ax = plt.subplots(figsize=(12, 7.5), facecolor=SURFACE, layout="constrained")
    _frameless(ax)
    _draw_cheapest(ax, grid, xs, ys, fontsize=15)
    _price_axis(ax)
    _eaten_axis(ax)
    ax.set_xlabel(X_LABEL, color=MUTED, fontsize=style.LABEL)
    ax.set_ylabel(Y_LABEL, color=MUTED, fontsize=style.LABEL)
    shown = {p for row in grid for p in row}
    handles = [Patch(facecolor=PLAN_COLORS_NOW[p], edgecolor=INK, linewidth=0.8, label=_two_lines(PLAN_LABELS[p]))
               for p in PLANS if p in shown]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=style.TICK,
              labelcolor=INK, title="Cheapest option", title_fontsize=style.LABEL, alignment="left")
    t21 = lowest_winning_price("nr21", prices)
    style.title(fig, f"No plan is cheapest unless a meal elsewhere costs over ${t21:.0f};\n"
                     "above that, the more you eat at HUDS, the bigger the plan that wins")
    return fig


def plot_lead(prices: Prices):
    """Lead chart: one panel per marker price, food spending per semester against HUDS meals eaten
    per week, one line per option, labelled at the line's end. Same y-scale on every panel."""
    import matplotlib.pyplot as plt

    from charts import _spread_labels
    import style

    titles = {"Cooking": "If you mostly cook", "Cheap takeout": "If you get cheap takeout",
              "Sit-down": "If you eat at sit-down places"}
    eaten = [i * 0.25 for i in range(4 * FULL_WEEK + 1)]
    curves = {}
    for name, price in PRICE_MARKERS:
        rows = [per_semester(year_food_spending(FULL_WEEK - e, price, prices)) for e in eaten]
        curves[name] = {p: [r[p] for r in rows] for p in PLANS}
    y_max = max(max(max(c) for c in by_plan.values()) for by_plan in curves.values())
    y_top = 1000 * (int(y_max // 1000) + 1)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.8), facecolor=SURFACE, layout="constrained", sharey=True)
    for ax, (name, price) in zip(axes, PRICE_MARKERS):
        _frameless(ax)
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color("#c3c2b7")
        ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
        ax.set_axisbelow(True)
        for p in PLANS:
            ax.plot(eaten, curves[name][p], color=PLAN_COLORS_NOW[p], linewidth=2.5, solid_capstyle="round")
        ends = [curves[name][p][-1] for p in PLANS]
        for p, y in zip(PLANS, _spread_labels(ends, min_gap=0.09 * y_top)):
            label = "21-meal plan\n(= on-campus plan)" if p == "nr21" else SHORT_LABELS[p]
            ax.text(FULL_WEEK + 0.5, y, label, va="center", fontsize=style.TICK, weight="bold",
                    color=LABEL_INK.get(p, PLAN_COLORS_NOW[p]))
        ax.set_xlim(0, FULL_WEEK)
        ax.set_ylim(0, y_top)
        ax.set_xticks([0, 7, 14, 21])
        ax.tick_params(colors=MUTED, labelsize=style.TICK, length=0)
        tag = f"~${price:.0f}/meal?" if name in PLACEHOLDER_MARKERS else f"${price:.2f}/meal"
        ax.set_title(f"{titles[name]} ({tag})", color=INK, fontsize=style.PANEL_TITLE, loc="left", pad=10)
    axes[0].set_ylabel("Food spending per semester", color=MUTED, fontsize=style.LABEL)
    fig.supxlabel(Y_LABEL, color=MUTED, fontsize=style.LABEL)  # one label under all three panels
    axes[0].yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    t21 = lowest_winning_price("nr21", prices)
    style.title(fig, f"A meal plan only saves money if a meal elsewhere would cost you more than about ${t21:.0f}")
    return fig


def _swipes_line(ax, n):
    """Horizontal line at the plan's weekly swipes: above it, extra meals are eaten out or cooked."""
    import style

    ax.axhline(n, color=INK, linewidth=1.6, linestyle=(0, (5, 3)), zorder=5)
    ax.text(PRICE_RANGE[0] + 0.6, n + 0.35, "Swipes run out here", ha="left", va="bottom", fontsize=style.TICK,
            color=INK, weight="bold", zorder=6, path_effects=_halo())


def _spending_panels(fig_title: str, panel_data, cmap, norm, colorbar_label, colorbar_ticks=None,
                     colorbar_ticklabels=None, decorate=None):
    """2 x 2 grid, one panel per option, shared colour scale and a colourbar on the right."""
    import matplotlib.pyplot as plt

    import style

    xs, ys = _axes()
    fig, axes = plt.subplots(2, 2, figsize=(15, 11.5), facecolor=SURFACE, layout="constrained")
    for i, (ax, p) in enumerate(zip(axes.ravel(), PLANS)):
        _frameless(ax)
        mesh = ax.pcolormesh(_edges(xs), _edges(ys), panel_data[p], cmap=cmap, norm=norm, shading="flat")
        if decorate:
            decorate(ax, p, xs, ys)
        if p in SWIPES:
            _swipes_line(ax, SWIPES[p])
        _price_axis(ax)
        _eaten_axis(ax, show_labels=i % 2 == 0)
        ax.set_title(PANEL_TITLES[p], fontsize=style.PANEL_TITLE, color=INK, loc="left", pad=10)
        if i % 2 == 0:
            ax.set_ylabel(Y_LABEL, color=MUTED, fontsize=style.LABEL)
    cbar = fig.colorbar(mesh, ax=axes, location="right", shrink=0.7, aspect=30, pad=0.02)
    cbar.set_label(colorbar_label, color=MUTED, fontsize=style.LABEL)
    if colorbar_ticks is not None:
        cbar.set_ticks(colorbar_ticks, labels=colorbar_ticklabels)
    else:
        cbar.ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    cbar.ax.tick_params(colors=MUTED, labelsize=style.TICK, length=0)
    cbar.outline.set_visible(False)
    fig.supxlabel(X_LABEL, color=MUTED, fontsize=style.LABEL)  # one label under both columns
    style.title(fig, fig_title)
    return fig


LABEL_ROWS = [16, 18, 13, 20, 8, 3, 1]  # rows tried for contour labels, away from the swipe lines at 5 and 10


def _contour_label_spots(values, xs, ys, levels):
    """One label position per contour level: where it crosses the first row of LABEL_ROWS it
    crosses at all (so labels stay off the "Swipes run out here" lines)."""
    spots = []
    for level in levels:
        for y in LABEL_ROWS:
            row = values[ys.index(y)]
            hits = [i for i in range(len(xs) - 1) if (row[i] - level) * (row[i + 1] - level) <= 0
                    and row[i] != row[i + 1]]
            if hits and 1 < xs[hits[0]] - PRICE_RANGE[0] and PRICE_RANGE[1] - xs[hits[0]] > 1:
                spots.append((xs[hits[0]], y))
                break
    return spots


def plot_spending(prices: Prices, step: float = 1000):
    """Food spending per semester under each option, in $1,000 bands on one scale, with labelled
    contour lines every $2,000."""
    from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap

    import style

    xs, ys = _axes()
    grid = spending_grid(prices, xs, ys)
    vmax = max(max(max(r) for r in grid[p]) for p in PLANS)
    bounds = [step * i for i in range(int(vmax // step) + 2)]
    cmap = LinearSegmentedColormap.from_list("spend", SEQ5, N=len(bounds) - 1)
    norm = BoundaryNorm(bounds, len(bounds) - 1)
    levels = [b for b in bounds[1:-1] if b % (2 * step) == 0]

    def contours(ax, p, xs, ys):
        cs = ax.contour(xs, ys, grid[p], levels=levels, colors=SURFACE, linewidths=1.0)
        ax.clabel(cs, fmt=lambda v: f"${v / 1000:.0f}k", fontsize=style.TICK, colors=INK, inline=True,
                  inline_spacing=6, manual=_contour_label_spots(grid[p], xs, ys, cs.levels))
        for t in cs.labelTexts:
            t.set_path_effects(_halo())

    ticks = [b for b in bounds if b % (2 * step) == 0]
    return _spending_panels("A plan lowers your food bill only if you use its swipes and meals elsewhere are pricey",
                            grid, cmap, norm, "Total food spending per semester ($1,000 bands)",
                            colorbar_ticks=ticks, colorbar_ticklabels=[f"${t:,.0f}" for t in ticks],
                            decorate=contours)


def extra_cost_grid(prices: Prices, xs, ys):
    """{plan: rows[y][x] of how much more per semester than the cheapest option}."""
    grid = spending_grid(prices, xs, ys)
    best = [[min(grid[p][j][i] for p in PLANS) for i in range(len(xs))] for j in range(len(ys))]
    return {p: [[grid[p][j][i] - best[j][i] for i in range(len(xs))] for j in range(len(ys))] for p in PLANS}


def _outline_cheapest(ax, bands, xs, ys):
    """Outline and label the cells where this option is the cheapest (band 0)."""
    from matplotlib.collections import LineCollection

    import style

    mask = [[b == 0 for b in row] for row in bands]
    ax.add_collection(LineCollection(_region_edges(mask, xs, ys), colors=INK, linewidths=1.6, capstyle="projecting"))
    pts = [(x, y) for row, y in zip(mask, ys) for x, m in zip(xs, row) if m]
    if len(pts) >= 20:
        x, y = _label_point(pts, xs, ys)
        ax.text(x, y, "Cheapest here", ha="center", va="center", fontsize=style.LABEL, color=INK,
                weight="bold", path_effects=_halo())


def _extra_cost_bands(prices: Prices, xs, ys):
    extra = extra_cost_grid(prices, xs, ys)
    return extra, {p: [[extra_cost_band(v) for v in row] for row in extra[p]] for p in PLANS}


def _extra_cost_colorbar(fig, mesh, ax):
    import style

    cbar = fig.colorbar(mesh, ax=ax, location="right", shrink=0.8, aspect=30, pad=0.02)
    cbar.set_label("How much more than the cheapest option, per semester", color=MUTED, fontsize=style.LABEL)
    cbar.set_ticks(list(range(len(SEQ5))), labels=EXTRA_LABELS)
    cbar.ax.tick_params(colors=MUTED, labelsize=style.TICK, length=0)
    cbar.outline.set_visible(False)


def plot_on_campus_extra(prices: Prices):
    """On-campus students: the 21-meal panel of the extra-cost chart on its own. The required
    unlimited plan costs the same as the 21-meal plan, so this is how much more the required plan
    costs than the cheapest of the four options for the same eating habits."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap

    import style

    xs, ys = _axes()
    _, bands = _extra_cost_bands(prices, xs, ys)
    norm = BoundaryNorm([-0.5 + i for i in range(len(SEQ5) + 1)], len(SEQ5))
    fig, ax = plt.subplots(figsize=(12, 7.5), facecolor=SURFACE, layout="constrained")
    _frameless(ax)
    mesh = ax.pcolormesh(_edges(xs), _edges(ys), bands["nr21"], cmap=ListedColormap(SEQ5), norm=norm, shading="flat")
    _outline_cheapest(ax, bands["nr21"], xs, ys)
    _price_axis(ax)
    _eaten_axis(ax)
    ax.set_xlabel(X_LABEL, color=MUTED, fontsize=style.LABEL)
    ax.set_ylabel(Y_LABEL, color=MUTED, fontsize=style.LABEL)
    ax.set_title("On-campus unlimited plan (= 21-meal plan) vs your best option", fontsize=style.PANEL_TITLE,
                 color=INK, loc="left", pad=10)
    _extra_cost_colorbar(fig, mesh, ax)
    t21 = lowest_winning_price("nr21", prices)
    style.title(fig, f"The required on-campus plan only pays off if you eat most meals at HUDS and meals elsewhere "
                     f"would cost over ${t21:.0f}")
    return fig


def plot_extra_cost(prices: Prices):
    """Each option coloured by how much more it costs per semester than the cheapest option, with
    the region where it is the cheapest outlined and labelled."""
    from matplotlib.colors import BoundaryNorm, ListedColormap

    xs, ys = _axes()
    extra, bands = _extra_cost_bands(prices, xs, ys)
    norm = BoundaryNorm([-0.5 + i for i in range(len(SEQ5) + 1)], len(SEQ5))
    worst = max(max(max(r) for r in extra[p]) for p in PLANS)

    def outline(ax, p, xs, ys):
        _outline_cheapest(ax, bands[p], xs, ys)

    return _spending_panels(f"Picking the wrong option can cost up to ${worst:,.0f} a semester",
                            bands, ListedColormap(SEQ5), norm, "How much more than the cheapest option, per semester",
                            colorbar_ticks=list(range(len(SEQ5))), colorbar_ticklabels=EXTRA_LABELS,
                            decorate=outline)


def write_grid_csv(prices: Prices, path, n=75):
    import csv

    xs, _ = _axes(n=n)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hud_meals_per_week", "meals_missed_per_week", "outside_price"]
                   + [f"semester_{p}" for p in PLANS] + ["cheapest", "runner_up_extra_per_year"])
        for eaten in range(FULL_WEEK + 1):
            y = FULL_WEEK - eaten
            for x in xs:
                c = per_semester(year_food_spending(y, x, prices))
                best, gap = cheapest(y, x, prices)
                w.writerow([eaten, y, round(x, 2)] + [round(c[p], 2) for p in PLANS] + [best, round(gap, 2)])
