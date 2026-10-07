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
