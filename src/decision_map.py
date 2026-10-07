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
  7 dinners. Skipped breakfasts come off breakfast. By default meals out come off the 14
  non-breakfast meals in proportion (5 lunch : 2 brunch : 7 dinner), so 14 meals out
  means no lunch, brunch or dinner at HUDS. meals_out_from="dinners_first" instead takes
  them off dinners until none are left, then off lunches and brunches in proportion.
* A weekend away removes that week's Saturday and Sunday meals: both brunches and 2/7 of
  the week's breakfasts and dinners (skips and meals out are spread evenly over the week).
  Weeks with and without a weekend away are costed separately, so weekly swipe
  forfeiture on the non-resident plans is counted correctly.
* Meals out cost the same whichever plan you hold, so they don't change which plan
  is cheapest and aren't priced here.
* Term lengths come from the CSV term dates (model.load_term_weeks): fall 15.57 weeks,
  spring 14.86 (one spring-break week removed). Same habits in both terms. A short first
  week counts as a fraction of a week, with that fraction of the weekly meals and, by
  default, of the weekly swipes (full_first_week_swipes=True gives it a full allowance).
* Breakfast is priced at the House guest rate unless breakfast_venue="annenberg_quincy".
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
    load_first_week_fractions,
    load_term_weeks,
)

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


MEALS_OUT_FROM = ("spread", "dinners_first")


def habits_to_patterns(meals_out: float, breakfasts_skipped: float,
                       meals_out_from: str = "spread") -> Tuple[WeeklyPattern, WeeklyPattern]:
    """Return (normal week, week with a weekend away) as HUDS meals eaten."""
    _check_range("meals_out", meals_out, MEALS_OUT_RANGE)
    _check_range("breakfasts_skipped", breakfasts_skipped, BREAKFASTS_SKIPPED_RANGE)
    if meals_out_from == "spread":
        keep = 1 - meals_out / 14
        lunch, brunch, dinner = 5 * keep, 2 * keep, 7 * keep
    elif meals_out_from == "dinners_first":
        dinner = 7 - min(meals_out, 7)
        keep = 1 - max(meals_out - 7, 0) / 7  # share of lunches and brunches still eaten at HUDS
        lunch, brunch = 5 * keep, 2 * keep
    else:
        raise ValueError(f"meals_out_from must be one of {MEALS_OUT_FROM}")
    breakfast = 7 - breakfasts_skipped
    normal = WeeklyPattern(breakfast=breakfast, lunch=lunch, brunch=brunch, dinner=dinner)
    away = WeeklyPattern(breakfast=breakfast * 5 / 7, lunch=lunch, brunch=0, dinner=dinner * 5 / 7)
    return normal, away


def _average(normal: WeeklyPattern, away: WeeklyPattern, weeks: float, weeks_away: float) -> WeeklyPattern:
    w = weeks_away / weeks
    # Rounded so float noise can't push a count past HUDS's weekly maximum (e.g. 5.000000000000001).
    return WeeklyPattern(**{m: round(getattr(normal, m) * (1 - w) + getattr(away, m) * w, 9)
                            for m in ("breakfast", "lunch", "brunch", "dinner")})


def annual_costs(meals_out: float, breakfasts_skipped: float, weekends_away: float, prices: Prices,
                 plans: Optional[List[str]] = None, term_weeks: Optional[Dict[str, float]] = None,
                 cafe_meal_price: Optional[float] = None, meals_out_from: str = "spread",
                 breakfast_venue: str = "houses", full_first_week_swipes: bool = False) -> Dict[str, float]:
    """Cost per academic year (USD) of each plan for these habits.

    term_weeks gives the weeks of dining in each term, e.g. {"fall": 15.57, "spring": 14.86};
    by default it comes from the term dates in data/huds_prices.csv (model.load_term_weeks).
    The short first week of each term (model.load_first_week_fractions) is a home week.
    """
    _check_range("weekends_away", weekends_away, WEEKENDS_AWAY_RANGE)
    term_weeks = term_weeks or load_term_weeks()
    if any(weekends_away >= w for w in term_weeks.values()):
        raise ValueError("need at least one week on campus per term")
    plans = plans or GROUPS["all"]
    normal, away = habits_to_patterns(meals_out, breakfasts_skipped, meals_out_from)
    first_week = load_first_week_fractions()

    def year(cost_fn) -> float:
        # Per term, the plan charge is counted once and the cash for meals outside the plan in
        # each kind of week is added up. Valid for every plan whose balance resets weekly or never.
        # cost_fn(pattern, weeks, first_week_fraction) -- only swipe plans use the last argument.
        total = 0.0
        for term, weeks in term_weeks.items():
            r = cost_fn(normal, weeks - weekends_away, first_week[term])
            total += r.plan_charge - r.credits + r.extra_cash
            if weekends_away:
                total += cost_fn(away, weekends_away, 0.0).extra_cash
        return total

    def non_resident(n):
        return lambda p, w, f: cost_non_resident(p, w, prices, n, breakfast_venue, first_week_fraction=f,
                                                 full_first_week_swipes=full_first_week_swipes)

    def gradplus_year(tier: str) -> float:
        # GradPlus spends one balance over the whole term, so the averaged pattern is exact.
        fall_w, spring_w = term_weeks["fall"], term_weeks["spring"]
        fall = cost_gradplus(_average(normal, away, fall_w, weekends_away), fall_w, prices, tier, "fall",
                             cafe_meal_price=cafe_meal_price)
        spring = cost_gradplus(_average(normal, away, spring_w, weekends_away), spring_w, prices, tier, "spring",
                               carry_in=fall.carry_out, cafe_meal_price=cafe_meal_price)
        return fall.total_cost + spring.total_cost

    calc = {
        "resident": lambda: year(lambda p, w, f: cost_resident_unlimited(p, w, prices)),
        "nr5": lambda: year(non_resident(5)),
        "nr10": lambda: year(non_resident(10)),
        "nr21": lambda: year(non_resident(21)),
        "cash_guest": lambda: year(lambda p, w, f: cost_no_plan(p, w, prices, breakfast_venue)),
        "cash_cafe": lambda: year(lambda p, w, f: cost_cash_at_cafe(p, w, cafe_meal_price)),
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
X_LABEL = "Lunches, brunches & dinners eaten elsewhere per week"  # the meals_out input
Y_LABEL = "Breakfasts skipped or eaten elsewhere per week"  # the breakfasts_skipped input
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
    fig.supxlabel(X_LABEL, color=MUTED, fontsize=10)
    fig.supylabel(Y_LABEL, color=MUTED, fontsize=10)
    fig.suptitle(f"Decision map: {GROUP_TITLES[group]}\nCheapest option per academic year, 2026-27 prices",
                 color=INK, fontsize=13, x=0.01, ha="left")
    return fig


def _plural(n: float, word: str) -> str:
    return f"{n:g} {word}" + ("" if n == 1 else "s")


def plot_you_are_here(meals_out: float, breakfasts_skipped: float, weekends_away: int, prices: Prices,
                      group: str, label: str = "Example student", **kw):
    """One map panel at the student's weekends-away level, with a labelled dot at their habits and the answer."""
    import matplotlib.pyplot as plt

    plans = GROUPS[group]
    rec = recommend(meals_out, breakfasts_skipped, weekends_away, prices, group, **kw)
    cells = grid(weekends_away, prices, group, **kw)
    fig, ax = plt.subplots(figsize=(11, 5.6), facecolor=SURFACE, layout="constrained")
    dot = (meals_out + 0.5, breakfasts_skipped + 0.5)
    _draw_panel(ax, cells, plans, f"{GROUP_TITLES[group]}, {weekends_away} weekends away per term",
                avoid=(dot, (dot[0], dot[1] + 1), (dot[0], dot[1] + 2)))
    ax.plot(meals_out + 0.5, breakfasts_skipped + 0.5, "o", markersize=13, color=INK,
            markeredgecolor=SURFACE, markeredgewidth=2.5, zorder=5)
    habits = (f"{_plural(meals_out, 'meal')} out, {_plural(breakfasts_skipped, 'breakfast')} skipped, "
              f"{_plural(weekends_away, 'weekend')} away")
    ax.annotate(f"{label}\n{habits}", dot, xytext=(0, 14), textcoords="offset points", ha="center",
                fontsize=9, color=INK, linespacing=1.3,
                bbox=dict(boxstyle="round,pad=0.3", fc=SURFACE, ec="none"))
    ax.set_xlabel(X_LABEL, color=MUTED)
    ax.set_ylabel(Y_LABEL, color=MUTED)
    # "\$" because matplotlib reads a pair of bare $ signs as maths notation.
    gap = "tied with" if rec.gap == 0 else f"\\${rec.gap:,.2f}/yr cheaper than"
    fig.suptitle(f"{label}: cheapest is {rec.label} (\\${rec.annual_cost:,.2f}/yr), {gap} {rec.runner_up_label}",
                 color=INK, fontsize=11, x=0.02, ha="left")
    _legend(ax, plans, {c.plan for row in cells for c in row}, loc="upper left", bbox_to_anchor=(1.03, 1),
            note_xy=(1.04, 1.0))
    return fig
