"""Supporting charts for the report: savings vs no plan, cost per swipe, the gap map and the
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
from model import (
    CAFE_MEAL_PRICE_ESTIMATE,
    MAX_PER_WEEK,
    Prices,
    WeeklyPattern,
    cost_gradplus,
    load_term_weeks,
)

FULL_WEEK = sum(MAX_PER_WEEK.values())  # 21
OFF_CAMPUS = GROUPS["undergrad_offcampus"]
GRID_COLOR, AXIS_COLOR = "#e1e0d9", "#c3c2b7"


# ---------------------------------------------------------------------------- 1. savings vs no plan

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


def savings_vs_no_plan(meals_per_week: float, prices: Prices, weekends_away: int = 2,
                       plans: List[str] = ("nr5", "nr10", "nr21")) -> Dict[str, float]:
    """Yearly saving of each plan compared with no plan (paying guest rates). Positive = the plan saves money."""
    c = yearly_costs(meals_per_week, prices, weekends_away, list(plans) + ["cash_guest"])
    return {p: c["cash_guest"] - c[p] for p in plans}


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS_COLOR)


def _spread_labels(ys: List[float], min_gap: float) -> List[float]:
    """Nudge label positions apart so none are closer than min_gap, keeping their order. Each group
    of labels that had to move is re-centred on its original positions, so it spreads both ways."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    groups = [[order[0]]]
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < min_gap:
            out[b] = out[a] + min_gap
            groups[-1].append(b)
        else:
            groups.append([b])
    for g in groups:
        shift = sum(ys[i] for i in g) / len(g) - sum(out[i] for i in g) / len(g)
        for i in g:
            out[i] += shift
    return out


# Label text in each line's colour; the yellow is darkened so it stays readable on the light surface.
LABEL_INK = {"nr10": "#9a6a00"}


def plot_savings(prices: Prices, weekends_away: int = 2):
    import matplotlib.pyplot as plt

    plans = ["nr5", "nr10", "nr21"]
    xs = [i * 0.25 for i in range(int(FULL_WEEK / 0.25) + 1)]
    curves = {p: [] for p in plans}
    for x in xs:
        s = savings_vs_no_plan(x, prices, weekends_away, plans)
        for p in plans:
            curves[p].append(s[p])
    y_min = -3500

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=SURFACE, layout="constrained")
    _style(ax)
    ax.axhline(0, color=PLAN_COLORS["cash_guest"], linewidth=2, zorder=3)
    for p in plans:
        ax.plot(xs, curves[p], color=PLAN_COLORS[p], linewidth=2, zorder=4)

    ends = [curves[p][-1] for p in plans] + [0.0]
    names = plans + ["cash_guest"]
    for name, y_end, y in zip(names, ends, _spread_labels(ends, min_gap=260)):
        ax.text(FULL_WEEK + 0.3, y, SHORT_LABELS[name], va="center", fontsize=10, weight="bold",
                color=LABEL_INK.get(name, PLAN_COLORS[name]))
    ax.text(0.3, 120, "Above $0: the plan saves money", fontsize=9, color=MUTED, va="bottom")
    # Bottom-left corner, under the 5-meal line and left of where the other plans enter the chart.
    ax.text(0.3, y_min + 150, "Below $0: the plan costs more", fontsize=9, color=MUTED, va="bottom")

    ax.set_xlim(0, FULL_WEEK)
    ax.set_ylim(y_min, max(max(c) for c in curves.values()) + 400)
    ax.set_xticks(range(0, FULL_WEEK + 1, 3))
    ax.set_xlabel("Meals eaten at HUDS per week", color=MUTED)
    ax.set_ylabel("How much cheaper than paying at the door (per year)", color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}")
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    fig.suptitle("How much each plan saves compared to no plan", color=INK, fontsize=12, x=0.01, ha="left")
    ax.set_title(f"Off-campus undergraduate, {weekends_away} weekends away per term, every meal type cut evenly. "
                 f"Lines below -${-y_min:,} are cut off.", color=MUTED, fontsize=9, loc="left")
    return fig


# ---------------------------------------------------------------------------- 2. cost per swipe

def cost_per_swipe(prices: Prices, term_weeks: Optional[Dict[str, float]] = None) -> Dict[int, float]:
    """Yearly plan price / swipes available in a year, assuming every swipe is used."""
    weeks = sum((term_weeks or load_term_weeks()).values())
    return {n: 2 * price / (n * weeks) for n, price in sorted(prices.non_resident_per_term.items())}


def plot_swipe_cost(prices: Prices):
    """One swipe on each off-campus plan next to the three outside prices (cooking, cheap takeout,
    sit-down). Imported lazily: outside_food imports this module."""
    import matplotlib.pyplot as plt

    from outside_food import PLACEHOLDER_MARKERS, PRICE_MARKERS, marker_price_text

    swipes = cost_per_swipe(prices)
    plans = {5: "nr5", 10: "nr10", 21: "nr21"}
    names = {5: "5-meal plan", 10: "10-meal plan", 21: "21-meal plan\n(= on-campus plan)"}
    bars = [(f"{names[n]}\n(one swipe)", v, PLAN_COLORS[plans[n]]) for n, v in swipes.items()]
    neutral = "#898781"
    notes = {"Cooking": "(USDA moderate plan)"}
    bars += [(f"{name}\n{notes.get(name, '(placeholder)')}", price, neutral) for name, price in PRICE_MARKERS]
    value_text = {i + 3: marker_price_text(name, price) for i, (name, price) in enumerate(PRICE_MARKERS)}

    from matplotlib import patheffects

    halo = [patheffects.withStroke(linewidth=3, foreground=SURFACE)]
    import style

    fig, ax = plt.subplots(figsize=(14, 7), facecolor=SURFACE, layout="constrained")
    _style(ax)
    ax.tick_params(labelsize=style.TICK)
    xs = [i + (0.6 if i >= 3 else 0) for i in range(len(bars))]  # gap between plans and outside prices
    right = xs[-1] + 0.5
    for i, (x, (label, value, color)) in enumerate(zip(xs, bars)):
        placeholder = i >= 3 and PRICE_MARKERS[i - 3][0] in PLACEHOLDER_MARKERS
        ax.bar(x, value, width=0.62, color=color, zorder=3, hatch="//" if placeholder else None,
               edgecolor=SURFACE, linewidth=0)
        ax.text(x, value + 0.4, value_text.get(i, f"${value:.2f}"), ha="center", va="bottom", fontsize=style.TICK, color=INK,
                path_effects=halo, zorder=5)
    # Dashed line at each plan's swipe cost, running across the outside prices for comparison.
    label_ys = _spread_labels([swipes[n] for n in plans], min_gap=1.2)
    for (n, plan), y_label in zip(plans.items(), label_ys):
        ax.plot([xs[0] - 0.4, right], [swipes[n]] * 2, color=PLAN_COLORS[plan], linewidth=1.5,
                linestyle=(0, (5, 3)), zorder=4)
        ax.text(right + 0.1, y_label, "21-meal / on-campus\nswipe" if n == 21 else f"{n}-meal swipe", va="center", fontsize=style.TICK, weight="bold",
                color=LABEL_INK.get(plan, PLAN_COLORS[plan]))
    ax.set_xlim(xs[0] - 0.5, right + 1.6)
    ax.set_xticks(xs, [b[0] for b in bars], fontsize=style.TICK, color=INK)
    ax.set_ylabel("Cost of one meal (USD)", color=MUTED, fontsize=style.LABEL)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_ylim(0, max(b[1] for b in bars) * 1.15)
    ax.text(1, -0.17, "Meal plans", transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=style.LABEL, color=MUTED)
    ax.text(sum(xs[3:]) / len(xs[3:]), -0.17, "Meals not eaten at HUDS (hatched = placeholder price)",
            transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=style.LABEL, color=MUTED)
    cook = dict(PRICE_MARKERS)["Cooking"]
    style.title(fig, f"Cooking (${cook:.2f} a meal) is cheaper than any swipe; a plan only pays off against "
                     f"meals out that cost more than ${swipes[21]:.2f} (21-meal / on-campus) or about "
                     f"${(swipes[5] + swipes[10]) / 2:.0f} (5- and 10-meal)")
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


def plot_gap_map(prices: Prices, group: str = "undergrad_offcampus", weekends_away: int = 2):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    from decision_map import GROUP_TITLES, _label_regions

    fig, ax = plt.subplots(figsize=(11, 5.6), facecolor=SURFACE, layout="constrained")
    nx, ny = MEALS_OUT_RANGE[1] + 1, BREAKFASTS_SKIPPED_RANGE[1] + 1
    cells = grid(weekends_away, prices, group)
    for bs in range(ny):
        for mo in range(nx):
            ax.add_patch(Rectangle((mo, bs), 1, 1, facecolor=GAP_COLORS[gap_bin(cells[bs][mo].gap)],
                                   edgecolor=SURFACE, linewidth=0.8))
    # Dark lines where the cheapest option changes, so the plan regions stay visible.
    for bs in range(ny):
        for mo in range(nx):
            if mo + 1 < nx and cells[bs][mo].plan != cells[bs][mo + 1].plan:
                ax.plot([mo + 1, mo + 1], [bs, bs + 1], color=INK, linewidth=2, solid_capstyle="butt")
            if bs + 1 < ny and cells[bs][mo].plan != cells[bs + 1][mo].plan:
                ax.plot([mo, mo + 1], [bs + 1, bs + 1], color=INK, linewidth=2, solid_capstyle="butt")
    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)
    ax.set_aspect("equal")
    ax.set_xticks([x + 0.5 for x in range(nx)], [str(x) for x in range(nx)])
    ax.set_yticks([y + 0.5 for y in range(ny)], [str(y) for y in range(ny)])
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    _label_regions(ax, cells, GROUPS[group], fontsize=10, min_cells=3)
    ax.set_xlabel(X_LABEL, color=MUTED)
    ax.set_ylabel(Y_LABEL, color=MUTED)
    handles = [Patch(facecolor=c, label=_bin_label(lo, hi)) for (lo, hi), c in zip(GAP_BINS, GAP_COLORS)]
    handles.append(Patch(facecolor=SURFACE, edgecolor=INK, linewidth=2, label="Boundary between plans"))
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.03, 1), frameon=False, fontsize=9,
              labelcolor=INK, title="Saving vs the runner-up, per year", title_fontsize=10, alignment="left")
    fig.suptitle(f"How much the cheapest option saves: {GROUP_TITLES[group].lower()}", color=INK, fontsize=12,
                 x=0.01, ha="left")
    ax.set_title(f"{weekends_away} weekends away per term. Dollar gap per year between the cheapest and second-cheapest "
                 "option, 2026-27 prices.", color=MUTED, fontsize=9, loc="left")
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


def plot_assumption_effects(summary: dict, x_max: float = 15):
    import matplotlib.pyplot as plt

    effects = assumption_effects(summary["agreement_by_assumption"])
    fig, ax = plt.subplots(figsize=(9, 4), facecolor=SURFACE, layout="constrained")
    _style(ax)
    ys = list(range(len(effects)))[::-1]
    for y, e in zip(ys, effects):
        ax.barh(y, e["effect_pp"], height=0.55, color="#2a78d6", zorder=3)
        ax.text(e["effect_pp"] + 0.2, y, f"{e['effect_pp']:.1f}", va="center", fontsize=10, color=INK)
    ax.set_yticks(ys, [e["assumption"] for e in effects], color=INK)
    ax.set_xlim(0, x_max)
    ax.set_xlabel("How much this changes the answer (percentage points)", color=MUTED)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8)
    fig.suptitle("Which assumption changes the off-campus map most?", color=INK, fontsize=12, x=0.01, ha="left")
    ax.set_title(f"Monte Carlo, {summary['runs']:,} runs", color=MUTED, fontsize=9, loc="left")
    return fig


# ---------------------------------------------------------------------------- 5. grad students: cafe spending

GRAD_OPTIONS = ["cash_cafe", "gp_regular", "gp_deluxe"]


def grad_year_costs(spending: float, prices: Prices, term_weeks: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """What a grad student actually pays in a year under each option, if they would spend `spending`
    a year at HUDS cafes at menu prices, evenly across the weeks of both terms.

    The answer doesn't depend on the cafe meal price: it only converts spending into meals and back.
    """
    term_weeks = term_weeks or load_term_weeks()
    price = CAFE_MEAL_PRICE_ESTIMATE
    meals = spending / (price * sum(term_weeks.values()))
    if meals > FULL_WEEK:
        raise ValueError("spending is more than 21 cafe meals a week")
    pattern = WeeklyPattern(**{m: n * meals / FULL_WEEK for m, n in MAX_PER_WEEK.items()})
    out = {"cash_cafe": float(spending)}
    for tier in ("regular", "deluxe"):
        fall = cost_gradplus(pattern, term_weeks["fall"], prices, tier, "fall", cafe_meal_price=price)
        spring = cost_gradplus(pattern, term_weeks["spring"], prices, tier, "spring", carry_in=fall.carry_out,
                               cafe_meal_price=price)
        out[f"gp_{tier}"] = fall.total_cost + spring.total_cost
    return out


def grad_switch_points(prices: Prices, max_spending: float = 3000, step: float = 5) -> List[Tuple[float, str, str]]:
    """Yearly cafe spending at which the cheapest grad option changes: [(spending, below, above)]."""
    def cheapest(s):
        c = grad_year_costs(s, prices)
        return min(GRAD_OPTIONS, key=lambda o: (c[o], GRAD_OPTIONS.index(o)))

    points, prev_s, prev = [], 0.0, cheapest(0.0)
    s = step
    while s <= max_spending:
        cur = cheapest(s)
        if cur != prev:
            lo, hi = prev_s, s
            for _ in range(40):
                mid = (lo + hi) / 2
                c = grad_year_costs(mid, prices)
                lo, hi = (mid, hi) if c[prev] < c[cur] else (lo, mid)
            points.append(((lo + hi) / 2, prev, cur))
        prev_s, prev = s, cur
        s += step
    return points


def plot_grad_spending(prices: Prices, max_spending: float = 2500):
    import matplotlib.pyplot as plt
    from matplotlib import patheffects

    points = grad_switch_points(prices, max_spending)
    edges = [0.0] + [s for s, _, _ in points] + [max_spending]
    options = [points[0][1]] + [above for _, _, above in points] if points else ["cash_cafe"]
    names = {"cash_cafe": "No plan", "gp_regular": "GradPlus Regular", "gp_deluxe": "GradPlus Deluxe"}

    import style

    fig, ax = plt.subplots(figsize=(13, 4.2), facecolor=SURFACE, layout="constrained")
    ax.set_facecolor(SURFACE)
    halo = [patheffects.withStroke(linewidth=3, foreground=SURFACE)]
    for (lo, hi), opt in zip(zip(edges, edges[1:]), options):
        ax.barh(0, hi - lo, left=lo, height=0.6, color=PLAN_COLORS[opt], edgecolor=SURFACE, linewidth=2)
        ax.text((lo + hi) / 2, 0, names[opt], ha="center", va="center", fontsize=style.LABEL + 1, color=INK,
                weight="bold", path_effects=halo)
    for s, below, above in points:
        ax.plot([s, s], [-0.42, 0.42], color=INK, linewidth=1.5)
        ax.text(s, 0.48, f"${s:,.0f}", ha="center", va="bottom", fontsize=style.LABEL, color=INK)
    ax.set_xlim(0, max_spending)
    ax.set_ylim(-0.5, 0.75)
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.tick_params(colors=MUTED, length=0, labelsize=style.TICK)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS_COLOR)
    ax.set_xlabel("What you would spend at HUDS cafés in a year, at menu prices", color=MUTED, fontsize=style.LABEL)
    if points:
        style.title(fig, f"Graduate students: GradPlus only pays off if you would spend over ${points[0][0]:,.0f} "
                         "a year at HUDS cafés")
    return fig


# ---------------------------------------------------------------------------- 6. which meals you skip

MEAL_TYPE_LINES = {  # name -> (how annual_costs is called for x meals of that type skipped, colour)
    "breakfasts": ("Skipping breakfasts", "#e87ba4"),
    "lunches": ("Skipping lunches or brunches", "#008300"),
    "dinners": ("Skipping dinners", "#4a3aa7"),
}


def meal_type_savings(skipped: float, meal_type: str, prices: Prices, weekends_away: int = 2) -> float:
    """How much cheaper the 5-meal plan is than no plan per year, for a student who eats every
    HUDS meal except `skipped` meals a week of one type (lunches: weekday lunches, then brunches)."""
    if meal_type == "breakfasts":
        kw = dict(meals_out=0, breakfasts_skipped=skipped)
    elif meal_type == "lunches":
        kw = dict(meals_out=skipped, breakfasts_skipped=0, meals_out_from="lunches_first")
    elif meal_type == "dinners":
        kw = dict(meals_out=skipped, breakfasts_skipped=0, meals_out_from="dinners_first")
    else:
        raise ValueError(f"meal_type must be one of {list(MEAL_TYPE_LINES)}")
    if not 0 <= skipped <= 7:
        raise ValueError("skipped must be 0..7")
    extra = {"meals_out_from": kw.pop("meals_out_from")} if "meals_out_from" in kw else {}
    c = annual_costs(kw["meals_out"], kw["breakfasts_skipped"], weekends_away, prices, ["nr5", "cash_guest"], **extra)
    return c["cash_guest"] - c["nr5"]


def plot_meal_type_savings(prices: Prices, weekends_away: int = 2):
    import matplotlib.pyplot as plt

    xs = [i * 0.25 for i in range(29)]
    fig, ax = plt.subplots(figsize=(10, 5.8), facecolor=SURFACE, layout="constrained")
    _style(ax)
    ax.axhline(0, color=AXIS_COLOR, linewidth=1.2, zorder=2)
    curves = {k: [meal_type_savings(x, k, prices, weekends_away) for x in xs] for k in MEAL_TYPE_LINES}
    # Breakfasts and lunches give the same line, so the second is drawn dashed on top of the first.
    styles = {"breakfasts": dict(linewidth=4, linestyle="-"), "lunches": dict(linewidth=2, linestyle=(0, (5, 3))),
              "dinners": dict(linewidth=2.5, linestyle="-")}
    for k, (label, color) in MEAL_TYPE_LINES.items():
        ax.plot(xs, curves[k], color=color, zorder=3, **styles[k])
    ends = [curves[k][-1] for k in MEAL_TYPE_LINES]
    for (k, (label, color)), y in zip(MEAL_TYPE_LINES.items(), _spread_labels(ends, min_gap=45)):
        ax.text(7.12, y, label, va="center", fontsize=10, weight="bold", color=color if k != "breakfasts" else "#b8467a")
    ax.text(0.08, 10, "Above $0: the 5-meal plan is cheaper", fontsize=9, color=MUTED, va="bottom")
    ax.text(0.08, -10, "Below $0: paying at the door is cheaper", fontsize=9, color=MUTED, va="top")
    ax.set_xlim(0, 7)
    ax.set_xlabel("Meals of that type skipped (or eaten elsewhere) per week", color=MUTED)
    ax.set_ylabel("How much cheaper the 5-meal plan is (per year)", color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}")
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    fig.suptitle("Skipping dinners is what makes the 5-meal plan lose to paying at the door", color=INK, fontsize=12,
                 x=0.01, ha="left")
    ax.set_title(f"Off-campus undergraduate who eats every other meal at HUDS (all 21 a week except the ones skipped), "
                 f"{weekends_away} weekends away per term.\nThe plan's swipes go on dinners first, so skipping "
                 "breakfasts or lunches saves the same on both options; skipping dinners does not.\n"
                 "Compares only the 5-meal plan with no plan.",
                 color=MUTED, fontsize=9, loc="left")
    return fig
