#!/usr/bin/env python3
"""Generate the decision-map figures (PNG) and their data tables (CSV) in figures/.

Usage:
  .venv/bin/python scripts/make_decision_map.py
  .venv/bin/python scripts/make_decision_map.py --you-are-here 4 3 2 --group undergrad_offcampus

Writes, for each student group in src/decision_map.GROUPS:
  figures/decision_map_<group>.png   one panel per weekends-away level
  figures/decision_map_<group>.csv   every cell: inputs, cheapest plan, cost, runner-up, gap, all costs
and figures/you_are_here.png for the --you-are-here habits.
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

OUT = ROOT / "figures"


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
    ap.add_argument("--group", choices=sorted(GROUPS), default="undergrad_offcampus",
                    help="student group for the you-are-here figure")
    args = ap.parse_args()

    prices = load_prices()
    OUT.mkdir(exist_ok=True)
    for group in GROUPS:
        fig = plot_decision_map(prices, group)
        fig.savefig(OUT / f"decision_map_{group}.png", dpi=150, facecolor=fig.get_facecolor())
        write_table(prices, group, OUT / f"decision_map_{group}.csv")
        print(f"wrote figures/decision_map_{group}.png and .csv")

    mo, bs, we = args.you_are_here
    fig = plot_you_are_here(mo, bs, int(we), prices, args.group)
    fig.savefig(OUT / "you_are_here.png", dpi=150, facecolor=fig.get_facecolor())
    print("wrote figures/you_are_here.png")


if __name__ == "__main__":
    main()
