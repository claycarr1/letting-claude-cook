"""Step 4: decision map -- which plan is cheapest for a student's habits?

A student is described by three habit inputs:
  meals_out          meals eaten away from HUDS per week (0-14)
  breakfasts_skipped breakfasts skipped per week (0-7)
  weekends_away      weekends away from campus per term (0-10)

habits_to_patterns() turns them into weekly eating patterns, every plan in a student
group is run through src/model.py, and recommend() returns the cheapest plan and its
dollar gap to the runner-up. Costs are per academic year (fall + spring with the same
habits), so GradPlus's fall-to-spring rollover and year-end forfeiture are counted.

Assumptions (each needs to go in report.md):
* Start from a full HUDS week: 7 breakfasts, 5 lunches (Mon-Fri), 2 brunches (Sat-Sun),
  7 dinners. Skipped breakfasts come off breakfast. Meals out come off the 14
  non-breakfast meals in proportion (5 lunch : 2 brunch : 7 dinner), so 14 meals out
  means no lunch, brunch or dinner at HUDS.
* A weekend away removes that week's Saturday and Sunday meals: both brunches and 2/7 of
  the week's breakfasts and dinners (skips and meals out are spread evenly over the week).
  Weeks with and without a weekend away are costed separately, so weekly swipe
  forfeiture on the non-resident plans is counted correctly.
* Meals out cost the same whichever plan you hold, so they don't change which plan
  is cheapest and aren't priced here.
* Both terms are WEEKS_PER_TERM weeks long, with the same habits.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from model import (
    Prices,
    WeeklyPattern,
    cost_cash_at_cafe,
    cost_gradplus,
    cost_no_plan,
    cost_non_resident,
    cost_resident_unlimited,
)

WEEKS_PER_TERM = 15
MEALS_OUT_RANGE = (0, 14)
BREAKFASTS_SKIPPED_RANGE = (0, 7)
WEEKENDS_AWAY_RANGE = (0, 10)

PLAN_LABELS = {
    "resident": "Resident unlimited",
    "nr5": "Non-resident 5 meals/wk",
    "nr10": "Non-resident 10 meals/wk",
    "nr21": "Non-resident 21 meals/wk",
    "gp_regular": "GradPlus Regular",
    "gp_deluxe": "GradPlus Deluxe",
    "cash_guest": "No plan (pay guest rates)",
    "cash_cafe": "No plan (pay cash at cafe)",
}

# Which options a student can actually choose between.
GROUPS = {
    # Literal brief: every plan plus the no-plan cash baseline on one map.
    "all": ["resident", "nr5", "nr10", "nr21", "gp_regular", "gp_deluxe", "cash_guest"],
    # Undergrads living off campus: the resident plan isn't available, GradPlus isn't either.
    "undergrad_offcampus": ["nr5", "nr10", "nr21", "cash_guest"],
    # Grad students: GradPlus at HUDS cafes, or pay cash at the same cafes.
    "grad": ["gp_regular", "gp_deluxe", "cash_cafe"],
}


@dataclass(frozen=True)
class Recommendation:
    plan: str
    label: str
    annual_cost: float
    runner_up: str
    runner_up_label: str
    runner_up_cost: float
    gap: float  # runner-up cost minus cheapest cost, USD/year; 0 means a tie
    tied_with: Tuple[str, ...]  # other plans exactly as cheap (to the cent)
    costs: Dict[str, float]  # every plan in the group, USD/year


def _check_range(name: str, value: float, bounds: Tuple[int, int]):
    lo, hi = bounds
    if not lo <= value <= hi:
        raise ValueError(f"{name}={value} is outside {lo}..{hi}")


def habits_to_patterns(meals_out: float, breakfasts_skipped: float) -> Tuple[WeeklyPattern, WeeklyPattern]:
    """Return (normal week, week with a weekend away) as HUDS meals eaten."""
    _check_range("meals_out", meals_out, MEALS_OUT_RANGE)
    _check_range("breakfasts_skipped", breakfasts_skipped, BREAKFASTS_SKIPPED_RANGE)
    keep = 1 - meals_out / 14
    breakfast = 7 - breakfasts_skipped
    normal = WeeklyPattern(breakfast=breakfast, lunch=5 * keep, brunch=2 * keep, dinner=7 * keep)
    away = WeeklyPattern(breakfast=breakfast * 5 / 7, lunch=5 * keep, brunch=0, dinner=7 * keep * 5 / 7)
    return normal, away


def _average(normal: WeeklyPattern, away: WeeklyPattern, weeks: float, weeks_away: float) -> WeeklyPattern:
    w = weeks_away / weeks
    # Rounded so float noise can't push a count past HUDS's weekly maximum (e.g. 5.000000000000001).
    return WeeklyPattern(**{m: round(getattr(normal, m) * (1 - w) + getattr(away, m) * w, 9)
                            for m in ("breakfast", "lunch", "brunch", "dinner")})


def annual_costs(meals_out: float, breakfasts_skipped: float, weekends_away: float, prices: Prices,
                 plans: Optional[List[str]] = None, weeks_per_term: float = WEEKS_PER_TERM,
                 cafe_meal_price: Optional[float] = None) -> Dict[str, float]:
    """Cost per academic year (USD) of each plan for these habits."""
    _check_range("weekends_away", weekends_away, WEEKENDS_AWAY_RANGE)
    if weekends_away >= weeks_per_term:
        raise ValueError("need at least one week on campus per term")
    plans = plans or GROUPS["all"]
    normal, away = habits_to_patterns(meals_out, breakfasts_skipped)
    home_weeks = weeks_per_term - weekends_away

    def per_term(cost_fn) -> float:
        # The plan charge is counted once; the cash for meals outside the plan in each kind of
        # week is added up. Valid for every plan whose balance resets weekly or never.
        r = cost_fn(normal, home_weeks)
        term = r.plan_charge - r.credits + r.extra_cash
        if weekends_away:
            term += cost_fn(away, weekends_away).extra_cash
        return term

    def gradplus_year(tier: str) -> float:
        # GradPlus spends one balance over the whole term, so the averaged pattern is exact.
        avg = _average(normal, away, weeks_per_term, weekends_away)
        fall = cost_gradplus(avg, weeks_per_term, prices, tier, "fall", cafe_meal_price=cafe_meal_price)
        spring = cost_gradplus(avg, weeks_per_term, prices, tier, "spring", carry_in=fall.carry_out,
                               cafe_meal_price=cafe_meal_price)
        return fall.total_cost + spring.total_cost

    calc = {
        "resident": lambda: 2 * per_term(lambda p, w: cost_resident_unlimited(p, w, prices)),
        "nr5": lambda: 2 * per_term(lambda p, w: cost_non_resident(p, w, prices, 5)),
        "nr10": lambda: 2 * per_term(lambda p, w: cost_non_resident(p, w, prices, 10)),
        "nr21": lambda: 2 * per_term(lambda p, w: cost_non_resident(p, w, prices, 21)),
        "cash_guest": lambda: 2 * per_term(lambda p, w: cost_no_plan(p, w, prices)),
        "cash_cafe": lambda: 2 * per_term(lambda p, w: cost_cash_at_cafe(p, w, cafe_meal_price)),
        "gp_regular": lambda: gradplus_year("regular"),
        "gp_deluxe": lambda: gradplus_year("deluxe"),
    }
    return {plan: round(calc[plan](), 2) for plan in plans}


def recommend(meals_out: float, breakfasts_skipped: float, weekends_away: float, prices: Prices,
              group: str = "all", **kw) -> Recommendation:
    """The cheapest plan in `group` for these habits, and how much more the runner-up costs per year."""
    if group not in GROUPS:
        raise ValueError(f"group must be one of {sorted(GROUPS)}")
    costs = annual_costs(meals_out, breakfasts_skipped, weekends_away, prices, GROUPS[group], **kw)
    order = GROUPS[group]
    ranked = sorted(costs, key=lambda p: (costs[p], order.index(p)))  # ties broken by group order
    best, second = ranked[0], ranked[1]
    return Recommendation(
        plan=best, label=PLAN_LABELS[best], annual_cost=costs[best],
        runner_up=second, runner_up_label=PLAN_LABELS[second], runner_up_cost=costs[second],
        gap=round(costs[second] - costs[best], 2),
        tied_with=tuple(p for p in ranked[1:] if costs[p] == costs[best]),
        costs=costs,
    )


# ---------------------------------------------------------------------------- plotting
# Colour encodes the kind of option, consistently across every map: blue = pay cash,
# aqua = the smaller plan of a family, orange = the larger one. These are the first three
# slots of the dataviz reference palette, which pass the all-pairs colour-blindness checks.
# Plans that win nowhere under the current prices get fallback colours and are flagged.
SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
PLAN_COLORS = {
    "cash_guest": "#2a78d6", "cash_cafe": "#2a78d6",
    "nr5": "#1baf7a", "gp_regular": "#1baf7a",
    "nr21": "#eb6834", "gp_deluxe": "#eb6834",
    "nr10": "#eda100", "resident": "#4a3aa7",  # fallbacks: neither wins anywhere at 2026-27 prices
}
SHORT_LABELS = {
    "resident": "Resident", "nr5": "NR 5", "nr10": "NR 10", "nr21": "NR 21",
    "gp_regular": "GP Reg", "gp_deluxe": "GP Deluxe", "cash_guest": "Cash", "cash_cafe": "Cash",
}
GROUP_TITLES = {
    "all": "Every plan on one map (as specified in the brief)",
    "undergrad_offcampus": "Undergraduates living off campus",
    "grad": "Graduate students",
}


def grid(weekends_away: int, prices: Prices, group: str, **kw) -> List[List[Recommendation]]:
    """recommend() for every (breakfasts_skipped, meals_out) cell, rows = breakfasts skipped."""
    return [[recommend(mo, bs, weekends_away, prices, group, **kw) for mo in range(MEALS_OUT_RANGE[1] + 1)]
            for bs in range(BREAKFASTS_SKIPPED_RANGE[1] + 1)]


def _draw_panel(ax, cells: List[List[Recommendation]], plans: List[str], title: str,
                avoid: Tuple[Tuple[float, float], ...] = ()):
    from matplotlib import patheffects
    from matplotlib.colors import ListedColormap

    index = {p: i for i, p in enumerate(plans)}
    codes = [[index[c.plan] for c in row] for row in cells]
    cmap = ListedColormap([PLAN_COLORS[p] for p in plans])
    ax.pcolormesh(range(MEALS_OUT_RANGE[1] + 2), range(BREAKFASTS_SKIPPED_RANGE[1] + 2), codes,
                  cmap=cmap, vmin=-0.5, vmax=len(plans) - 0.5, edgecolors=SURFACE, linewidth=0.6)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xticks([x + 0.5 for x in range(0, 15, 2)], [str(x) for x in range(0, 15, 2)])
    ax.set_yticks([y + 0.5 for y in range(8)], [str(y) for y in range(8)])
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_aspect("equal")
    # Direct label in each region big enough to hold one (colour is never the only cue). Largest
    # regions first; a label that would crowd an earlier label or an `avoid` point is skipped --
    # the legend still names every colour.
    regions = {plan: [(mo + 0.5, bs + 0.5) for bs, row in enumerate(cells) for mo, c in enumerate(row)
                      if c.plan == plan] for plan in plans}
    placed = list(avoid)
    for plan in sorted(plans, key=lambda q: -len(regions[q])):
        pts = regions[plan]
        if len(pts) < 4:
            continue
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        # Put the label on the region's most interior cell (most same-plan neighbours), nearest the
        # centroid, and keep it clear of the panel edge so it can't run into the tick labels.
        own = set(pts)
        def interior(pt):
            return sum((pt[0] + dx, pt[1] + dy) in own for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        x, y = max(pts, key=lambda p: (interior(p), -((p[0] - cx) ** 2 + (p[1] - cy) ** 2)))
        x = min(max(x, 1.4), MEALS_OUT_RANGE[1] - 0.4)
        if any(abs(x - px) < 3.5 and abs(y - py) < 1.5 for px, py in placed):
            continue
        placed.append((x, y))
        ax.text(x, y, SHORT_LABELS[plan], ha="center", va="center", fontsize=8, color=INK,
                path_effects=[patheffects.withStroke(linewidth=2.5, foreground=SURFACE)])


def _legend(ax, plans: List[str], shown: set, note_xy: Tuple[float, float] = (0.0, 0.5), **kw):
    """Legend of the options that win somewhere; the rest are listed as text, not given a swatch."""
    from matplotlib.patches import Patch

    handles = [Patch(facecolor=PLAN_COLORS[p], edgecolor="none", label=f"{SHORT_LABELS[p]}: {PLAN_LABELS[p]}")
               for p in plans if p in shown]
    never = [PLAN_LABELS[p] for p in plans if p not in shown]
    kw = {"loc": "center left", **kw}
    leg = ax.legend(handles=handles, frameon=False, fontsize=9, labelcolor=INK,
                    title="Cheapest option", title_fontsize=10, alignment="left", **kw)
    if never:
        ax.text(note_xy[0], note_xy[1] - 0.05 * (len(handles) + 2), "Never cheapest:\n" + "\n".join(never),
                transform=ax.transAxes, fontsize=8.5, color=MUTED, va="top")
    return leg


def plot_decision_map(prices: Prices, group: str, weekends_levels=range(WEEKENDS_AWAY_RANGE[1] + 1), **kw):
    """Small multiples: one panel per weekends-away level, cells coloured by the cheapest plan."""
    import matplotlib.pyplot as plt

    plans = GROUPS[group]
    levels = list(weekends_levels)
    ncols = 4
    nrows = -(-(len(levels) + 1) // ncols)  # +1 for the legend panel
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 2.9 * nrows + 1.2), facecolor=SURFACE,
                             layout="constrained")
    axes = axes.ravel()
    shown = set()
    for ax, w in zip(axes, levels):
        cells = grid(w, prices, group, **kw)
        shown |= {c.plan for row in cells for c in row}
        _draw_panel(ax, cells, plans, f"{w} weekend{'s' if w != 1 else ''} away per term")
    for ax in axes[len(levels):]:
        ax.axis("off")
    _legend(axes[len(levels)], plans, shown)
    fig.supxlabel("Meals out per week (lunch, brunch or dinner not eaten at HUDS)", color=MUTED, fontsize=10)
    fig.supylabel("Breakfasts skipped per week", color=MUTED, fontsize=10)
    fig.suptitle(f"Decision map: {GROUP_TITLES[group]}\nCheapest option per academic year, 2026-27 prices",
                 color=INK, fontsize=13, x=0.01, ha="left")
    return fig


def plot_you_are_here(meals_out: float, breakfasts_skipped: float, weekends_away: int, prices: Prices,
                      group: str, **kw):
    """One map panel at the student's weekends-away level, with a dot at their habits and the answer."""
    import matplotlib.pyplot as plt

    plans = GROUPS[group]
    rec = recommend(meals_out, breakfasts_skipped, weekends_away, prices, group, **kw)
    cells = grid(weekends_away, prices, group, **kw)
    fig, ax = plt.subplots(figsize=(11, 5.6), facecolor=SURFACE, layout="constrained")
    dot = (meals_out + 0.5, breakfasts_skipped + 0.5)
    _draw_panel(ax, cells, plans, f"{GROUP_TITLES[group]}, {weekends_away} weekends away per term",
                avoid=(dot, (dot[0], dot[1] + 1)))
    ax.plot(meals_out + 0.5, breakfasts_skipped + 0.5, "o", markersize=13, color=INK,
            markeredgecolor=SURFACE, markeredgewidth=2.5, zorder=5)
    ax.annotate("You are here", (meals_out + 0.5, breakfasts_skipped + 0.5), xytext=(0, 14),
                textcoords="offset points", ha="center", fontsize=9, color=INK, weight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none"))
    ax.set_xlabel("Meals out per week", color=MUTED)
    ax.set_ylabel("Breakfasts skipped per week", color=MUTED)
    # "\$" because matplotlib reads a pair of bare $ signs as maths notation.
    gap = "tied with" if rec.gap == 0 else f"\\${rec.gap:,.2f}/yr cheaper than"
    fig.suptitle(f"Cheapest for you: {rec.label} (\\${rec.annual_cost:,.2f}/yr), {gap} {rec.runner_up_label}",
                 color=INK, fontsize=11, x=0.02, ha="left")
    _legend(ax, plans, {c.plan for row in cells for c in row}, loc="upper left", bbox_to_anchor=(1.03, 1),
            note_xy=(1.04, 1.0))
    return fig
