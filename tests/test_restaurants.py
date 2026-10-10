"""Hand-worked checks for the restaurant prices (src/restaurants.py)."""

import csv

import pytest

from restaurants import average_price, averages, load_meals, out_the_door

FIELDS = ["restaurant", "neighborhood", "address", "service", "meal_type", "item", "menu_price", "includes_drink",
          "price_source", "date_checked", "collected_by", "notes"]


def _csv(tmp_path, rows):
    path = tmp_path / "meals.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for service, meal, price, source in rows:
            w.writerow({"restaurant": "X", "service": service, "meal_type": meal, "menu_price": price,
                        "price_source": source})
    return path


def test_out_the_door():
    assert out_the_door(10, "counter") == pytest.approx(10.70)   # + 7% tax
    assert out_the_door(20, "sit-down") == pytest.approx(25.00)  # + 7% tax + 18% tip on the menu price
    with pytest.raises(ValueError):
        out_the_door(10, "drive-through")


def test_averages_by_group(tmp_path):
    path = _csv(tmp_path, [("counter", "lunch", "10", "restaurant website"),
                           ("counter", "dinner", "20", "in person"),
                           ("sit-down", "dinner", "20", "news article"),
                           ("sit-down", "lunch", "", "menu photo")])  # blank price: skipped
    meals = load_meals(path)
    assert len(meals) == 3
    by_service = averages(meals, "service")
    assert by_service["counter"]["mean"] == pytest.approx((10.70 + 21.40) / 2)
    assert by_service["sit-down"]["n"] == 1 and by_service["sit-down"]["mean"] == pytest.approx(25.00)
    assert averages(meals, "meal_type")["dinner"]["mean"] == pytest.approx((21.40 + 25.00) / 2)
    # Dropping the news-article row leaves no sit-down meals.
    assert "sit-down" not in averages(load_meals(path, exclude_sources=["news article"]), "service")


def test_rejects_unknown_values(tmp_path):
    with pytest.raises(ValueError):
        load_meals(_csv(tmp_path, [("counter", "lunch", "10", "delivery app")]))
    with pytest.raises(ValueError):
        load_meals(_csv(tmp_path, [("counter", "snack", "10", "in person")]))


def test_real_sample():
    # 30 meals: 20 counter, 10 sit-down; 9 breakfasts, 10 lunches, 11 dinners.
    meals = load_meals()
    assert len(meals) == 30
    s = averages(meals, "service")
    assert (s["counter"]["n"], s["sit-down"]["n"]) == (20, 10)
    assert {k: v["n"] for k, v in averages(meals, "meal_type").items()} == {"breakfast": 9, "lunch": 10, "dinner": 11}
    # Counter menu prices: breakfast 60.49 + lunch 109.99 + dinner 66.09 = 236.57 -> x 1.07 / 20; sit-down sum to 197.64 -> x 1.25 / 10.
    assert sum(float(m["menu_price"]) for m in meals if m["service"] == "counter") == pytest.approx(236.57)
    assert average_price("counter") == pytest.approx(236.57 * 1.07 / 20)
    assert average_price("sit-down") == pytest.approx(197.64 * 1.25 / 10)


def test_types_and_log_tables_in_report():
    # Every row has a type from the list, and report.md holds the current log tables.
    from pathlib import Path

    from restaurants import RESTAURANT_TYPES, log_table

    meals = load_meals()
    assert all(m["type"] in RESTAURANT_TYPES for m in meals)
    report = (Path(__file__).resolve().parent.parent / "report.md").read_text(encoding="utf-8")
    for service in ("counter", "sit-down"):
        assert log_table(service, meals) in report
    first = log_table("counter", meals).splitlines()[2]
    assert "Dunkin'" in first and "$5.77" in first  # 5.39 x 1.07, the cheapest meal


def test_rejects_unknown_type(tmp_path):
    path = tmp_path / "m.csv"
    path.write_text("restaurant,type,service,meal_type,menu_price,price_source\nX,fusion,counter,lunch,10,in person\n")
    with pytest.raises(ValueError):
        load_meals(path)
