def trend(current, previous, higher_is_worse: bool = True, period: str = "previous day") -> dict:
    """Change versus the previous period, with whether it is an improvement."""
    if current is None or previous is None:
        return {"previous": previous, "change_pct": None, "direction": "flat", "improving": None, "period": period}
    current, previous = float(current), float(previous)
    change = round((current - previous) / previous * 100, 1) if previous else 0.0
    if abs(change) < 0.05:
        direction, improving = "flat", None
    else:
        direction = "up" if change > 0 else "down"
        improving = (direction == "down") if higher_is_worse else (direction == "up")
    return {
        "previous": round(previous, 2),
        "change_pct": change,
        "direction": direction,
        "improving": improving,
        "period": period,
    }
