"""Hand-worked checks for src/decision_map.py (2026-27 prices pinned in test_model.PRICES).

Most checks use two 15-week terms (TW15) so the arithmetic stays simple; the calendar
tests at the bottom use the real term lengths from the CSV.
"""

import pytest

from decision_map import annual_costs, habits_to_patterns, recommend
from model import load_term_weeks
from test_model import PRICES

TW15 = {"fall": 15, "spring": 15}


def test_habits_to_patterns():
    # 7 meals out = half of the 14 non-breakfast meals; 2 breakfasts skipped.
    normal, away = habits_to_patterns(7, 2)
    assert (normal.breakfast, normal.lunch, normal.brunch, normal.dinner) == (5, 2.5, 1, 3.5)
    # A weekend away drops both brunches and 2 of 7 days' breakfasts and dinners.
    assert away.brunch == 0
    assert away.breakfast == pytest.approx(5 * 5 / 7)
    assert away.dinner == pytest.approx(3.5 * 5 / 7)
    assert away.lunch == 2.5


def test_full_week_undergrad():
    # Every HUDS meal, no weekends away. NR 21: 2 x 4406 = 8812.
    # NR 5: swipes on 5 dinners; cash for 2 dinners + 5 lunches + 2 brunches + 7 breakfasts
    #   = 42.80 + 86.50 + 34.60 + 75.88 = 239.78/wk x 15 = 3596.70; term 5134.70; year 10269.40.
    r = recommend(0, 0, 0, PRICES, "undergrad_offcampus", term_weeks=TW15)
    assert r.plan == "nr21" and r.annual_cost == 8812
    assert r.runner_up == "nr5" and r.gap == pytest.approx(1457.40)


def test_nr5_vs_cash_boundary():
    # 6 meals out: 4 dinners, 2.857 lunches, 1.143 brunches. Swipes: 4 dinners + 1 lunch/brunch,
    #   worth 85.60 + 17.30 = 102.90/wk x 15 = 1543.50 > 1538 -> NR 5 wins by 5.50/term = 11.00/yr.
    r = recommend(6, 7, 0, PRICES, "undergrad_offcampus", term_weeks=TW15)
    assert r.plan == "nr5" and r.runner_up == "cash_guest" and r.gap == pytest.approx(11.00)
    # 7 meals out: 3.5 dinners + 1.5 lunch/brunch on swipes = 74.90 + 25.95 = 100.85/wk
    #   x 15 = 1512.75 < 1538 -> paying cash is 25.25/term = 50.50/yr cheaper.
    r = recommend(7, 7, 0, PRICES, "undergrad_offcampus", term_weeks=TW15)
    assert r.plan == "cash_guest" and r.gap == pytest.approx(50.50)


def test_nr10_never_beats_cash():
    # The best 10 swipes a week can do is 7 dinners + 3 lunches = 149.80 + 51.90 = 201.70/wk,
    # x 15 = 3025.50 per term -- less than the 3060 plan price. So paying cash always wins.
    for weekends in (0, 5, 10):
        for meals_out in range(15):
            for skipped in range(8):
                c = annual_costs(meals_out, skipped, weekends, PRICES, ["nr10", "cash_guest"], term_weeks=TW15)
                assert c["cash_guest"] < c["nr10"]


def test_weekend_away_weeks_costed_separately():
    # NR 5, 0 meals out, all breakfasts skipped, 1 weekend away per term.
    # Home week: 7 dinners, 5 lunches, 2 brunches; swipes on 5 dinners, cash for 2 dinners + 5 lunches
    #   + 2 brunches = 42.80 + 86.50 + 34.60 = 163.90, for 14 weeks = 2294.60.
    # Away week: 5 dinners, 5 lunches; swipes on the dinners, cash for 5 lunches = 86.50.
    # Term = 1538 + 2294.60 + 86.50 = 3919.10; year = 7838.20.
    c = annual_costs(0, 7, 1, PRICES, ["nr5"], term_weeks=TW15)
    assert c["nr5"] == pytest.approx(7838.20)


def test_grad_full_week():
    # 21 meals/wk x 15 x 12.50 (estimate) = 3937.50 per term in cash, 7875 per year.
    # Each GradPlus balance is fully spent, saving 10% of what it buys: Regular saves
    # (400 + 500) / 0.9 x 0.1 = 100, Deluxe (600 + 750) / 0.9 x 0.1 = 150.
    r = recommend(0, 0, 0, PRICES, "grad", term_weeks=TW15)
    assert r.costs == pytest.approx({"gp_regular": 7775, "gp_deluxe": 7725, "cash_cafe": 7875})
    assert r.plan == "gp_deluxe" and r.gap == pytest.approx(50)


def test_no_meals_at_all():
    # 14 meals out and every breakfast skipped: nothing eaten at HUDS, so paying cash costs 0.
    r = recommend(14, 7, 10, PRICES, "undergrad_offcampus", term_weeks=TW15)
    assert r.plan == "cash_guest" and r.annual_cost == 0
    assert r.runner_up == "nr5" and r.gap == 2 * 1538


def test_resident_ties_nr21_on_the_all_map():
    c = annual_costs(0, 0, 0, PRICES, ["resident", "nr21"], term_weeks=TW15)
    assert c["resident"] == c["nr21"] == 8812


@pytest.mark.parametrize("args", [(15, 0, 0), (0, 8, 0), (0, 0, 11), (-1, 0, 0)])
def test_inputs_out_of_range(args):
    with pytest.raises(ValueError):
        recommend(*args, PRICES)


def test_unknown_group():
    with pytest.raises(ValueError):
        recommend(0, 0, 0, PRICES, "faculty", term_weeks=TW15)


def test_dinners_first_patterns():
    # 4 meals out, dinners first: 3 dinners left, all 5 lunches and 2 brunches.
    normal, away = habits_to_patterns(4, 3, "dinners_first")
    assert (normal.breakfast, normal.lunch, normal.brunch, normal.dinner) == (4, 5, 2, 3)
    assert away.dinner == pytest.approx(3 * 5 / 7) and away.brunch == 0
    # 10 meals out: no dinners; the other 3 come off lunches and brunches in proportion (5:2),
    # leaving 4/7 of each: 5 x 4/7 lunches and 2 x 4/7 brunches.
    normal, _ = habits_to_patterns(10, 0, "dinners_first")
    assert normal.dinner == 0
    assert normal.lunch == pytest.approx(20 / 7) and normal.brunch == pytest.approx(8 / 7)


def test_lunches_first_patterns():
    # 4 meals out, lunches first: 1 lunch left, both brunches, all 7 dinners.
    normal, away = habits_to_patterns(4, 3, "lunches_first")
    assert (normal.breakfast, normal.lunch, normal.brunch, normal.dinner) == (4, 1, 2, 7)
    assert away.dinner == pytest.approx(5) and away.brunch == 0 and away.lunch == 1
    # 6 meals out: no lunches, 1 brunch; 9 meals out: no lunches or brunches, 5 dinners.
    six, _ = habits_to_patterns(6, 0, "lunches_first")
    assert (six.lunch, six.brunch, six.dinner) == (0, 1, 7)
    nine, _ = habits_to_patterns(9, 0, "lunches_first")
    assert (nine.lunch, nine.brunch, nine.dinner) == (0, 0, 5)


def test_example_student_lunches_first():
    # Example student (4 meals out, 3 breakfasts skipped, 2 weekends away), real calendar,
    # meals out taken from lunches first.
    # Home week: 4 breakfasts, 1 lunch, 2 brunches, 7 dinners.
    #   5-meal plan: swipes on 5 dinners; cash for 2 dinners + 1 lunch + 2 brunches + 4 breakfasts
    #     = 42.80 + 17.30 + 34.60 + 43.36 = 138.06.
    #   Paying as you go: 43.36 + 17.30 + 34.60 + 149.80 = 245.06.
    # Away week: 20/7 breakfasts, 1 lunch, 5 dinners.
    #   5-meal plan: swipes on the 5 dinners; cash for 1 lunch + 20/7 breakfasts = 17.30 + 30.9714 = 48.2714.
    #   Paying as you go: 30.9714 + 17.30 + 107.00 = 155.2714.
    # 185/7 home weeks and 4 away weeks over the year:
    #   5-meal plan: 3076 + 138.06 x 185/7 + 48.2714 x 4 = 3076 + 3648.73 + 193.09 = 6917.81
    #   Paying as you go: 245.06 x 185/7 + 155.2714 x 4 = 6476.59 + 621.09 = 7097.67
    # So the 5-meal plan wins by 179.86 (vs losing by 83.72 with dinners first).
    c = annual_costs(4, 3, 2, PRICES, ["nr5", "cash_guest"], meals_out_from="lunches_first")
    assert c["nr5"] == pytest.approx(6917.81, abs=0.05)
    assert c["cash_guest"] == pytest.approx(7097.67, abs=0.05)
    r = recommend(4, 3, 2, PRICES, "undergrad_offcampus", meals_out_from="lunches_first")
    assert r.plan == "nr5" and r.gap == pytest.approx(179.86, abs=0.05)


def test_example_student_dinners_first():
    # Example student (4 meals out, 3 breakfasts skipped, 2 weekends away), real calendar
    # (fall 15 4/7 weeks, spring 14 6/7), meals out taken from dinners first.
    # Home week: 4 breakfasts, 5 lunches, 2 brunches, 3 dinners.
    #   5-meal plan: swipes on 3 dinners + 2 lunches; cash for 3 lunches + 2 brunches + 4 breakfasts
    #     = 86.50 + 43.36 = 129.86.
    #   Paying as you go: 43.36 + 86.50 + 34.60 + 64.20 = 228.66.
    # Away week: 20/7 breakfasts, 5 lunches, 15/7 dinners.
    #   5-meal plan: swipes on 15/7 dinners + 20/7 lunches; cash for 15/7 lunches + 20/7 breakfasts
    #     = 37.0714 + 30.9714 = 68.0429.
    #   Paying as you go: 30.9714 + 86.50 + 45.8571 = 163.3286.
    # Home weeks: fall 13 4/7, spring 12 6/7 (26 3/7 in total); 2 away weeks per term (4 in total).
    #   5-meal plan: 2 x 1538 + 129.86 x 185/7 + 68.0429 x 4 = 3076 + 3431.98 + 272.17 = 6780.16
    #   Paying as you go: 228.66 x 185/7 + 163.3286 x 4 = 6043.16 + 653.31 = 6696.47
    c = annual_costs(4, 3, 2, PRICES, ["nr5", "cash_guest"], meals_out_from="dinners_first")
    assert c["nr5"] == pytest.approx(6780.16, abs=0.05)
    assert c["cash_guest"] == pytest.approx(6696.47, abs=0.05)
    # With meals out spread, the 5-meal plan costs the same but paying as you go costs more
    # (5 dinners instead of 3 each home week), so the 5-meal plan wins instead.
    spread = annual_costs(4, 3, 2, PRICES, ["nr5", "cash_guest"])
    assert spread["nr5"] == pytest.approx(c["nr5"], abs=0.05)
    assert spread["cash_guest"] > spread["nr5"]


def test_annenberg_breakfast_raises_cash_cost():
    # 0 meals out, 0 skipped, no weekends away: 7 breakfasts/week x (12.90 - 10.84) = 14.42 more
    # per week when paying as you go, x 213/7 weeks = 438.78 more per year.
    houses = annual_costs(0, 0, 0, PRICES, ["cash_guest"])["cash_guest"]
    annenberg = annual_costs(0, 0, 0, PRICES, ["cash_guest"], breakfast_venue="annenberg_quincy")["cash_guest"]
    assert annenberg - houses == pytest.approx(14.42 * 213 / 7, abs=0.02)


# ---------------------------------------------------------------- real calendar (2026-27)

def test_term_weeks_from_csv():
    # Fall: Wed Sept 2 - Sat Dec 19 2026 = 109 days = 15 4/7 weeks.
    # Spring: Mon Jan 25 - Sat May 15 2027 = 111 days = 15 6/7 weeks, minus 1 spring-break week = 14 6/7.
    w = load_term_weeks()
    assert w["fall"] == pytest.approx(109 / 7)
    assert w["spring"] == pytest.approx(111 / 7 - 1)


def test_full_week_on_real_calendar():
    # NR 21 is a flat 4406 per term whatever the length: 8812 per year.
    # Paying guest rates for all 21 meals: 346.78/wk x (109/7 + 104/7 = 213/7 weeks) = 10552.31.
    c = annual_costs(0, 0, 0, PRICES, ["nr21", "cash_guest"])
    assert c["nr21"] == 8812
    assert c["cash_guest"] == pytest.approx(346.78 * 213 / 7, abs=0.01)


def test_nr10_on_real_calendar():
    # 10 swipes are worth at most 201.70/wk. Fall (15.57 wk) -> 3140.76 > 3060, so a heavy eater
    # beats cash in fall; spring (14.86 wk) -> 2996.40 < 3060, so cash wins in spring. Over the
    # year NR 10 can beat cash, but NR 5 or NR 21 is still cheaper everywhere on the map.
    beats_cash = cheapest = 0
    for weekends in range(11):
        for meals_out in range(15):
            for skipped in range(8):
                c = annual_costs(meals_out, skipped, weekends, PRICES, ["nr5", "nr10", "nr21", "cash_guest"])
                beats_cash += c["nr10"] < c["cash_guest"]
                cheapest += min(c, key=c.get) == "nr10"
    assert beats_cash > 0
    assert cheapest == 0


def test_which_meals_out_moves_the_5_meal_region():
    # The comparison figure (2 weekends away): taking meals out from dinners first leaves fewer
    # dinners for the 5-meal plan's swipes and makes paying as you go cheaper, so the 5-meal
    # region shrinks and the example student switches; lunches first does the opposite.
    from collections import Counter
    from decision_map import grid

    spread = Counter(c.plan for row in grid(2, PRICES, "undergrad_offcampus") for c in row)
    dinners = Counter(c.plan for row in grid(2, PRICES, "undergrad_offcampus", meals_out_from="dinners_first")
                      for c in row)
    lunches = Counter(c.plan for row in grid(2, PRICES, "undergrad_offcampus", meals_out_from="lunches_first")
                      for c in row)
    assert dinners["nr5"] < spread["nr5"] < lunches["nr5"]
    assert dinners["cash_guest"] > spread["cash_guest"] > lunches["cash_guest"]
    assert recommend(4, 3, 2, PRICES, "undergrad_offcampus").plan == "nr5"
    assert recommend(4, 3, 2, PRICES, "undergrad_offcampus", meals_out_from="dinners_first").plan == "cash_guest"
