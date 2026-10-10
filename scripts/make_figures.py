#!/usr/bin/env python3
"""Generate every current figure (PNG) and its data table (CSV) in figures/.

Usage:
  .venv/bin/python scripts/make_figures.py

Current model (from 2026-10-08): no guest meals; meals not eaten at HUDS are eaten out or cooked
at an outside price (see src/outside_food.py). Figure rules (text size, titles) are in src/style.py.
Figures (figures/), in report order:
  restaurant_prices_summary.csv          out-the-door restaurant prices by service and meal type (feeds the markers)
  spending_at_three_prices.png           lead chart: spending per semester vs HUDS meals, at 3 outside prices
  decision_map_undergrad_offcampus.png/.csv  cheapest option by outside price x HUDS meals eaten
  spending_by_option.png                 spending per semester under each option (5 bands, contours)
  extra_cost_by_option.png               how much more each option costs than the cheapest
  swipe_cost.png                         cost of one swipe on each plan vs the three outside prices
  on_campus_extra_cost.png               on-campus students: the required plan (= 21-meal plan) vs their best option
  grad_cafe_spending.png                 graduate students: cheapest option by yearly cafe spending
Appendix (figures/appendix/):
  on_campus_cost_per_meal.png/.csv       the required unlimited plan's cost per meal eaten
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
from restaurants import summary_rows  # noqa: E402
from outside_food import (  # noqa: E402
    plot_extra_cost,
    plot_lead,
    plot_main_map,
    plot_on_campus_extra,
    plot_spending,
    write_grid_csv,
)

OUT = ROOT / "figures"
APPENDIX = OUT / "appendix"


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    prices = load_prices()
    OUT.mkdir(exist_ok=True)

    def save(fig, path):
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        print(f"wrote {path.relative_to(ROOT)}")

    with (OUT / "restaurant_prices_summary.csv").open("w", newline="") as f:
        rows = summary_rows()
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote figures/restaurant_prices_summary.csv")
    save(plot_lead(prices), OUT / "spending_at_three_prices.png")
    save(plot_main_map(prices), OUT / "decision_map_undergrad_offcampus.png")
    write_grid_csv(prices, OUT / "decision_map_undergrad_offcampus.csv")
    save(plot_spending(prices), OUT / "spending_by_option.png")
    save(plot_extra_cost(prices), OUT / "extra_cost_by_option.png")
    save(plot_swipe_cost(prices), OUT / "swipe_cost.png")
    save(plot_on_campus_extra(prices), OUT / "on_campus_extra_cost.png")
    save(plot_grad_spending(prices), OUT / "grad_cafe_spending.png")

    save(plot_on_campus(prices, band_draws=draw_assumptions()), APPENDIX / "on_campus_cost_per_meal.png")
    with (APPENDIX / "on_campus_cost_per_meal.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["meals_per_week", "cost_per_meal_boardplus_spent", "cost_per_meal_boardplus_unspent"])
        for m in range(1, FULL_WEEK + 1):
            w.writerow([m, round(resident_cost_per_meal(m, prices), 2),
                        round(resident_cost_per_meal(m, prices, count_boardplus=False), 2)])
    print("wrote figures/appendix/on_campus_cost_per_meal.csv")


if __name__ == "__main__":
    main()
