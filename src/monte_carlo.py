"""Step 3 (secondary): Monte Carlo check of how sensitive the decision map is to assumptions.

The off-campus undergrad map is redrawn many times. Each run draws the uncertain
assumptions at random:

  weeks per term          fall and spring each uniform on WEEKS_RANGE (drawn separately)
  short first week        full weekly swipes or a fraction of them    (50/50)
  meals eaten elsewhere   spread over lunch/brunch/dinner or dinners first (50/50)
  breakfast price         House guest rate or Annenberg/Quincy rate    (50/50)
  BoardPlus               spent or unspent -- affects only the on-campus plan, so it is
                          used for the on-campus chart's band, not the map (50/50)

The 50/50 odds are a deliberately neutral choice, not evidence; the stability numbers
depend on them. A square's stability is the share of runs in which its cheapest plan is the
same as on the baseline map (calendar weeks, partial first-week swipes, meals out spread,
House breakfast). Every cost comes from src/decision_map.annual_costs, i.e. src/model.py.
"""

import os
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from decision_map import (
    BREAKFASTS_SKIPPED_RANGE,
    GROUPS,
    MEALS_OUT_RANGE,
    WEEKENDS_AWAY_RANGE,
    annual_costs,
)
from model import Prices, load_term_weeks

SEED = 2026
N_RUNS = 2000
WEEKS_RANGE = (14.5, 16.0)
COIN = 0.5  # odds for every yes/no assumption
GROUP = "undergrad_offcampus"

Cell = Tuple[int, int, int]  # (weekends_away, meals_out, breakfasts_skipped)
CELLS: List[Cell] = [(we, mo, bs)
                     for we in range(WEEKENDS_AWAY_RANGE[1] + 1)
                     for mo in range(MEALS_OUT_RANGE[1] + 1)
                     for bs in range(BREAKFASTS_SKIPPED_RANGE[1] + 1)]


@dataclass(frozen=True)
class Draw:
    fall_weeks: float
    spring_weeks: float
    full_first_week_swipes: bool
    meals_out_from: str  # "spread" or "dinners_first"
    breakfast_venue: str  # "houses" or "annenberg_quincy"
    boardplus_spent: bool  # on-campus chart only

    def term_weeks(self) -> Dict[str, float]:
        return {"fall": self.fall_weeks, "spring": self.spring_weeks}


def baseline_draw() -> Draw:
    weeks = load_term_weeks()
    return Draw(weeks["fall"], weeks["spring"], False, "spread", "houses", True)


def draw_assumptions(n: int = N_RUNS, seed: int = SEED, weeks_range: Tuple[float, float] = WEEKS_RANGE,
                     coin: float = COIN) -> List[Draw]:
    rng = random.Random(seed)
    return [Draw(fall_weeks=rng.uniform(*weeks_range),
                 spring_weeks=rng.uniform(*weeks_range),
                 full_first_week_swipes=rng.random() < coin,
                 meals_out_from="dinners_first" if rng.random() < coin else "spread",
                 breakfast_venue="annenberg_quincy" if rng.random() < coin else "houses",
                 boardplus_spent=rng.random() < coin)
            for _ in range(n)]


def cheapest_map(prices: Prices, draw: Draw, group: str = GROUP) -> Dict[Cell, str]:
    """The cheapest plan in every square under one draw (ties go to the earlier plan in the group)."""
    plans = GROUPS[group]
    out = {}
    for we, mo, bs in CELLS:
        costs = annual_costs(mo, bs, we, prices, plans, term_weeks=draw.term_weeks(),
                             meals_out_from=draw.meals_out_from, breakfast_venue=draw.breakfast_venue,
                             full_first_week_swipes=draw.full_first_week_swipes)
        out[(we, mo, bs)] = min(plans, key=lambda p: (costs[p], plans.index(p)))
    return out


def _cheapest_map_job(args):
    prices, draw, group = args
    return cheapest_map(prices, draw, group)


@dataclass
class Result:
    draws: List[Draw]
    baseline: Dict[Cell, str]
    agree: Dict[Cell, int]  # runs whose cheapest plan matches the baseline
    alternatives: Dict[Cell, Counter]  # cheapest plan when it differs from the baseline
    nr10_cells: List[int]  # per run: squares where the 10-meal plan is cheapest
    agreement_by_run: List[float]  # per run: share of squares matching the baseline

    def stability(self, cell: Cell) -> float:
        return self.agree[cell] / len(self.draws)


def run(prices: Prices, n: int = N_RUNS, seed: int = SEED, group: str = GROUP,
        draws: Optional[List[Draw]] = None, processes: Optional[int] = None) -> Result:
    """Redraw the map once per draw. processes=1 runs in this process (used by the tests)."""
    draws = draws if draws is not None else draw_assumptions(n, seed)
    baseline = cheapest_map(prices, baseline_draw(), group)
    jobs = [(prices, d, group) for d in draws]
    processes = processes or os.cpu_count() or 1
    if processes == 1:
        maps = [_cheapest_map_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(processes) as pool:
            maps = list(pool.map(_cheapest_map_job, jobs, chunksize=max(1, len(jobs) // (4 * processes))))

    agree = {c: 0 for c in CELLS}
    alternatives = {c: Counter() for c in CELLS}
    nr10_cells, agreement_by_run = [], []
    for m in maps:
        same = 0
        for c in CELLS:
            if m[c] == baseline[c]:
                agree[c] += 1
                same += 1
            else:
                alternatives[c][m[c]] += 1
        nr10_cells.append(sum(1 for c in CELLS if m[c] == "nr10"))
        agreement_by_run.append(same / len(CELLS))
    return Result(draws, baseline, agree, alternatives, nr10_cells, agreement_by_run)


def factor_effects(result: Result) -> Dict[str, Dict[str, float]]:
    """Average share of squares matching the baseline, split by each assumption's value."""
    def mean(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    pairs = list(zip(result.draws, result.agreement_by_run))
    out = {}
    for name, fn in [("first week swipes", lambda d: "full" if d.full_first_week_swipes else "partial"),
                     ("meals out taken from", lambda d: d.meals_out_from),
                     ("breakfast price", lambda d: d.breakfast_venue)]:
        groups: Dict[str, List[float]] = {}
        for d, a in pairs:
            groups.setdefault(fn(d), []).append(a)
        out[name] = {k: mean(v) for k, v in sorted(groups.items())}
    weeks_bins = {}
    for d, a in pairs:
        total = d.fall_weeks + d.spring_weeks
        key = "29.0-30.0" if total < 30 else "30.0-31.0" if total < 31 else "31.0-32.0"
        weeks_bins.setdefault(key, []).append(a)
    out["total weeks per year"] = {k: mean(v) for k, v in sorted(weeks_bins.items())}
    return out


def nr10_summary(result: Result) -> Dict[str, object]:
    """How often the 10-meal plan is cheapest anywhere, and what those runs have in common."""
    wins = [(d, n) for d, n in zip(result.draws, result.nr10_cells) if n]
    summary: Dict[str, object] = {
        "runs": len(result.draws),
        "runs_where_nr10_wins_somewhere": len(wins),
        "share_of_runs": len(wins) / len(result.draws),
        "share_of_all_squares": sum(result.nr10_cells) / (len(result.draws) * len(CELLS)),
        "max_squares_in_one_run": max(result.nr10_cells, default=0),
    }
    if wins:
        ds = [d for d, _ in wins]
        summary["in_those_runs"] = {
            "full_first_week_swipes": sum(d.full_first_week_swipes for d in ds) / len(ds),
            "meals_out_dinners_first": sum(d.meals_out_from == "dinners_first" for d in ds) / len(ds),
            "annenberg_breakfast": sum(d.breakfast_venue == "annenberg_quincy" for d in ds) / len(ds),
            "min_total_weeks": min(d.fall_weeks + d.spring_weeks for d in ds),
            "mean_total_weeks": sum(d.fall_weeks + d.spring_weeks for d in ds) / len(ds),
        }
    return summary


def draw_to_dict(d: Draw) -> dict:
    return asdict(d)


# ---------------------------------------------------------------------------- plotting

STABILITY_BINS = [(0.95, 1.0, "95% or more of runs agree"),
                  (0.80, 0.55, "80-95%"),
                  (0.0, 0.2, "under 80% (toss-up)")]  # (lower bound, colour strength, label)


def _blend(hex_color: str, strength: float, surface: str) -> str:
    """Mix a colour toward the surface: strength 1 = full colour, 0 = surface."""
    c = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    s = [int(surface[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a * strength + b * (1 - strength)):02x}" for a, b in zip(c, s))


def strength_for(stability: float) -> float:
    for lower, strength, _ in STABILITY_BINS:
        if stability >= lower:
            return strength
    return STABILITY_BINS[-1][1]


def plot_stability(result: Result, group: str = GROUP):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    from decision_map import GROUP_TITLES, INK, MUTED, PLAN_COLORS, PLAN_LABELS, SHORT_LABELS, SURFACE, X_LABEL, Y_LABEL

    levels = list(range(WEEKENDS_AWAY_RANGE[1] + 1))
    ncols = 4
    nrows = -(-(len(levels) + 1) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 2.9 * nrows + 1.4), facecolor=SURFACE,
                             layout="constrained")
    axes = axes.ravel()
    for ax, we in zip(axes, levels):
        for mo in range(MEALS_OUT_RANGE[1] + 1):
            for bs in range(BREAKFASTS_SKIPPED_RANGE[1] + 1):
                cell = (we, mo, bs)
                color = _blend(PLAN_COLORS[result.baseline[cell]], strength_for(result.stability(cell)), SURFACE)
                ax.add_patch(Rectangle((mo, bs), 1, 1, facecolor=color, edgecolor=SURFACE, linewidth=0.6))
        ax.set_xlim(0, MEALS_OUT_RANGE[1] + 1)
        ax.set_ylim(0, BREAKFASTS_SKIPPED_RANGE[1] + 1)
        ax.set_aspect("equal")
        ax.set_title(f"{we} weekend{'s' if we != 1 else ''} away per term", fontsize=10, color=INK, loc="left")
        ax.set_xticks([x + 0.5 for x in range(0, 15, 2)], [str(x) for x in range(0, 15, 2)])
        ax.set_yticks([y + 0.5 for y in range(8)], [str(y) for y in range(8)])
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        for side in ax.spines.values():
            side.set_visible(False)
    for ax in axes[len(levels):]:
        ax.axis("off")

    shown = [p for p in GROUPS[group] if p in set(result.baseline.values())]
    plan_handles = [Patch(facecolor=PLAN_COLORS[p], label=f"{SHORT_LABELS[p]}: {PLAN_LABELS[p]}") for p in shown]
    ref = PLAN_COLORS[shown[0]]
    strength_handles = [Patch(facecolor=_blend(ref, s, SURFACE), label=label) for _, s, label in STABILITY_BINS]
    legend_ax = axes[len(levels)]
    first = legend_ax.legend(handles=plan_handles, loc="upper left", frameon=False, fontsize=9, labelcolor=INK,
                             title="Cheapest on the main map", title_fontsize=10, alignment="left")
    legend_ax.add_artist(first)
    legend_ax.legend(handles=strength_handles, loc="lower left", frameon=False, fontsize=9, labelcolor=INK,
                     title="How often it stays cheapest", title_fontsize=10, alignment="left")

    fig.supxlabel(X_LABEL, color=MUTED, fontsize=10)
    fig.supylabel(Y_LABEL, color=MUTED, fontsize=10)
    wks = f"{WEEKS_RANGE[0]:g}-{WEEKS_RANGE[1]:g}"
    fig.suptitle(f"How stable is the decision map? {GROUP_TITLES[group]}, {len(result.draws):,} runs\n"
                 f"Each run draws weeks per term ({wks}), full or partial first-week swipes, meals out spread or "
                 f"dinners first, and House or Annenberg breakfast price (50/50 odds)",
                 color=INK, fontsize=12, x=0.01, ha="left")
    return fig
