# Hand-collected prices

Fill these in by hand; the code reads them as they are. One row per item. Leave a cell blank rather than guess.

## `restaurant_meals.csv` — about 30 meals near Harvard Square and Central Square

Aim for a spread: roughly 10 breakfast, 10 lunch and 10 dinner items, from cheap (food trucks, cafés, takeout) to sit-down, in both squares. Pick what a student would typically order as a full meal, not the cheapest side or the priciest special.

| Column | What to enter |
|---|---|
| `restaurant` | Name as on the menu |
| `type` | One of: coffee chain, café, bakery-café, Mexican, burgers, pizza, salad/bowls, Mediterranean, Greek, Vietnamese, grilled cheese, healthy bowls, diner, pub, tavern, New American, Italian (checked in code; add new types to `RESTAURANT_TYPES` in `src/restaurants.py`) |
| `neighborhood` | `Harvard Sq` or `Central Sq` |
| `address` | Street address |
| `service` | `counter` (order at the counter / takeout) or `sit-down` (table service) — decides whether a tip is added |
| `meal_type` | `breakfast`, `lunch` or `dinner` |
| `item` | The dish, e.g. "chicken burrito bowl" |
| `menu_price` | Menu price in dollars, **before** tax and tip, e.g. `13.95` (tax and tip are added in code, so the same rule applies to every row) |
| `includes_drink` | `yes` or `no` |
| `price_source` | `in person`, `restaurant website`, `menu photo`, or `news article` (avoid delivery apps: their prices are marked up). `news article` is accepted but second-hand and may be out of date; `figures/restaurant_prices_summary.csv` shows the averages without those rows too |
| `date_checked` | `YYYY-MM-DD` |
| `collected_by` | Your initials, or `Claude (web)` for prices Claude looked up online |
| `notes` | Anything odd: lunch special, student discount, portion size |

Example row (don't copy into the file):
`Example Cafe,Harvard Sq,1 Example St,counter,lunch,turkey sandwich,12.50,no,in person,2026-10-10,CC,lunch special`

## `grocery_basket.csv` — optional check on the cooking cost

The cooking cost per meal will come from USDA/BLS data. If you want a local check, price a small basket of staples (rice, pasta, eggs, chicken, beans, vegetables, bread, milk) at Star Market, Trader Joe's and/or Market Basket.

| Column | What to enter |
|---|---|
| `store` | `Star Market`, `Trader Joe's`, `Market Basket`, ... |
| `item` / `brand` | e.g. `long-grain rice` / `store brand` |
| `package_size` / `unit` | e.g. `2` / `lb` |
| `shelf_price` | Price on the shelf in dollars |
| `on_sale` | `yes` or `no` |
| `servings_per_package` | From the label |
| `used_in_meal` | Which kind of meal it's for: `breakfast`, `lunch`, `dinner` or `any` |
| `date_checked`, `collected_by`, `notes` | As above |
