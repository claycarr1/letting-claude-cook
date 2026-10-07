#!/usr/bin/env python3
"""Generate every figure (PNG) and its data table (CSV) in figures/.

Usage:
  .venv/bin/python scripts/make_figures.py
  .venv/bin/python scripts/make_figures.py --you-are-here 4 3 2 --group undergrad_offcampus

Writes:
  figures/decision_map_<group>.png/.csv  for each group in MAP_GROUPS (one panel per weekends-away
                                         level; CSV has every cell's costs, cheapest plan and gap)
  figures/you_are_here.png               the --you-are-here habits on their map
  figures/on_campus_cost_per_meal.png/.csv  the mandatory unlimited plan's cost per meal eaten
"""

import argparse
import csv
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
    plot_decision_map,
    plot_you_are_here,
    recommend,
)
from model import load_prices  # noqa: E402
from on_campus import FULL_WEEK, plot_on_campus, resident_cost_per_meal  # noqa: E402

OUT = ROOT / "figures"
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
    args = ap.parse_args()

    prices = load_prices()
    OUT.mkdir(exist_ok=True)
    for group in MAP_GROUPS:
        fig = plot_decision_map(prices, group)
        fig.savefig(OUT / f"decision_map_{group}.png", dpi=150, facecolor=fig.get_facecolor())
        write_table(prices, group, OUT / f"decision_map_{group}.csv")
        print(f"wrote figures/decision_map_{group}.png and .csv")

    mo, bs, we = args.you_are_here
    fig = plot_you_are_here(mo, bs, int(we), prices, args.group)
    fig.savefig(OUT / "you_are_here.png", dpi=150, facecolor=fig.get_facecolor())
    print("wrote figures/you_are_here.png")

    fig = plot_on_campus(prices)
    fig.savefig(OUT / "on_campus_cost_per_meal.png", dpi=150, facecolor=fig.get_facecolor())
    with (OUT / "on_campus_cost_per_meal.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["meals_per_week", "cost_per_meal_boardplus_spent", "cost_per_meal_boardplus_unspent"])
        for m in range(1, FULL_WEEK + 1):
            w.writerow([m, round(resident_cost_per_meal(m, prices), 2),
                        round(resident_cost_per_meal(m, prices, count_boardplus=False), 2)])
    print("wrote figures/on_campus_cost_per_meal.png and .csv")


if __name__ == "__main__":
    main()
