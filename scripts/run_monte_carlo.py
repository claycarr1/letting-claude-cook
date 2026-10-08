#!/usr/bin/env python3
"""LEGACY (guest-rate model): Monte Carlo sensitivity check of the old off-campus decision map.

It still prices uncovered meals at HUDS guest rates, so it writes into the archive folder
figures/appendix/guest_rate_model/. It will be rebuilt on the current outside-price model.

Usage:
  .venv/bin/python scripts/run_monte_carlo.py            # 2,000 runs, seed 2026, all CPU cores
  .venv/bin/python scripts/run_monte_carlo.py --runs 200 --processes 1

Writes:
  figures/stability_map_undergrad_offcampus.png  each square coloured by its main-map plan, faded
                                                 by how often that plan stays cheapest (0, 5 and
                                                 10 weekends away; every level in figures/appendix/)
  figures/stability_map_undergrad_offcampus.csv  every square: main-map plan, stability, most
                                                 common alternative and its share
  figures/monte_carlo_draws.csv                  the assumptions drawn in every run
  figures/monte_carlo_summary.json               overall stability, 10-meal plan, factor effects
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from decision_map import MAIN_WEEKENDS  # noqa: E402
from model import load_prices  # noqa: E402
from monte_carlo import (  # noqa: E402
    CELLS, GROUP, N_RUNS, SEED, draw_to_dict, factor_effects, nr10_summary, plot_stability, run,
)

OUT = ROOT / "figures" / "appendix" / "guest_rate_model"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=N_RUNS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--processes", type=int, default=None, help="default: all CPU cores")
    args = ap.parse_args()

    prices = load_prices()
    start = time.perf_counter()
    result = run(prices, args.runs, args.seed, processes=args.processes)
    elapsed = time.perf_counter() - start
    print(f"{args.runs} runs x {len(CELLS)} squares in {elapsed:.1f}s")

    OUT.mkdir(exist_ok=True)
    fig = plot_stability(result, weekends_levels=MAIN_WEEKENDS)
    fig.savefig(OUT / f"stability_map_{GROUP}.png", dpi=150, facecolor=fig.get_facecolor())
    (OUT / "appendix").mkdir(parents=True, exist_ok=True)
    fig = plot_stability(result)
    fig.savefig(OUT / "appendix" / f"stability_map_{GROUP}_all_weekends.png", dpi=150, facecolor=fig.get_facecolor())

    with (OUT / f"stability_map_{GROUP}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["weekends_away", "meals_out", "breakfasts_skipped", "main_map_plan", "stability",
                    "most_common_alternative", "alternative_share"])
        for c in CELLS:
            alt = result.alternatives[c].most_common(1)
            name, count = alt[0] if alt else ("", 0)
            w.writerow([*c, result.baseline[c], round(result.stability(c), 4), name, round(count / args.runs, 4)])

    with (OUT / "monte_carlo_draws.csv").open("w", newline="") as f:
        fields = list(draw_to_dict(result.draws[0])) + ["share_of_squares_matching_main_map", "nr10_squares"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d, a, n in zip(result.draws, result.agreement_by_run, result.nr10_cells):
            w.writerow({**draw_to_dict(d), "share_of_squares_matching_main_map": round(a, 4), "nr10_squares": n})

    stabilities = [result.stability(c) for c in CELLS]
    summary = {
        "runs": args.runs, "seed": args.seed, "squares": len(CELLS), "seconds": round(elapsed, 1),
        "mean_stability": sum(stabilities) / len(stabilities),
        "squares_95_or_more": sum(s >= 0.95 for s in stabilities),
        "squares_80_to_95": sum(0.80 <= s < 0.95 for s in stabilities),
        "squares_under_80": sum(s < 0.80 for s in stabilities),
        "squares_under_60": sum(s < 0.60 for s in stabilities),
        "nr10": nr10_summary(result),
        "agreement_by_assumption": factor_effects(result),
    }
    (OUT / "monte_carlo_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
