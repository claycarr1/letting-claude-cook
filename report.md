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
The sensitivity check (below) treats three yes/no assumptions as coin flips with **50/50 odds**: whether the short first week gives full or partial swipes, whether meals eaten elsewhere come mostly from dinners or are spread across lunch, brunch and dinner, and whether breakfast is priced at the House ($10.84) or Annenberg/Quincy ($12.90) guest rate. BoardPlus spent or unspent is also 50/50 (it only affects the on-campus chart). Weeks per term are drawn uniformly between 14.5 and 16, separately for fall and spring. **The 50/50 odds are a deliberately neutral choice, not a measurement**; the stability percentages depend on them, and different odds would give different percentages.

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

For off-campus undergraduates choosing between the 5-meal plan and paying as you go, **the kind of meal you usually eat elsewhere matters as much as how many**:

- **If the meals you eat elsewhere are mostly dinners, lean toward paying as you go.** The 5-meal plan's swipes are worth the most on dinners ($21.40 at guest rates), so a student who eats dinner out has less to spend them on, and paying at the door for the lunches and brunches they do eat at HUDS ($17.30) is cheaper.
- **If they are mostly lunches, lean toward the 5-meal plan.** The student still eats most dinners at HUDS, so all five swipes go on the most expensive meal and the plan is good value.

`figures/meals_out_comparison.png` shows this for a student away 2 weekends a term. With meals out spread over lunch, brunch and dinner (the main map), the 5-meal plan is cheapest in 49 of the 120 squares, up to about 6 meals eaten elsewhere a week. With meals out taken from dinners first, it is cheapest in only 26, up to about 3 a week, and paying as you go takes over the rest. The example student (4 meals elsewhere, 3 breakfasts skipped) switches from the 5-meal plan to paying as you go.

The dinners-first case is part of the model and the Monte Carlo check. The lunches-first direction follows from the same reasoning but is not a separate option in the model.
