# Project Brief — Is Harvard's Meal Plan Worth It?

This file is the source of truth for the project. Read it fully before making changes. Ask the user before deviating from any decision below. This REPLACES an earlier brief about a restaurant recommender app; that project is cancelled.

## Assignment context

Course project. Requirement: a scientific/quantitative question investigated by having AI agents write and execute code as the primary mode of investigation, with results that can be checked. Sample projects included physics simulations, data pipelines, and reproducing published results. The instructor is flexible on domain but the work must be a real investigation with a hypothesis, model, data, and verifiable output. Not a product or app.

## Research question

Given realistic student eating patterns, what is the true cost per meal eaten under each Harvard dining option, and at what utilization does each plan beat eating off-campus or cooking in Cambridge?

Sub-questions:
1. For on-campus undergrads (mandatory unlimited plan): what does the plan implicitly cost per meal actually eaten, and how does that compare to what those meals would cost at guest rates, off campus, or cooked?
2. For non-resident undergrads (choice of 5/10/21 meals per week): which tier is optimal for which eating pattern, and how badly does weekly swipe forfeiture hurt the small plans?
3. For grad students (declining balance): what usage makes the Regular vs Deluxe plan worthwhile given the 10% discount and year-end forfeiture?

Working hypothesis: the small non-resident plans are priced at roughly the guest meal rate, so they only beat paying cash if nearly every swipe is used; the 21-meal plan and the unlimited plan are cheap per meal only for heavy dining-hall users.

## Data — VERIFY EACH VALUE IN CODE BY FETCHING THE PAGE, DON'T HARDCODE FROM THIS FILE

Pages to fetch:
- https://www.dining.harvard.edu/undergraduate-dining/meal-plans
- https://www.dining.harvard.edu/undergraduate-dining/faqs
- https://www.dining.harvard.edu/graduate-professional-dining/meal-plans

**Undergraduate resident plan (2026–27):** mandatory unlimited swipes at 13 dining halls for all undergrads living on campus. Includes $65 BoardPlus per semester (expires end of year). Annual board fee: a third-party site reports ~$8,268 for 2026; CONFIRM from Harvard College's official cost-of-attendance page before using.

**Non-resident undergrad plans (FY26–27, per term):**
- 5 meals/week: $1,538
- 10 meals/week: $3,060
- 21 meals/week: $4,406
- One swipe per meal period; unused meals forfeited weekly after Saturday dinner. Non-refundable.
- Fall term Sept 2 – Dec 19, Spring Jan 25 – May 15.

**Guest meal rates (2026–27, incl. 7% tax):** breakfast ~$10.84 (Houses) / ~$12.90 (Annenberg & Quincy Mon–Sat); brunch and lunch ~$17.30; dinner ~$21.40. Source: HUDS undergraduate FAQ page.

**Grad student GradPlus plan:** Regular $100/month, Deluxe $150/month, declining balance, 10% discount on purchases at HUDS cafes, unused balance forfeited at end of academic year. Some GSAS residents also

> **[INCOMPLETE — the brief was cut off here when pasted. The rest of this section and any later sections (e.g. build order) are still to come from the user.]**
