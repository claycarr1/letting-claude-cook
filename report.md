# Is Harvard's Meal Plan Worth It?

*Draft — sections are added as each step is completed.*

## Note: why there is no single map of every plan

An early version put every plan (resident unlimited, non-resident 5/10/21, GradPlus Regular/Deluxe) and the pay-at-the-door baseline on one decision map. GradPlus came out cheapest in about 92% of it. That result is misleading for two reasons:

1. **Different groups can buy different plans.** Undergraduates can't buy GradPlus, and on-campus undergraduates must take the unlimited plan. A map that recommends GradPlus to an undergraduate is recommending something they can't buy.
2. **Different plans are spent in different places.** GradPlus is spent at HUDS cafes, priced here at an estimated $12.50 a meal, while the undergraduate plans and guest rates are for dining-hall meals at $10.84–$21.40. GradPlus "wins" mostly because cafe meals are cheaper, not because the plan is a better deal.

The results therefore use one map per group of students who face the same choice: off-campus undergraduates (the headline) and graduate students. On-campus undergraduates, who have no choice, get a cost-per-meal chart instead. `src/decision_map.py` still supports the combined view (`group="all"`) for reference.

## Assumptions

### Meal times: 21 per week
HUDS's 2026-27 guest-meal price list names every meal period: breakfast at the Houses every day (and at Annenberg on Sunday; Annenberg and Quincy Monday–Saturday), lunch Monday–Friday, brunch Saturday and Sunday, and dinner every day. That is 7 breakfasts + 5 lunches + 2 brunches + 7 dinners = **21 meal times per week**, matching the 21-meal non-resident plan. A student who skips weekend breakfast and treats brunch as their first meal of the day is covered by the "breakfasts skipped per week" input, so the model keeps 21.

### Term length
Weeks of dining come from the non-resident plan's term dates on the HUDS meal-plans page:

| Term | Dates | Days | Weeks used |
|---|---|---|---|
| Fall 2026 | Wed Sept 2 – Sat Dec 19 | 109 | 109 / 7 = **15.57** |
| Spring 2027 | Mon Jan 25 – Sat May 15 | 111 | 111 / 7 − 1 = **14.86** |
| Year | | | **30.43** |

- **Spring break:** the HUDS FAQ says dining halls close for spring break, but the saved pages don't give its dates, so one full week is taken off spring.
- **Thanksgiving:** not removed. Dining halls serve dinner on Thanksgiving (the guest dinner rate "includes Thanksgiving"); a student who goes home enters it as a weekend away.
- **Short first week:** both terms start mid-week (fall on a Wednesday, spring on a Monday), and swipes reset after Saturday dinner. The short week counts as a fraction of a week (4/7 in fall, 6/7 in spring): the student eats that fraction of their usual meals, and a non-resident plan gets that fraction of its weekly swipes. The HUDS pages don't say whether the first week carries a full allowance; if it does, the small plans are slightly better value than modelled.
- **Why it matters:** the 10-meal plan beats paying guest rates only if a term has more than 15.17 weeks (3,060 ÷ 201.70, the most 10 swipes a week can be worth) and is never the cheapest option below about 16.1 weeks. With the calendar above it beats paying cash for some heavy eaters (in fall) but is still never the cheapest option. The Monte Carlo step varies weeks per term from 14.5 to 16.

### BoardPlus
Resident undergraduates get $65 of BoardPlus per semester ($130 per year), spendable at HUDS cafes, House grilles and on guest meals; it can't be topped up and expires at the end of the school year. **The $65 is listed on the HUDS FAQ alongside 2025–26 dates; it is assumed to still apply in 2026–27.** Results credit it at face value (treated as fully spent), so the resident plan costs $4,471 − $65 = $4,406 per term. The on-campus chart also shows the plan with BoardPlus unspent ($4,471 per term); the difference is about 1.5%.

### Monte Carlo odds: 50/50
The sensitivity check (below) treats three yes/no assumptions as coin flips with **50/50 odds**: whether the short first week gives full or partial swipes, whether meals eaten elsewhere come mostly from dinners or are spread across lunch, brunch and dinner (the model's third setting, lunches first, is not part of the Monte Carlo check), and whether breakfast is priced at the House ($10.84) or Annenberg/Quincy ($12.90) guest rate. BoardPlus spent or unspent is also 50/50 (it only affects the on-campus chart). Weeks per term are drawn uniformly between 14.5 and 16, separately for fall and spring. **The 50/50 odds are a deliberately neutral choice, not a measurement**; the stability percentages depend on them, and different odds would give different percentages.

## Sensitivity check (Monte Carlo)

`scripts/run_monte_carlo.py` redraws the off-campus undergraduate map 2,000 times (seed 2026), each time with the assumptions above drawn at random, and records how often each square's cheapest plan matches the main map. Outputs: `figures/stability_map_undergrad_offcampus.png` and `.csv`, `figures/monte_carlo_draws.csv`, `figures/monte_carlo_summary.json`.

- **Most of the map is solid.** 806 of 1,320 squares (61%) keep the same cheapest plan in at least 95% of runs; 153 are 80–95%; 361 (27%) are below 80%. Averaged over all squares, the main map's answer holds 86% of the time.
- **The uncertain zone is the 5-meal plan vs paying as you go**, at about 3–7 lunches/brunches/dinners eaten elsewhere per week. 334 of the 361 shaky squares are a choice between those two. The money at stake there is small: on the main map, the cheapest option in those squares saves a median of $63 a year (at most $180) over the runner-up.
- **Paying as you go (8+ meals elsewhere) and the 21-meal plan (eating nearly everything) are robust**: 96% and 95% average stability.
- **Which meals you skip matters most.** If meals eaten elsewhere are mostly dinners, the main map's answer holds in 81% of squares, against 93% if they are spread out. Dinners are the meals the 5-meal plan's swipes are worth most on, so eating dinner elsewhere makes paying as you go relatively cheaper. Term length, first-week swipes and breakfast price each move agreement by only 1–3 percentage points.
- **The 10-meal plan never won a single square in any of the 2,000 runs.**
- **Example student** (4 meals elsewhere, 3 breakfasts skipped, 2 weekends away): the 5-meal plan stays cheapest in 59% of runs; otherwise paying as you go wins. With meals out taken from dinners first, the 5-meal plan costs the same ($6,780) but paying as you go drops from $6,937 to $6,696 a year, because the student now eats 3 dinners and 7 lunches/brunches a week at HUDS instead of 5 and 5.
- **On-campus undergraduates:** across the runs, the unlimited plan beats paying the guest dinner price above 13.2–14.1 meals a week, and the guest lunch price above 16.3–17.4 meals a week (5th–95th percentile). The shaded band on `figures/on_campus_cost_per_meal.png` shows the range of cost per meal.

### Practical advice: which meals you eat elsewhere

For off-campus undergraduates choosing between the 5-meal plan and paying as you go, **the kind of meal you usually eat elsewhere matters as much as how many**. The model has three settings for this: meals out spread over lunch, brunch and dinner (the main map), taken from dinners first, or taken from lunches first (then brunches, then dinners).

- **If the meals you eat elsewhere are mostly dinners, lean toward paying as you go.** The 5-meal plan's swipes are worth the most on dinners ($21.40 at guest rates), so a student who eats dinner out has less to spend them on, and paying at the door for the lunches and brunches they do eat at HUDS ($17.30) is cheaper. Across the whole map, the 5-meal plan is cheapest in 272 of 1,320 squares, down from 534 on the main map.
- **If they are mostly lunches, lean toward the 5-meal plan.** The student still eats most dinners at HUDS, so all five swipes go on the most expensive meal and the plan is good value. The 5-meal plan is cheapest in 786 of 1,320 squares.

For a student away 2 weekends a term, the three settings give:

| Meals eaten elsewhere | Squares where the 5-meal plan is cheapest (of 120) | It wins up to about … meals elsewhere a week | Example student (4 elsewhere, 3 breakfasts skipped) |
|---|---|---|---|
| Spread out (main map) | 49 | 6 | 5-meal plan, $156 a year cheaper than paying as you go |
| Mostly dinners | 26 | 3 | Paying as you go, $84 a year cheaper |
| Mostly lunches | 72 | 9 | 5-meal plan, $180 a year cheaper |

For the example student, the 5-meal plan's yearly cost changes only a little ($6,780 spread or dinners first, $6,918 lunches first). The bigger swing is in paying as you go, which depends on what they still eat at HUDS: $6,937 spread out, $6,696 dinners first (they eat cheaper lunches and brunches at HUDS), and $7,098 lunches first (they eat their dinners at HUDS).

`figures/meal_type_savings.png` shows why, one meal type at a time. Starting from a student who eats every meal at HUDS, skipping breakfasts or lunches/brunches leaves the 5-meal plan's advantage unchanged (about $180 a year), because those meals were paid at the door under both options. Skipping dinners is different: once fewer than about 5 dinners a week are left, the swipes move onto cheaper lunches and the advantage falls, reaching $0 at about 3.3 dinners skipped a week and -$444 when all 7 are skipped.

**The Monte Carlo check only compared spread-out vs dinners-first** (50/50). Lunches first is not part of it, so the stability percentages above say nothing about it; it is shown here as a separate, deterministic comparison.

### How much is at stake

For a student away 2 weekends a term, picking the right option near the borders between plans usually saves little (a median of $36 a year, and under $150 in three-quarters of border squares), while at the edges it saves a lot: $1,400–3,100 a year for students who eat almost nothing at HUDS, and about $1,160 a year (the 21-meal plan) for one who eats almost everything.

## Supporting figures

All made by `scripts/make_figures.py` (the last one reads the Monte Carlo summary written by `scripts/run_monte_carlo.py`). Full-detail versions are in `figures/appendix/`: the decision and stability maps at every weekends-away level (0–10), the graduate decision map, and the map of the dollar gap between the cheapest and second-cheapest option.

- **`figures/decision_map_undergrad_offcampus.png`** — The cheapest option for off-campus undergraduates by meals eaten elsewhere and breakfasts skipped, at 0, 5 and 10 weekends away per term.
- **`figures/stability_map_undergrad_offcampus.png`** — The same three panels, faded where the Monte Carlo runs often disagree with the main map.
- **`figures/grad_cafe_spending.png`** — For graduate students, the cheapest option by how much they would spend at HUDS cafés in a year: no plan below $933, GradPlus Regular from $933 to $1,604, GradPlus Deluxe above $1,604 (this does not depend on the estimated cafe meal price).
- **`figures/meal_type_savings.png`** — How much cheaper the 5-meal plan is than paying at the door as one type of meal is skipped: skipping breakfasts or lunches leaves it about $180 a year ahead, skipping more than about 3 dinners a week puts it behind.

- **`figures/savings_vs_no_plan.png`** — How much each off-campus plan saves per year compared to no plan, against meals eaten at HUDS per week (every meal type cut evenly, 2 weekends away per term): the 5-meal plan starts saving at about 11 meals a week, the 21-meal plan at about 18, and the 10-meal plan never rises above $0.
- **`figures/swipe_cost.png`** — What one swipe costs on each off-campus plan if every swipe is used ($20.22 on the 5-meal plan, $20.11 on the 10-meal, $13.79 on the 21-meal), drawn as dashed lines across the guest prices: only dinner ($21.40) rises above the 5- and 10-meal lines, while lunch, brunch and dinner all rise above the 21-meal line.
- **`figures/assumption_effects.png`** — From the Monte Carlo runs, how much more of the off-campus map changes its answer under one setting of each assumption than the other: which meals are eaten elsewhere matters most (11.9 percentage points), far more than weeks per term (2.6), first-week swipes (1.5) or breakfast price (1.0).
