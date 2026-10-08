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

**Undergraduate resident plan (2026–27):** mandatory unlimited swipes at 13 dining halls for all undergrads living on campus. Includes $65 BoardPlus per semester (expires end of year). Annual board fee: **$8,942 for 2026–27** (confirmed from Harvard College's official cost of attendance, listed as "Food": https://college.harvard.edu/financial-aid/how-aid-works). The ~$8,268 figure reported elsewhere is the 2024–25 value.

**Non-resident undergrad plans (FY26–27, per term):**
- 5 meals/week: $1,538
- 10 meals/week: $3,060
- 21 meals/week: $4,406
- One swipe per meal period; unused meals forfeited weekly after Saturday dinner. Non-refundable.
- Fall term Sept 2 – Dec 19, Spring Jan 25 – May 15.

**Guest meal rates (2026–27, incl. 7% tax):** breakfast ~$10.84 (Houses) / ~$12.90 (Annenberg & Quincy Mon–Sat); brunch and lunch ~$17.30; dinner ~$21.40. Source: HUDS undergraduate FAQ page. **Reference only — not an option a student can choose** (see "Guest meals are not an option" under Decisions).

**Grad student GradPlus plan:** Regular $100/month, Deluxe $150/month, declining balance, 10% discount on purchases at HUDS cafes, unused balance forfeited at end of academic year. Some GSAS residents also have a required Commons at Lehman Hall plan (~$3,190/yr, lunch and dinner weekdays).

**Off-campus alternatives (to collect in a later step):**
- Restaurant prices near Harvard Square / Central Square: a hand-collected sample of ~30 menus, with prices for typical student meals. Tag by meal type. (No Google Places API.)
- Grocery/cooking cost per meal: BLS or USDA food cost data for the Boston metro, plus a small basket priced at local stores (Star Market, Trader Joe's, Market Basket) if feasible.
- Meal delivery markup (optional).

**Validation data:** the user's own swipe history if it can be exported from the Harvard dining/Crimson Cash portal. Also consider a small survey of friends' weekly dining-hall meal counts.

## Method

1. **Data collection:** agent fetches and parses the HUDS pages and the official board fee, records values with source URLs and fetch dates in a `data/` folder. Step 1 covers only these; Cambridge restaurant and grocery prices are gathered in a separate later step.
2. **Deterministic model:** cost per meal eaten for each plan as a function of meals eaten per week by meal type, weeks on campus, and forfeiture rules. Pure, unit-tested functions.
3. **Monte Carlo simulation (secondary):** simulate thousands of students with varied habits — breakfast skipping rate, weekend-away frequency, eat-out frequency, cooking share — and varied assumptions, including **weeks per term, varied from about 14.5 to 16** (the result is sensitive to it: the 10-meal plan beats paying cash only above ~15.2 weeks and is never the cheapest option below ~16.1). Its job is now to show how sensitive the decision map (step 4) is to the model's assumptions, not to be the headline result.
4. **Decision map (main output):** for every combination of the three habit inputs (meals out per week, breakfasts skipped per week, weekends away per term), run every plan through the model and find the cheapest option and its dollar gap to the runner-up. Plot meals out vs breakfasts skipped with regions colored by the cheapest option, one panel per weekends-away level, with an optional "you are here" dot. Break-even points against (a) guest rates, (b) eating out at typical Cambridge prices, (c) cooking are read off the region boundaries. See "Decision map" below.
5. **Validation:** compare model prediction to the user's actual swipe history (or survey data). Report error.
6. **Write-up:** short report with figures (break-even curves, cost-per-meal distributions, tier recommendation by student type). Every figure reproducible from a script.

## Decision map (from instructor feedback)

**Current version (2026-10-08, after the no-guest-meals decision):** the main decision map is the cheapest option for an off-campus undergraduate by **cost of a meal not eaten at HUDS** (x, a blend of cooking and eating out, about $3–$40) and **HUDS meals missed per week** (y, 0–21), with 2 weekends away per term. Everyone eats 21 meals a week; missed meals are eaten elsewhere and paid for. The instructor's chart is one panel per option (no plan, 5-, 10-, 21-meal plan) coloured by total food spending per semester on a shared scale, plus this cheapest-option panel; drafts in `figures/drafts/`. Labeled markers for typical cooking cost, cheap takeout and sit-down meals use placeholder values until real prices are collected. The original three-habit map below is archived with the guest-rate model.

The main output of the project is a **decision map**: a plot where a student locates themselves by three habit inputs and reads off which plan is cheapest.

- **Inputs:** meals out per week (0–14), breakfasts skipped per week (0–7), weekends away per term (0–10).
- **Plots:** meals out vs breakfasts skipped, regions colored by the cheapest option, one panel per weekends-away level. Only options a student can actually choose between appear on the same map:
  - **Headline: off-campus undergrads** — non-resident 5/10/21 plans vs paying guest rates.
  - **Grad students** — GradPlus Regular/Deluxe vs paying cash at the cafe. Keep it, with its caveats: it depends on the estimated cafe meal price, and the 21-meal week is unrealistic for weekday cafes.
  - **No all-plans map in the results.** Mixing groups is misleading (GradPlus "wins" ~92% of it only because cafe meals are cheaper than dining-hall meals, and undergrads can't buy it). It appears only as a short note in `report.md` explaining this.
- **On-campus undergrads** have no choice (the unlimited plan is mandatory), so they get a separate chart instead of a map: cost per meal actually eaten vs meals eaten per week, with guest-rate prices as comparison lines.
- **Function:** takes the three inputs and returns the recommended plan and the dollar gap to the runner-up.
- **"You are here":** a way to plot a dot at a student's own inputs on the map.
- The Monte Carlo step stays, but is secondary: it shows how sensitive the map is to assumptions.

## Deliverables

- `data/` with raw fetched data + provenance
- `src/` model and simulation code, `tests/` unit tests
- `notebooks/` or `scripts/` that regenerate all figures
- `report.md` with findings, assumptions, limitations
- README explaining how to reproduce everything with one command

## Tech

Python 3.9+. pandas, numpy, matplotlib (or plotly), pytest. Optional: requests + BeautifulSoup for fetching HUDS pages. Keep it simple; no web app.

## Decisions already made

- Domain: Harvard dining, all three plan types (resident unlimited, non-resident tiers, grad declining balance).
- Off-campus comparison uses real Cambridge price data, not national averages alone.
- Everything must be reproducible; document every assumption in `report.md`.
- The earlier restaurant-recommender app and student-discount tracker are dropped. Do not build them.
- Step 1 (data collection) = HUDS pages + official board fee only. Off-campus prices are a separate later step.
- Restaurant prices come from a hand-collected sample of ~30 menus, not the Google Places API.
- Resident board fee for 2026–27 is $8,942 (official; see Data section).
- 21 meal times per week (7 breakfasts incl. weekend House breakfast, 5 lunches, 2 brunches, 7 dinners). Skipping weekend breakfast is handled by the breakfasts-skipped input.
- Term length = actual term dates minus spring break: fall 109/7 = 15.57 weeks, spring 111/7 − 1 = 14.86 weeks (computed from the CSV by `model.load_term_weeks`). A short first week counts as a fraction of a week.
- BoardPlus ($65/semester) is credited at face value; the on-campus chart also shows it unspent. The $65 is listed with 2025–26 dates and assumed to still apply.
- dining.harvard.edu blocks scripted requests (HTTP 403). HUDS pages are saved from a browser into `data/raw/manual/` and parsed by `scripts/fetch_prices.py`, which verifies each page's canonical URL.

### Guest meals are not an option (decided 2026-10-08)

- **Rule:** a student without a meal plan can't buy a guest meal unless accompanied by a Harvard student on a plan. Source: the user's own knowledge of HUDS rules; **to be confirmed with HUDS.** The saved FAQ is consistent but not explicit: it describes guest meals as something "students on the meal plan may host … and may pay for them with cash or BoardPlus"; the only case of affiliates paying the guest rate themselves is summer dining at Winthrop and Adams.
- **"No plan" means eating out in Cambridge or cooking.** Meals not covered by a plan's swipes are also eaten out or cooked, not bought at guest rates.
- **Guest rates stay only as a reference** ("what HUDS charges for a meal"), not as an option.
- **Until real prices are collected,** the price of a meal out is a variable (about $8–$40), and cooking is a separate cost per meal.
- **The guest-rate results are kept** (in `figures/appendix/`) so old and new can be compared.
- Graduate students are unaffected: HUDS cafés sell to anyone, so paying cash at the café is a real option.

## Open questions for the user

- Confirm with HUDS that a student without a plan can't buy guest meals on their own.
- Can the user export their own swipe history?
