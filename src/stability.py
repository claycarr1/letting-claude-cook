"""Monte Carlo check of the current model (from 2026-10-09): how stable is the off-campus decision?

The map: two panels (students who eat out at counter places / at sit-down places), x = share of
the meals not eaten at HUDS that the student cooks (0-100%), y = HUDS meals per week (0-21). In
each square a meal not eaten at HUDS costs, per meal type (breakfast, lunch, brunch, dinner):

    cooking share x cooking cost + (1 - cooking share) x that service's eating-out price

Each run draws:
  weeks per term        fall and spring each uniform on 14.5-16 (drawn separately)
  first-week swipes     full or partial                                      (50/50)
  meals skipped at HUDS spread / dinners first / lunches first               (1/3 each)
  sit-down tip          uniform 15-22%, on the pre-tax or after-tax price   (50/50)
  cooking cost          uniform between the USDA Thrifty and Liberal costs ($4.01-$6.42)
  eating-out prices     each (service, meal type) group of the restaurant sample is resampled
                        with replacement (same size) and averaged -- a bootstrap of the means.
                        Counter brunch has no meals and uses counter lunch.

The baseline is the deterministic map: calendar weeks, partial first-week swipes, meals skipped
spread out, 18% tip on the pre-tax price, $5.15 cooking (moderate plan, cooking alone), sample
means. A square's stability is the share of runs whose cheapest option matches the baseline's.
Yes/no odds are 50/50 and the three-way choice 1/3 each: neutral choices, not evidence.
Every cost comes from src/outside_food.year_food_spending (src/model.py).
"""

import os
import random
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from cooking import cooking_cost_per_meal, cooking_range
from model import MEAL_TYPES, Prices, load_term_weeks
from outside_food import FULL_WEEK, PLANS, cheapest
from restaurants import FALLBACK, SERVICES, SIT_DOWN_TIP, load_meals, meal_type_prices, out_the_door

SEED = 2026
N_RUNS = 2000
WEEKS_RANGE = (14.5, 16.0)
TIP_RANGE = (0.15, 0.22)
COIN = 0.5
MEALS_OUT_FROM = ("spread", "dinners_first", "lunches_first")
COOK_SHARES = tuple(i / 20 for i in range(21))  # 0%, 5%, ..., 100%
HUD_MEALS = tuple(range(FULL_WEEK + 1))
SERVICE_TITLES = {"counter": "If you eat out at counter places", "sit-down": "If you eat out at sit-down places"}

Cell = Tuple[str, float, int]  # (service, cooking share, HUDS meals per week)
CELLS: List[Cell] = [(s, c, e) for s in SERVICES for c in COOK_SHARES for e in HUD_MEALS]


@dataclass(frozen=True)
class Draw:
    fall_weeks: float
    spring_weeks: float
    full_first_week_swipes: bool
    meals_out_from: str
    tip: float
    tip_on_tax: bool
    cooking_cost: float
    eat_out: Dict[str, Dict[str, float]]  # service -> meal type -> mean out-the-door price

    def term_weeks(self) -> Dict[str, float]:
        return {"fall": self.fall_weeks, "spring": self.spring_weeks}

    def outside_prices(self, service: str, cook_share: float) -> Dict[str, float]:
        return {m: cook_share * self.cooking_cost + (1 - cook_share) * self.eat_out[service][m] for m in MEAL_TYPES}


def baseline_draw(meals: Optional[List[dict]] = None) -> Draw:
    meals = load_meals() if meals is None else meals
    weeks = load_term_weeks()
    return Draw(weeks["fall"], weeks["spring"], False, "spread", SIT_DOWN_TIP, False, cooking_cost_per_meal(),
                {s: meal_type_prices(s, meals) for s in SERVICES})


def bootstrap_prices(meals: List[dict], rng: random.Random, tip: float, tip_on_tax: bool) -> Dict[str, Dict[str, float]]:
    """Resample every (service, meal type) group with replacement and average it."""
    out: Dict[str, Dict[str, float]] = {}
    for s in SERVICES:
        out[s] = {}
        for m in MEAL_TYPES:
            group = [float(x["menu_price"]) for x in meals if x["service"] == s and x["meal_type"] == m]
            if group:
                sample = [rng.choice(group) for _ in group]
                out[s][m] = statistics.mean(out_the_door(p, s, tip, tip_on_tax) for p in sample)
        for m, fallback in FALLBACK.items():
            out[s].setdefault(m, out[s][fallback])
    return out


def draw_assumptions(n: int = N_RUNS, seed: int = SEED, meals: Optional[List[dict]] = None) -> List[Draw]:
    meals = load_meals() if meals is None else meals
    cook = cooking_range()
    cook_lo, cook_hi = min(cook.values()), max(cook.values())
    rng = random.Random(seed)
    draws = []
    for _ in range(n):
        fall, spring = rng.uniform(*WEEKS_RANGE), rng.uniform(*WEEKS_RANGE)
        full_first = rng.random() < COIN
        meals_out_from = rng.choice(MEALS_OUT_FROM)
        tip, tip_on_tax = rng.uniform(*TIP_RANGE), rng.random() < COIN
        cooking = rng.uniform(cook_lo, cook_hi)
        draws.append(Draw(fall, spring, full_first, meals_out_from, tip, tip_on_tax, cooking,
                          bootstrap_prices(meals, rng, tip, tip_on_tax)))
    return draws


def cheapest_map(prices: Prices, draw: Draw, cells: List[Cell] = CELLS) -> Dict[Cell, str]:
    """The cheapest option in every square under one draw (ties go to the earlier option)."""
    weeks = draw.term_weeks()
    return {(s, c, e): cheapest(FULL_WEEK - e, draw.outside_prices(s, c), prices, term_weeks=weeks,
                                meals_out_from=draw.meals_out_from,
                                full_first_week_swipes=draw.full_first_week_swipes)[0]
            for s, c, e in cells}


def _job(args):
    return cheapest_map(*args)


@dataclass
class Result:
    draws: List[Draw]
    baseline: Dict[Cell, str]
    agree: Dict[Cell, int]
    alternatives: Dict[Cell, Counter]
    agreement_by_run: List[float]  # per run: share of squares matching the baseline
    maps: List[Dict[Cell, str]]  # per run: cheapest option in every square

    def contested(self) -> List[Cell]:
        """Squares whose answer changes in at least 5% of runs (not solid)."""
        return [c for c in self.baseline if self.stability(c) < STABLE]

    def contested_agreement_by_run(self) -> List[float]:
        cells = self.contested()
        if not cells:
            return [1.0] * len(self.maps)
        return [sum(m[c] == self.baseline[c] for c in cells) / len(cells) for m in self.maps]

    def stability(self, cell: Cell) -> float:
        return self.agree[cell] / len(self.draws)


def run(prices: Prices, n: int = N_RUNS, seed: int = SEED, draws: Optional[List[Draw]] = None,
        processes: Optional[int] = None, cells: List[Cell] = CELLS) -> Result:
    """Redraw the map once per draw. processes=1 runs in this process (used by the tests)."""
    draws = draws if draws is not None else draw_assumptions(n, seed)
    baseline = cheapest_map(prices, baseline_draw(), cells)
    jobs = [(prices, d, cells) for d in draws]
    processes = processes or os.cpu_count() or 1
    if processes == 1:
        maps = [_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(processes) as pool:
            maps = list(pool.map(_job, jobs, chunksize=max(1, len(jobs) // (4 * processes))))
    agree = {c: 0 for c in cells}
    alternatives = {c: Counter() for c in cells}
    agreement_by_run = []
    for m in maps:
        same = 0
        for c in cells:
            if m[c] == baseline[c]:
                agree[c] += 1
                same += 1
            else:
                alternatives[c][m[c]] += 1
        agreement_by_run.append(same / len(cells))
    return Result(draws, baseline, agree, alternatives, agreement_by_run, maps)


# ---------------------------------------------------------------------------- summaries

STABLE, MOSTLY = 0.95, 0.80  # solid: >= 95% of runs agree; toss-up: under 80%


def stability_class(s: float) -> str:
    return "solid" if s >= STABLE else "mostly" if s >= MOSTLY else "toss-up"


def _eat_out_level(d: Draw) -> float:
    """Mean of a draw's eating-out prices (all groups), to split runs into cheaper/pricier halves."""
    return statistics.mean(v for s in d.eat_out.values() for v in s.values())


ASSUMPTIONS = {  # name -> (label, function of a draw giving its setting; numbers are split at the median)
    "weeks": ("Weeks per term", lambda d: d.fall_weeks + d.spring_weeks),
    "first_week": ("Full or partial first-week swipes", lambda d: "full" if d.full_first_week_swipes else "partial"),
    "meals_out_from": ("Which HUDS meals are skipped", lambda d: d.meals_out_from),
    "tip": ("Sit-down tip (15-22%)", lambda d: d.tip),
    "tip_on_tax": ("Tip on pre- or after-tax price", lambda d: "after tax" if d.tip_on_tax else "pre-tax"),
    "cooking": ("Cooking cost ($4.01-$6.42)", lambda d: d.cooking_cost),
    "eat_out": ("Restaurant sample (resampled)", _eat_out_level),
}


def agreement_by_assumption(result: Result) -> Dict[str, Dict[str, float]]:
    """{assumption: {setting: mean share of the contested squares (stability under 95%) matching
    the baseline}}. Numeric assumptions are split into a lower and an upper half at their median.
    Solid squares are left out: they agree in (nearly) every run, so they would only dilute the
    differences."""
    pairs = list(zip(result.draws, result.contested_agreement_by_run()))
    out = {}
    for key, (_, fn) in ASSUMPTIONS.items():
        values = [fn(d) for d, _ in pairs]
        if isinstance(values[0], (int, float)) and not isinstance(values[0], bool):
            mid = statistics.median(values)
            settings = ["lower half" if v <= mid else "upper half" for v in values]
        else:
            settings = values
        groups: Dict[str, List[float]] = {}
        for s, (_, a) in zip(settings, pairs):
            groups.setdefault(s, []).append(a)
        out[key] = {s: statistics.mean(v) for s, v in sorted(groups.items())}
    return out


def assumption_effects(result: Result) -> List[dict]:
    """Per assumption: percentage points between its settings with the most and least agreement
    with the baseline map. Biggest first."""
    out = []
    for key, by_setting in agreement_by_assumption(result).items():
        hi, lo = max(by_setting, key=by_setting.get), min(by_setting, key=by_setting.get)
        out.append({"assumption": key, "label": ASSUMPTIONS[key][0], "effect_pp": 100 * (by_setting[hi] - by_setting[lo]),
                    "most_agreement": hi, "least_agreement": lo, "by_setting": by_setting})
    return sorted(out, key=lambda e: -e["effect_pp"])


def summary(result: Result) -> dict:
    cells = list(result.baseline)
    classes = Counter(stability_class(result.stability(c)) for c in cells)
    pairs = Counter()
    for c in cells:
        if stability_class(result.stability(c)) == "toss-up" and result.alternatives[c]:
            alt = result.alternatives[c].most_common(1)[0][0]
            pairs[" vs ".join(sorted((result.baseline[c], alt), key=PLANS.index))] += 1
    by_service = {}
    for s in SERVICES:
        sc = [c for c in cells if c[0] == s]
        by_service[s] = {"squares": len(sc),
                         "mean_stability": statistics.mean(result.stability(c) for c in sc),
                         **{k: sum(stability_class(result.stability(c)) == k for c in sc)
                            for k in ("solid", "mostly", "toss-up")},
                         "baseline_options": dict(Counter(result.baseline[c] for c in sc))}
    return {"runs": len(result.draws), "squares": len(cells), "seed": SEED,
            "mean_stability": statistics.mean(result.stability(c) for c in cells),
            "classes": dict(classes), "contested_squares": len(result.contested()), "toss_up_pairs": dict(pairs.most_common()), "by_service": by_service,
            "assumption_effects": assumption_effects(result)}


def draw_to_row(d: Draw) -> dict:
    row = {k: v for k, v in asdict(d).items() if k != "eat_out"}
    for s, by_type in d.eat_out.items():
        for m, v in by_type.items():
            row[f"{s}_{m}"] = round(v, 4)
    return row


# ---------------------------------------------------------------------------- figures

def _grid_axes(ax, show_y=True):
    import style
    from outside_food import MUTED, _frameless

    _frameless(ax)
    ax.set_xlim(-0.025, 1.025)
    ax.set_ylim(-0.5, FULL_WEEK + 0.5)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_yticks([0, 7, 14, 21])
    if not show_y:
        ax.set_yticklabels([])
    ax.tick_params(colors=MUTED, labelsize=style.TICK, length=0)


X_LABEL = "Share of your meals not eaten at HUDS that you cook (the rest you eat out)"
Y_LABEL = "Meals you'd eat at HUDS per week (if you had swipes)"


def _panel(ax, service: str, plan_of, color_of, label_regions=True):
    """Draw one service's squares (colour from color_of(cell)) with borders where plan_of changes."""
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle

    from outside_food import INK, SHORT_LABELS, SURFACE, _halo, _label_point, _region_edges, _two_lines
    import style

    xs, ys = list(COOK_SHARES), list(HUD_MEALS)
    step = xs[1] - xs[0]
    grid = [[plan_of((service, x, y)) for x in xs] for y in ys]
    for y in ys:
        for x in xs:
            ax.add_patch(Rectangle((x - step / 2, y - 0.5), step, 1, facecolor=color_of((service, x, y)),
                                   edgecolor="none"))
    segs = []
    for p in PLANS:
        segs += _region_edges([[q == p for q in row] for row in grid], xs, ys)
    ax.add_collection(LineCollection(segs, colors=INK, linewidths=1.4, capstyle="projecting"))
    if label_regions:
        for p in PLANS:
            pts = [(x, y) for row, y in zip(grid, ys) for x, q in zip(xs, row) if q == p]
            if len(pts) >= 6:
                x, y = _label_point(pts, xs, ys)
                ax.text(x, y, _two_lines(SHORT_LABELS[p]) if p == "nr21" else SHORT_LABELS[p], ha="center",
                        va="center", fontsize=style.LABEL, color=INK, weight="bold", path_effects=_halo())


def _two_panels(title: str, plan_of, color_of, legend_handles, legend_title):
    import matplotlib.pyplot as plt

    import style
    from outside_food import INK, MUTED, SURFACE

    fig, axes = plt.subplots(1, 2, figsize=(16, 8), facecolor=SURFACE, layout="constrained")
    for i, (ax, s) in enumerate(zip(axes, SERVICES)):
        _panel(ax, s, plan_of, color_of)
        _grid_axes(ax, show_y=i == 0)
        ax.set_title(SERVICE_TITLES[s], fontsize=style.PANEL_TITLE, color=INK, loc="left", pad=10)
    axes[0].set_ylabel(Y_LABEL, color=MUTED, fontsize=style.LABEL)
    fig.supxlabel(X_LABEL, color=MUTED, fontsize=style.LABEL)
    fig.legend(handles=legend_handles, loc="outside right center", frameon=False, fontsize=style.TICK,
               labelcolor=INK, title=legend_title, title_fontsize=style.LABEL, alignment="left")
    style.title(fig, title)
    return fig


def plot_meal_type_map(prices: Prices, baseline: Optional[Dict[Cell, str]] = None):
    """Deterministic map with breakfast, lunch, brunch and dinner priced separately (the
    Monte Carlo's baseline)."""
    from matplotlib.patches import Patch

    from decision_map import PLAN_LABELS
    from outside_food import INK, PLAN_COLORS_NOW, _two_lines

    baseline = baseline or cheapest_map(prices, baseline_draw())
    shown = [p for p in PLANS if p in set(baseline.values())]
    handles = [Patch(facecolor=PLAN_COLORS_NOW[p], edgecolor=INK, linewidth=0.8, label=_two_lines(PLAN_LABELS[p]))
               for p in shown]
    counter_plans = {baseline[c] for c in baseline if c[0] == "counter"}
    plan_shares = [c[1] for c in baseline if c[0] == "sit-down" and baseline[c] != "no_plan"]
    sit_down = (f"plans win only for sit-down eaters who cook {max(plan_shares):.0%} or less of those meals"
                if plan_shares else "no plan wins for sit-down eaters too")
    counter = ("no plan still wins for every counter eater" if counter_plans == {"no_plan"}
               else "plans win for some counter eaters too")
    title = f"With separate breakfast, lunch and dinner prices, {counter}; {sit_down}"
    return _two_panels(title, baseline.get, lambda c: PLAN_COLORS_NOW[baseline[c]], handles, "Cheapest option")


STABILITY_LEVELS = [(STABLE, 1.0, "Solid: 95%+ of runs agree"), (MOSTLY, 0.55, "Mostly: 80-95%"),
                    (0.0, 0.2, "Toss-up: under 80%")]


def plot_stability(result: Result):
    from matplotlib.patches import Patch

    from decision_map import PLAN_LABELS
    from monte_carlo import _blend
    from outside_food import INK, PLAN_COLORS_NOW, SURFACE, _two_lines

    def strength(cell):
        s = result.stability(cell)
        return next(v for lower, v, _ in STABILITY_LEVELS if s >= lower)

    def color(cell):
        return _blend(PLAN_COLORS_NOW[result.baseline[cell]], strength(cell), SURFACE)

    shown = [p for p in PLANS if p in set(result.baseline.values())]
    handles = [Patch(facecolor=PLAN_COLORS_NOW[p], edgecolor=INK, linewidth=0.8, label=_two_lines(PLAN_LABELS[p]))
               for p in shown]
    ref = "#52514e"  # neutral grey for the fading key, so it doesn't look like a plan
    handles += [Patch(facecolor="none", edgecolor="none", label="")]
    handles += [Patch(facecolor=_blend(ref, v, SURFACE), edgecolor=INK, linewidth=0.5, label=label)
                for _, v, label in STABILITY_LEVELS]
    s = summary(result)
    solid = s["classes"].get("solid", 0) / s["squares"]
    toss = s["classes"].get("toss-up", 0) / s["squares"]
    title = (f"{solid:.0%} of the map is solid across {s['runs']:,} runs; the {toss:.0%} that is a toss-up "
             f"sits on the borders between options")
    return _two_panels(title, result.baseline.get, color, handles, "Cheapest option, faded where uncertain")


def plot_assumption_effects(result: Result):
    import matplotlib.pyplot as plt

    import style
    from charts import GRID_COLOR, _style
    from outside_food import INK, MUTED, SURFACE

    effects = assumption_effects(result)
    fig, ax = plt.subplots(figsize=(12, 6), facecolor=SURFACE, layout="constrained")
    _style(ax)
    ys = list(range(len(effects)))[::-1]
    for y, e in zip(ys, effects):
        ax.barh(y, e["effect_pp"], height=0.55, color="#2a78d6", zorder=3)
        ax.text(e["effect_pp"] + 0.1, y, f"{e['effect_pp']:.1f}", va="center", fontsize=style.TICK, color=INK)
    ax.set_yticks(ys, [e["label"].replace("$", r"\$") for e in effects], color=INK, fontsize=style.TICK)
    ax.tick_params(axis="x", labelsize=style.TICK)
    ax.set_xlim(0, max(e["effect_pp"] for e in effects) * 1.2 + 0.5)
    ax.set_xlabel("How much more often the main answer holds under one setting than the other\n"
                  "(percentage points, in the squares that aren't solid)", color=MUTED, fontsize=style.LABEL)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8)
    top = effects[0]
    style.title(fig, f"{top['label']} moves the answer most ({top['effect_pp']:.1f} points); "
                     f"the rest move it by {effects[1]['effect_pp']:.1f} points or less")
    return fig
