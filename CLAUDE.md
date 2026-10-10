# Project Brief — Is Harvard's Meal Plan Worth It?

This file is the source of truth for the project. Read it fully before making changes. Ask the user before deviating from any decision below. This REPLACES an earlier brief about a restaurant recommender app; that project is cancelled.

**Start here in a new session:** read "Current status" and "Next steps" at the end. Last updated 2026-10-09 (real restaurant prices in the model).

## Assignment context

Course project. Requirement: a scientific/quantitative question investigated by having AI agents write and execute code as the primary mode of investigation, with results that can be checked. Sample projects included physics simulations, data pipelines, and reproducing published results. The instructor is flexible on domain but the work must be a real investigation with a hypothesis, model, data, and verifiable output. Not a product or app.

## Research question

Given realistic student eating patterns, what is the true cost per meal eaten under each Harvard dining option, and at what utilization does each plan beat eating off-campus or cooking in Cambridge?

Sub-questions:
1. For on-campus undergrads (mandatory unlimited plan): what does the plan implicitly cost per meal actually eaten, and how does that compare to what those meals would cost off campus or cooked? **In scope again (2026-10-09, after briefly being dropped):** the resident plan is the 21-meal plan in this model (see "Resident plan = 21-meal plan"), so on-campus students are read off the 21-meal panel of the extra-cost chart (`figures/on_campus_extra_cost.png`).
2. For non-resident undergrads (choice of 5/10/21 meals per week): which tier is optimal for which eating pattern, and how badly does weekly swipe forfeiture hurt the small plans?
3. For grad students (declining balance): what usage makes the Regular vs Deluxe plan worthwhile given the 10% discount and year-end forfeiture?

Working hypothesis: the small non-resident plans are priced at roughly the guest meal rate, so they only beat paying cash if nearly every swipe is used; the 21-meal plan and the unlimited plan are cheap per meal only for heavy dining-hall users. *(Since 2026-10-08, "paying cash" means eating out or cooking — see "Guest meals are not an option".)*

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

**Guest meal rates (2026–27, incl. 7% tax):** breakfast ~$10.84 (Houses) / ~$12.90 (Annenberg & Quincy Mon–Sat); brunch and lunch ~$17.30; dinner ~$21.40. Source: HUDS undergraduate FAQ page. **Reference only — not an option a student can choose** (see "Guest meals are not an option").

**Grad student GradPlus plan:** Regular $100/month, Deluxe $150/month (fetched page: Regular $400 fall / $500 spring, Deluxe $600 / $750), declining balance, 10% discount on purchases at HUDS cafes, fall balance rolls into spring, unused balance forfeited at end of academic year. Some GSAS residents also have a required Commons at Lehman Hall plan (~$3,190/yr = $1,627 fall + $1,563 spring, lunch and dinner weekdays).

**Off-campus alternatives:**
- Restaurant prices near Harvard Square / Central Square: a hand-collected sample of ~30 meals (about 10 each breakfast/lunch/dinner), entered by the user in `data/hand_collected/restaurant_meals.csv` (instructions in its README). No Google Places API.
- Grocery/cooking cost per meal: **done** — USDA food plans (Aug 2026) with a BLS Northeast/U.S. price adjustment (`scripts/fetch_cooking_cost.py` → `data/cooking_cost.csv`, raw copies in `data/raw/usda/`, `data/raw/bls/`; computed in `src/cooking.py`), plus an optional basket priced at Star Market / Trader Joe's / Market Basket by the user in `data/hand_collected/grocery_basket.csv`.
- Meal delivery markup (optional).

**Validation data:** the user's own swipe history if it can be exported from the Harvard dining/Crimson Cash portal. Also consider a small survey of friends' weekly dining-hall meal counts.

## Method

1. **Data collection:** fetch and parse the HUDS pages and the official board fee; record values with source URLs and fetch dates in `data/`. **Done.** Cooking cost: done (2026-10-09). Restaurant prices: done (2026-10-09, `src/restaurants.py`).
2. **Deterministic model:** cost per meal eaten for each plan as a function of meals eaten per week by meal type, weeks on campus, and forfeiture rules. Pure, unit-tested functions. **Done**, including the 2026-10-08 change to outside prices.
3. **Monte Carlo simulation (secondary):** show how sensitive the decision map is to uncertain assumptions — not the headline result. It must vary **weeks per term from about 14.5 to 16** (fall and spring drawn separately), full vs partial first-week swipes, and on the current model the outside price and cooking share. Yes/no assumptions are 50/50 coin flips. **The existing Monte Carlo is on the superseded guest-rate model and must be rebuilt.**
4. **Decision map (main output):** see "Decision map" below. Current version: cheapest option by outside price × meals eaten at HUDS per week, led by a simpler three-price line chart.
5. **Validation:** compare model prediction to the user's actual swipe history (or survey data). Report error.
6. **Write-up:** short report with figures. Every figure reproducible from a script.

## Decision map (from instructor feedback)

The main output is a **decision map**: a plot where a student locates themselves and reads off which plan is cheapest.

**Current version (2026-10-09), in report order** — lead chart, decision map, spending by option, extra cost by option, swipe cost; then the "On-campus students" section; the grad chart near the end; on-campus cost per meal in the appendix. Off-campus charts (`src/outside_food.py`) use the axis labels **"Meals you'd eat at HUDS per week (if you had swipes)"** and **"Average cost of a meal not eaten at HUDS (cooking and eating out mixed)"** (2×2 grids: one shared x-label under both columns).
1. **Lead chart** (`figures/spending_at_three_prices.png`, `plot_lead`): three side-by-side line charts "If you mostly cook ($5.15/meal)", "If you get cheap takeout (~$13/meal)", "If you eat at sit-down places (~$30/meal)"; x = meals eaten at HUDS per week (0–21), y = food spending per semester, same y-scale on all three; one line per option, labelled at the line's end (no legend).
2. **Decision map** (`figures/decision_map_undergrad_offcampus.png`, `plot_main_map`): cheapest option for an off-campus undergraduate (no plan, 5-, 10-, 21-meal plan) by **cost of a meal not eaten at HUDS** (x-axis, about $3–$40) and **meals eaten at HUDS per week** (y-axis, 0–21). 2 weekends away per term.
3. **Spending by option** (`figures/spending_by_option.png`, `plot_spending`; was Draft B): 2×2 grid, one panel per option, colour = total food spending per semester in **$1,000 bands** (user's choice 2026-10-09, so nearby differences show), same scale across panels, labelled contour lines every $2,000 (labels kept off the swipe lines), colourbar on the right.
4. **Extra cost by option** (`figures/extra_cost_by_option.png`, `plot_extra_cost`; was Draft C): 2×2 grid, colour = how much more than the cheapest option per semester in 5 bands ($0 (cheapest), under $250, $250–1,000, $1,000–4,000, $4,000+); each panel outlines and labels its "Cheapest here" region.
- On both 2×2 charts, the 5- and 10-meal panels have a dashed line at 5 / 10 meals labelled **"Swipes run out here"**.
5. **Swipe cost** (`figures/swipe_cost.png`, `charts.plot_swipe_cost`): one swipe on each plan next to the three outside prices (Cooking, Cheap takeout, Sit-down, with the sample sizes). The guest-price bars were removed (2026-10-09).
6. **On-campus** (`figures/on_campus_extra_cost.png`, `plot_on_campus_extra`): the 21-meal panel of the extra-cost chart alone (see the On-campus bullet below).
- Draft A was dropped and `figures/drafts/` removed (in git history).
- **Markers:** "Cooking", "Cheap takeout", "Sit-down" are small labels on the x-axis (no dashed lines across the plot); `PRICE_MARKERS` in `src/outside_food.py`. **Cooking = $5.15, real** (from `cooking.cooking_cost_per_meal()`). **Cheap takeout = $12.66 and sit-down = $24.70, real** (mean out-the-door price of the 20 counter / 10 sit-down sample meals, `restaurants.average_price`). `PLACEHOLDER_MARKERS` is now empty; any name put back in it is shown as "~$13?" and hatched.
- **Grad students:** `figures/grad_cafe_spending.png` — cheapest option (no plan / GradPlus Regular / Deluxe) by yearly café spending, switch points $933 and $1,604 (independent of the estimated café price).
- **On-campus undergrads** (`figures/on_campus_extra_cost.png`, `outside_food.plot_on_campus_extra`): the 21-meal panel of the extra-cost chart on its own, same axes and colour steps; **compares against the cheapest of all four options** (including the 5-/10-meal plans on-campus students can't buy, read as "if you could choose") and keeps the computed takeaway title "The required on-campus plan only pays off if you eat most meals at HUDS and meals elsewhere would cost over $14" (both confirmed by the user 2026-10-09); "On-campus students" section in `report.md`. Supporting chart `figures/appendix/on_campus_cost_per_meal.png`: cost per meal eaten vs meals per week, guest prices as reference lines, BoardPlus spent and unspent, Monte Carlo range shaded.
- **No all-plans map** mixing student groups (GradPlus "wins" most of it only because café meals are cheaper and undergrads can't buy it); explained in a note in `report.md`.

**Archived version (guest-rate model, superseded):** three habit inputs — meals out per week (0–14), breakfasts skipped per week (0–7), weekends away per term (0–10) — with panels at 0, 5 and 10 weekends away, a "you are here" dot (`--you-are-here`, label "Example student", example 4 meals out / 3 breakfasts skipped / 2 weekends away), a stability map and a gap map. All in `figures/appendix/guest_rate_model/`. The code still exists (`decision_map.recommend`, `plot_you_are_here`, `monte_carlo.py`) and defaults to guest rates.

## Deliverables

- `data/` with raw fetched data + provenance
- `src/` model and simulation code, `tests/` unit tests
- `notebooks/` or `scripts/` that regenerate all figures
- `report.md` with findings, assumptions, limitations
- README explaining how to reproduce everything with one command

## Tech

Python 3.9+ (the machine has 3.9.6). Dependencies in a project virtualenv `.venv/` (gitignored): pytest, matplotlib (numpy comes with it); listed in `requirements.txt`. Data fetching uses only the standard library. Keep it simple; no web app.

## Decisions already made

**Project and scope**
- Domain: Harvard dining, all three plan types (resident unlimited, non-resident tiers, grad declining balance).
- The earlier restaurant-recommender app and student-discount tracker are dropped. Do not build them.
- Off-campus comparison uses real Cambridge price data, not national averages alone.
- Everything must be reproducible; document every assumption in `report.md`.

**Data**
- Step 1 (data collection) = HUDS pages + official board fee only. Off-campus prices are a separate later step.
- dining.harvard.edu blocks scripted requests (HTTP 403). HUDS pages are saved from a browser into `data/raw/manual/` and parsed by `scripts/fetch_prices.py`, which verifies each page's canonical URL.
- Resident board fee for 2026–27 is $8,942 (official; see Data section).
- Restaurant prices come from a hand-collected sample of ~30 meals, not the Google Places API. The user enters menu prices **before** tax and tip; code adds the **7% meals tax**, plus an **18% tip for sit-down** meals and **0% for counter service** (the `service` column).
- **Restaurant sample (done 2026-10-09):** 30 meals in `data/hand_collected/restaurant_meals.csv` (22 "Claude (web)" rows looked up online, 8 "CC" rows checked by the user). Out-the-door = menu × (1 + 7% tax + 18% tip on the **pre-tax** menu price for sit-down) — sit-down 1.25×, counter 1.07×. Markers use plain **means**: counter $12.66 (median $13.54), sit-down $24.70 (median $22.59). Breakfast/lunch/dinner averages ($14.09 / $17.27 / $18.25; by service too) are in `figures/restaurant_prices_summary.csv` and `report.md` but **not used in the charts** yet. `price_source` "news article" (Daily Provisions, Aug 2025) is accepted and kept (dropping it: counter $12.70); Joe's Pizza is the user's in-person estimate for 2 slices.
- **Cooking cost per meal (decided 2026-10-09):** USDA food plan weekly cost, average of the female and male 19–50 groups (Thrifty: 20–50), ÷ 21 meals. **Moderate-cost plan = the cooking marker ($5.15)**, range Thrifty–Liberal **$4.01–$6.42**. **Default: a student cooking alone (+20%, USDA's 1-person adjustment)**; roommates sharing (4-person, no adjustment, $4.29 moderate) is the lower case in `report.md`. **Regional adjustment: BLS Northeast vs U.S. average prices, +6.3%** (geometric mean over the 9 items BLS prices in both areas). BLS has no Boston food price levels (the Boston CPI measures change only), so "Boston" became "Northeast". Groceries only — no time, equipment or waste (in Limitations). Limitations also notes most on-campus students have limited kitchen access, so the cooking price is less realistic for them.
- Optional local grocery basket by the user.

**Model**
- 21 meal times per week (7 breakfasts incl. weekend House breakfast, 5 lunches, 2 brunches, 7 dinners). Skipping weekend breakfast is handled by the breakfasts-skipped input.
- Term length = actual term dates minus spring break: fall 109/7 = 15.57 weeks, spring 111/7 − 1 = 14.86 weeks (computed from the CSV by `model.load_term_weeks`). The short first week counts as a fraction of a week (4/7 fall, 6/7 spring) with that fraction of the swipes; the Monte Carlo also tries a full first-week allowance.
- BoardPlus ($65/semester) is credited at face value (resident plan = $4,406/term); the on-campus chart also shows it unspent ($4,471). The $65 is listed with 2025–26 dates and assumed to still apply.
- GradPlus meals are priced at `cafe_meal_price`, default **$12.50 — a placeholder estimate**, flagged in results, until real café prices are collected.
- Meals eaten elsewhere can be taken "spread" over lunch/brunch/dinner, "dinners first" or "lunches first" (`meals_out_from`).

**Resident plan = 21-meal plan (decided 2026-10-09)**
- The resident unlimited plan costs $8,942 − 2 × $65 BoardPlus = **$8,812 a year = 2 × $4,406, the 21-meal plan's price**, and with one swipe per meal period 21 swipes cover every meal HUDS serves. So in the model they are the same plan; `tests/test_on_campus.py` checks equal costs for every pattern, outside price and first-week rule, and on the real parsed prices. Holds only with BoardPlus counted as spent (unspent: +$130/yr).
- **Naming:** the 21-meal plan is "21-meal plan (= on-campus unlimited plan)" (`decision_map.NR21_NAME`) in legends, panel titles and the report; shorter "21-meal plan (= on-campus plan)" in tight direct labels.

**Guest meals are not an option (decided 2026-10-08)**
- **Rule (confirmed):** a student without a meal plan can't buy a dining-hall meal on their own at the guest rate, only as the guest of a Harvard student on a plan. **Confirmed by the user on 2026-10-08; who they asked and the date of that confirmation are still to be recorded.** The saved FAQ is consistent but not explicit: it describes guest meals as something "students on the meal plan may host … and may pay for them with cash or BoardPlus"; the only case of affiliates paying the guest rate themselves is summer dining at Winthrop and Adams.
- **"No plan" means eating out in Cambridge or cooking.** Meals not covered by a plan's swipes are also eaten out or cooked, not bought at guest rates.
- **Everyone eats 21 meals a week;** missed HUDS meals are eaten elsewhere and paid for. Only where they eat changes.
- **One "outside price" per meal**, a blend of cooking and eating out, is the x-axis (from about $3). It is a variable until real prices are collected.
- **Guest rates stay only as a reference** ("what HUDS charges for a meal"), not as an option.
- Weekends away fixed at **2 per term** for the new charts.
- **The guest-rate results are archived** in `figures/appendix/guest_rate_model/` with git tag `guest-rate-model` (local tag, not pushed) so old and new can be compared. Swipe-plan functions still default to guest rates when no outside price is given, so the archive reproduces.
- Graduate students are unaffected: HUDS cafés sell to anyone, so paying cash at the café is a real option.

**Monte Carlo**
- Yes/no assumptions are 50/50 coin flips (a neutral choice, noted in `report.md`); fall and spring weeks drawn separately from 14.5–16; fixed seed 2026; 2,000 runs, spread over CPU cores.
- The (guest-rate) Monte Carlo compared only meals out spread vs dinners first; lunches first was not part of it.

**Figures and report style**
- Plain plan names everywhere: "5-meal plan", "10-meal plan", "21-meal plan (= on-campus unlimited plan)", "No plan" (never "NR 5" / "Cash").
- Keep figures simple: few panels in the main text, full versions in `figures/appendix/`; each figure has a clear title, labelled axes and a one-line caption in `report.md`.
- Fixed colours by option: no plan blue, 5-meal aqua, 10-meal yellow, 21-meal orange (plus direct labels and region borders, because colour alone isn't enough).
- Toss-up squares on stability maps stay pale.
- **Figure rules (2026-10-08, every current figure; `src/style.py`, checked by `tests/test_figures.py`):** text at least 12 pt, panel titles 16 pt, main title 18 pt and a plain-language takeaway sentence (computed from the data where it quotes numbers); no footnote in the image — setup details and caveats go in the figure's caption in `report.md`. About 5 colour steps on banded charts, **except the spending chart, which uses $1,000 bands** (user's choice). The meals axis on off-campus charts is meals eaten at HUDS (not missed), labelled "Meals you'd eat at HUDS per week (if you had swipes)".
- The 10-meal yellow and 21-meal orange fail the normal-vision colour-difference check (ΔE 13.7 < 15); kept because the colours are fixed, with direct labels and borders as the secondary cue. Ask the user before changing them.
- The archived guest-rate figures in `figures/appendix/guest_rate_model/` were **not** restyled; they stay frozen as a record of the superseded model.
- `meal_type_savings.png` (archived) notes it compares only the 5-meal plan with no plan.

## Current status (2026-10-09)

- **Cooking cost done:** `scripts/fetch_cooking_cost.py` → `data/cooking_cost.csv` (USDA Aug 2026 PDFs parsed with the standard library; BLS API v1); `--offline` re-parses the saved copies.
- **Step 1 done:** `scripts/fetch_prices.py` → `data/huds_prices.csv` (every value with source URL, fetch date and the quoted page text).
- **Model done and tested:** `src/model.py` (plans, outside prices, term calendar), `src/decision_map.py` (habit patterns, yearly costs, `outside_price` and `no_plan`), `src/outside_food.py` (current model: full yearly food bill, cheapest option, all off-campus figures), `src/cooking.py` (cooking cost per meal), `src/style.py` (figure rules), `src/on_campus.py`, `src/charts.py`, `src/monte_carlo.py` (guest-rate legacy). **131 tests pass** (`.venv/bin/python -m pytest`).
- **Current figures** (`scripts/make_figures.py`): lead chart, decision map + CSV, spending by option, extra cost by option, swipe cost, on-campus extra cost, grad café spending; appendix: on-campus cost per meal + CSV. Captions in `report.md`.
- **First results on the current model** (in `report.md`; markers $5.15 / $12.66 / $24.70 — at both cooking and takeout prices no plan is cheapest for everyone; at sit-down, 21-meal 15+ HUDS meals/week, 10-meal 10–14, 5-meal 5–9, no plan 0–4): no plan is cheapest for everyone below $14.33 a meal and in 54% of the chart; the 21-meal plan wins for heavy HUDS users from $14.33 (every meal) to ~$20 (15 meals/week); the **10-meal plan now wins** for ~9–14 HUDS meals/week from $20.12; the 5-meal plan for ~3–13 from $20.22. Picking the wrong option costs up to $7,894 a semester. At the real cooking price ($5.15) no plan is cheapest for everyone.
- **`report.md`:** scope note, results, numbered figure captions, assumptions (incl. cooking cost), Limitations, Graduate students, on-campus appendix, plus the archived guest-rate sections (marked superseded). Not final.
- **Restaurant sample done** (30 meals); `grocery_basket.csv` (optional) still empty.
- **Not done yet:** Monte Carlo on the new model, validation, README, final report.

## Next steps (in order)

1. ~~Clean up Drafts B and C~~ — done 2026-10-08 (see "Decision map").
2. ~~Fetch the cooking cost per meal~~ — done 2026-10-09 ($5.15 marker in the model).
3. ~~Restaurant meals~~ — done 2026-10-09 (real markers in every chart). Still to decide: **separate breakfast/lunch/dinner outside prices** (counter lunches average $14.71, above the $14.33 at which the 21-meal plan starts to win, so it could matter).
4. **Rebuild the Monte Carlo on the current model** (outside price, cooking share, weeks per term 14.5–16, first-week swipes) and its stability/assumption figures.
5. **Update the remaining figures** for the current model as needed (e.g. example student; meal-type chart if per-meal-type prices are used).
6. Validation (swipe history or survey), README with one-command reproduction, final `report.md`.

## Open questions for the user

- Who confirmed the guest-meal rule, and when? (Record it in "Guest meals are not an option" and `report.md`.)
- Can the user export their own swipe history?

## How to run

- Tests: `.venv/bin/python -m pytest`
- Re-parse HUDS pages: `python3 scripts/fetch_prices.py` (uses browser-saved pages in `data/raw/manual/`)
- Cooking cost data: `python3 scripts/fetch_cooking_cost.py` (downloads USDA + BLS; `--offline` re-parses `data/raw/usda/`, `data/raw/bls/`)
- Current figures: `.venv/bin/python scripts/make_figures.py`
- Legacy guest-rate Monte Carlo (writes into the archive): `.venv/bin/python scripts/run_monte_carlo.py`
- Archived guest-rate version: `git checkout guest-rate-model`
