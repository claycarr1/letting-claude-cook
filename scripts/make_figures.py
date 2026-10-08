#!/usr/bin/env python3
"""Generate every current figure (PNG) and its data table (CSV) in figures/.

Usage:
  .venv/bin/python scripts/make_figures.py

Current model (from 2026-10-08): no guest meals; meals not eaten at HUDS are eaten out or cooked
at an outside price (see src/outside_food.py). Main figures (figures/):
  decision_map_undergrad_offcampus.png/.csv  cheapest option by outside price x HUDS meals missed
  grad_cafe_spending.png                 graduate students: cheapest option by yearly cafe spending
  swipe_cost.png                         cost of one swipe on each off-campus plan (guest prices as reference)
  on_campus_cost_per_meal.png/.csv       the mandatory unlimited plan's cost per meal eaten
Drafts of the spending chart (figures/drafts/):
  draft_A_continuous.png, draft_B_binned.png, draft_C_extra_cost.png
The guest-rate results are archived in figures/appendix/guest_rate_model/ (git tag guest-rate-model).
"""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from charts import plot_grad_spending, plot_swipe_cost  # noqa: E402
from model import load_prices  # noqa: E402
from monte_carlo import draw_assumptions  # noqa: E402
from on_campus import FULL_WEEK, plot_on_campus, resident_cost_per_meal  # noqa: E402
from outside_food import draft_binned, draft_continuous, draft_extra_cost, plot_main_map, write_grid_csv  # noqa: E402

OUT = ROOT / "figures"
DRAFTS = OUT / "drafts"


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    prices = load_prices()
    OUT.mkdir(exist_ok=True)
    DRAFTS.mkdir(exist_ok=True)

    def save(fig, path):
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        print(f"wrote {path.relative_to(ROOT)}")

    save(plot_main_map(prices), OUT / "decision_map_undergrad_offcampus.png")
    write_grid_csv(prices, OUT / "decision_map_undergrad_offcampus.csv")
    save(draft_continuous(prices), DRAFTS / "draft_A_continuous.png")
    save(draft_binned(prices), DRAFTS / "draft_B_binned.png")
    save(draft_extra_cost(prices), DRAFTS / "draft_C_extra_cost.png")
    save(plot_grad_spending(prices), OUT / "grad_cafe_spending.png")
    save(plot_swipe_cost(prices), OUT / "swipe_cost.png")

    save(plot_on_campus(prices, band_draws=draw_assumptions()), OUT / "on_campus_cost_per_meal.png")
    with (OUT / "on_campus_cost_per_meal.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["meals_per_week", "cost_per_meal_boardplus_spent", "cost_per_meal_boardplus_unspent"])
        for m in range(1, FULL_WEEK + 1):
            w.writerow([m, round(resident_cost_per_meal(m, prices), 2),
                        round(resident_cost_per_meal(m, prices, count_boardplus=False), 2)])
    print("wrote figures/on_campus_cost_per_meal.csv")


if __name__ == "__main__":
    main()
