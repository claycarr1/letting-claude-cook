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

**Guest meal rates (2026–27, incl. 7% tax):** breakfast ~$10.84 (Houses) / ~$12.90 (Annenberg & Quincy Mon–Sat); brunch and lunch ~$17.30; dinner ~$21.40. Source: HUDS undergraduate FAQ page.

**Grad student GradPlus plan:** Regular $100/month, Deluxe $150/month, declining balance, 10% discount on purchases at HUDS cafes, unused balance forfeited at end of academic year. Some GSAS residents also have a required Commons at Lehman Hall plan (~$3,190/yr, lunch and dinner weekdays).

**Off-campus alternatives (to collect in a later step):**
- Restaurant prices near Harvard Square / Central Square: a hand-collected sample of ~30 menus, with prices for typical student meals. Tag by meal type. (No Google Places API.)
- Grocery/cooking cost per meal: BLS or USDA food cost data for the Boston metro, plus a small basket priced at local stores (Star Market, Trader Joe's, Market Basket) if feasible.
- Meal delivery markup (optional).

**Validation data:** the user's own swipe history if it can be exported from the Harvard dining/Crimson Cash portal. Also consider a small survey of friends' weekly dining-hall meal counts.

## Method

1. **Data collection:** agent fetches and parses the HUDS pages and the official board fee, records values with source URLs and fetch dates in a `data/` folder. Step 1 covers only these; Cambridge restaurant and grocery prices are gathered in a separate later step.
2. **Deterministic model:** cost per meal eaten for each plan as a function of meals eaten per week by meal type, weeks on campus, and forfeiture rules. Pure, unit-tested functions.
3. **Monte Carlo simulation:** simulate thousands of students with varied habits — breakfast skipping rate, weekend-away frequency, eat-out frequency, cooking share, term length. Compute total food cost per term under each plan vs. the no-plan alternative.
4. **Break-even analysis:** for each plan, the utilization at which it beats (a) guest rates, (b) eating out at typical Cambridge prices, (c) cooking. Sensitivity analysis on the key assumptions.
5. **Validation:** compare model prediction to the user's actual swipe history (or survey data). Report error.
6. **Write-up:** short report with figures (break-even curves, cost-per-meal distributions, tier recommendation by student type). Every figure reproducible from a script.

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
- dining.harvard.edu blocks scripted requests (HTTP 403). HUDS pages are saved from a browser into `data/raw/manual/` and parsed by `scripts/fetch_prices.py`, which verifies each page's canonical URL.

## Open questions for the user

- Can the user export their own swipe history?
