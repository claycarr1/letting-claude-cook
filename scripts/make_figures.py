#!/usr/bin/env python3
"""Generate every figure (PNG) and its data table (CSV) in figures/.

Usage:
  .venv/bin/python scripts/make_figures.py
  .venv/bin/python scripts/make_figures.py --you-are-here 4 3 2 --group undergrad_offcampus --label You

Main figures (figures/):
  decision_map_undergrad_offcampus.png/.csv  cheapest option, panels for 0, 5 and 10 weekends away
                                             (CSV: every square at every weekends-away level)
  you_are_here.png                       the --you-are-here habits on their map (default: the
                                         example student, 4 meals out, 3 breakfasts skipped,
                                         2 weekends away)
  grad_cafe_spending.png                 graduate students: cheapest option by yearly cafe spending
  meal_type_savings.png                  5-meal plan vs no plan when skipping breakfasts, lunches or dinners
  savings_vs_no_plan.png                 each off-campus plan's yearly saving vs no plan, by HUDS meals/week
  swipe_cost.png                         cost of one swipe on each off-campus plan vs guest prices
  on_campus_cost_per_meal.png/.csv       the mandatory unlimited plan's cost per meal eaten, with
                                         the range across the Monte Carlo draws shaded
  assumption_effects.png                 Monte Carlo: how much each assumption changes the map
                                         (reads figures/monte_carlo_summary.json)
Appendix (figures/appendix/):
  decision_map_undergrad_offcampus_all_weekends.png  every weekends-away level (0-10)
  decision_map_grad.png/.csv             the graduate decision map
  gap_map_undergrad_offcampus.png        dollar gap between the cheapest and second-cheapest option
The Monte Carlo stability maps and summary are made by scripts/run_monte_carlo.py (about 30 seconds).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from decision_map import (  # noqa: E402
    BREAKFASTS_SKIPPED_RANGE,
    GROUPS,
    MEALS_OUT_RANGE,
    WEEKENDS_AWAY_RANGE,
    MAIN_WEEKENDS,
    plot_decision_map,
    plot_you_are_here,
    recommend,
)
from model import load_prices  # noqa: E402
from charts import (  # noqa: E402
    plot_assumption_effects,
    plot_gap_map,
    plot_grad_spending,
    plot_meal_type_savings,
    plot_savings,
    plot_swipe_cost,
)
from monte_carlo import draw_assumptions  # noqa: E402
from on_campus import FULL_WEEK, plot_on_campus, resident_cost_per_meal  # noqa: E402

OUT = ROOT / "figures"
APPENDIX = OUT / "appendix"
# The all-plans map is deliberately not drawn: mixing student groups is misleading (see report.md).
MAP_GROUPS = ["undergrad_offcampus", "grad"]


def write_table(prices, group, path):
    plans = GROUPS[group]
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["weekends_away", "meals_out", "breakfasts_skipped", "cheapest", "annual_cost",
                     "runner_up", "runner_up_cost", "gap"] + [f"cost_{p}" for p in plans])
        for we in range(WEEKENDS_AWAY_RANGE[1] + 1):
            for mo in range(MEALS_OUT_RANGE[1] + 1):
                for bs in range(BREAKFASTS_SKIPPED_RANGE[1] + 1):
                    r = recommend(mo, bs, we, prices, group)
                    w.writerow([we, mo, bs, r.plan, r.annual_cost, r.runner_up, r.runner_up_cost, r.gap]
                               + [r.costs[p] for p in plans])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--you-are-here", nargs=3, type=float, metavar=("MEALS_OUT", "BREAKFASTS_SKIPPED", "WEEKENDS_AWAY"),
                    default=[4, 3, 2])
    ap.add_argument("--group", choices=MAP_GROUPS, default="undergrad_offcampus",
                    help="student group for the you-are-here figure")
    ap.add_argument("--label", default="Example student",
                    help='name shown at the dot, e.g. "You" when plotting your own habits')
    args = ap.parse_args()

    prices = load_prices()
    OUT.mkdir(exist_ok=True)
    APPENDIX.mkdir(exist_ok=True)

    def save(fig, path):
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        print(f"wrote {path.relative_to(ROOT)}")

    group = "undergrad_offcampus"
    save(plot_decision_map(prices, group, MAIN_WEEKENDS), OUT / f"decision_map_{group}.png")
    save(plot_decision_map(prices, group), APPENDIX / f"decision_map_{group}_all_weekends.png")
    write_table(prices, group, OUT / f"decision_map_{group}.csv")
    save(plot_decision_map(prices, "grad"), APPENDIX / "decision_map_grad.png")
    write_table(prices, "grad", APPENDIX / "decision_map_grad.csv")

    mo, bs, we = args.you_are_here
    save(plot_you_are_here(mo, bs, int(we), prices, args.group, label=args.label), OUT / "you_are_here.png")

    fig = plot_on_campus(prices, band_draws=draw_assumptions())
    fig.savefig(OUT / "on_campus_cost_per_meal.png", dpi=150, facecolor=fig.get_facecolor())
    with (OUT / "on_campus_cost_per_meal.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["meals_per_week", "cost_per_meal_boardplus_spent", "cost_per_meal_boardplus_unspent"])
        for m in range(1, FULL_WEEK + 1):
            w.writerow([m, round(resident_cost_per_meal(m, prices), 2),
                        round(resident_cost_per_meal(m, prices, count_boardplus=False), 2)])
    print("wrote figures/on_campus_cost_per_meal.png and .csv")

    save(plot_grad_spending(prices), OUT / "grad_cafe_spending.png")
    save(plot_meal_type_savings(prices), OUT / "meal_type_savings.png")
    save(plot_savings(prices), OUT / "savings_vs_no_plan.png")
    save(plot_swipe_cost(prices), OUT / "swipe_cost.png")
    save(plot_gap_map(prices), APPENDIX / "gap_map_undergrad_offcampus.png")

    summary_path = OUT / "monte_carlo_summary.json"
    if summary_path.exists():
        fig = plot_assumption_effects(json.loads(summary_path.read_text()))
        fig.savefig(OUT / "assumption_effects.png", dpi=150, facecolor=fig.get_facecolor())
        print("wrote figures/assumption_effects.png")
    else:
        print("skipped figures/assumption_effects.png: run scripts/run_monte_carlo.py first")


if __name__ == "__main__":
    main()
