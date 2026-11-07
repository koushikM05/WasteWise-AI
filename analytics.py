"""Calculate canteen waste totals from a cleaned records table.

Waste percentage is wasted portions divided by prepared portions.
Sold portions are the portions_served column.
"""


def summary(records):
    """Return prepared, sold, wasted, and the overall waste percentage."""
    prepared = float(records["portions_prepared"].sum())
    sold = float(records["portions_served"].sum())
    wasted = float(records["portions_wasted"].sum())

    return {
        "prepared": prepared,
        "sold": sold,
        "wasted": wasted,
        "waste_percentage": _percentage(wasted, prepared),
    }


def portions_by_day(records):
    """Return one row per day with Prepared, Sold, and Wasted totals."""
    daily = (
        records.groupby("date", as_index=False)[
            ["portions_prepared", "portions_served", "portions_wasted"]
        ]
        .sum()
        .sort_values("date")
    )
    daily["day"] = daily["date"].dt.strftime("%d %b")
    return daily.rename(
        columns={
            "portions_prepared": "Prepared",
            "portions_served": "Sold",
            "portions_wasted": "Wasted",
        }
    )


def waste_by_item(records):
    """Return prepared, sold, wasted, and waste percentage for each dish."""
    grouped = _sum_by(records, "item")
    return grouped.sort_values("portions_wasted", ascending=False).reset_index(drop=True)


def waste_by_meal(records):
    """Return prepared, sold, wasted, and waste percentage for each meal."""
    grouped = _sum_by(records, "meal")
    meal_order = {"Breakfast": 0, "Lunch": 1, "Snacks": 2}
    grouped["_order"] = grouped["meal"].map(meal_order).fillna(99)
    grouped = grouped.sort_values("_order").drop(columns="_order")
    return grouped.reset_index(drop=True)


def cost_of_waste(records):
    """Estimate the rupee cost of wasted portions."""
    cost = records["portions_wasted"] * records["cost_per_portion"]
    return float(cost.sum())


def _sum_by(records, column_name):
    """Sum portion columns for one grouping column and add waste percentage."""
    grouped = records.groupby(column_name, as_index=False)[
        ["portions_prepared", "portions_served", "portions_wasted"]
    ].sum()
    grouped["waste_percentage"] = [
        _percentage(wasted, prepared)
        for wasted, prepared in zip(
            grouped["portions_wasted"], grouped["portions_prepared"]
        )
    ]
    return grouped


def _percentage(part, whole):
    """Return part / whole as a percent. Zero when there is nothing prepared."""
    if whole <= 0:
        return 0.0
    return float(part) / float(whole) * 100
