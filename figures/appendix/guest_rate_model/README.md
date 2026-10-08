# Archived: guest-rate model (before 2026-10-08)

Every figure and data table as it stood when meals not covered by a plan were priced at HUDS
guest rates, and "no plan" meant paying guest rates. That option turned out not to exist (a
student without a plan can't buy guest meals on their own; see CLAUDE.md), so these results are
superseded. They are kept to compare old and new.

To regenerate them exactly: `git checkout guest-rate-model`, then run `scripts/make_figures.py`
and `scripts/run_monte_carlo.py`.
