#!/usr/bin/env python3
"""Monte Carlo check of the current model: how stable is the off-campus decision? (src/stability.py)

Usage:
  .venv/bin/python scripts/run_stability.py            # 2,000 runs, seed 2026, all CPU cores
  .venv/bin/python scripts/run_stability.py --runs 200 --processes 1

Writes (figures/):
  stability_map.png             cheapest option by cooking share x HUDS meals, counter and sit-down
                                panels, faded where the runs disagree with the main answer
  stability_map.csv             every square: main answer, stability, class, most common alternative
  stability_assumptions.png     which assumption moves the answer most
  stability_draws.csv           the assumptions drawn in every run
  stability_summary.json        overall numbers, toss-up pairs, assumption effects
The deterministic version (decision_map_meal_type_prices.png) comes from scripts/make_figures.py.
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

from model import load_prices  # noqa: E402
from stability import (  # noqa: E402
    N_RUNS, SEED, draw_to_row, plot_assumption_effects, plot_stability, run, stability_class, summary,
)

OUT = ROOT / "figures"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=N_RUNS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--processes", type=int, default=None, help="default: all CPU cores")
    args = ap.parse_args()

    start = time.time()
    result = run(load_prices(), n=args.runs, seed=args.seed, processes=args.processes)
    print(f"{args.runs:,} runs in {time.time() - start:.0f} s")

    def save(fig, name):
        fig.savefig(OUT / name, dpi=150, facecolor=fig.get_facecolor())
        print(f"wrote figures/{name}")

    save(plot_stability(result), "stability_map.png")
    save(plot_assumption_effects(result), "stability_assumptions.png")
    with (OUT / "stability_map.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["service", "cook_share", "hud_meals_per_week", "main_answer", "stability", "class",
                    "most_common_alternative", "alternative_share"])
        for cell, plan in result.baseline.items():
            alt = result.alternatives[cell].most_common(1)
            w.writerow([*cell, plan, round(result.stability(cell), 4), stability_class(result.stability(cell)),
                        alt[0][0] if alt else "", round(alt[0][1] / args.runs, 4) if alt else 0])
    print("wrote figures/stability_map.csv")
    rows = [draw_to_row(d) for d in result.draws]
    with (OUT / "stability_draws.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote figures/stability_draws.csv")
    s = summary(result)
    s["seed"] = args.seed
    (OUT / "stability_summary.json").write_text(json.dumps(s, indent=1))
    print("wrote figures/stability_summary.json")


if __name__ == "__main__":
    main()
