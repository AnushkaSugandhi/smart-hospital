"""Additional resource cards: ventilators, theatres, nurses, oxygen, blood."""
from app.core.config import BLOOD_GROUPS, LOW_STOCK, STATUS_META, status_for_pct
from app.services.trends import trend

BLOOD_LABELS = {g: g.replace("_pos", "+").replace("_neg", "-").upper() for g in BLOOD_GROUPS}


def _status(status: str) -> dict:
    return {"status": status, "status_label": STATUS_META[status]["label"]}


def _latest_with(rows: list[dict], *keys: str):
    """Most recent row (and the one before it) that has all `keys` filled."""
    found = [r for r in rows if all(r.get(k) is not None for k in keys)]
    if not found:
        return None, None
    return found[-1], (found[-2] if len(found) > 1 else None)


def _utilisation_card(rows, key, label, used_key, total_key, noun):
    row, prev = _latest_with(rows, used_key, total_key)
    if not row:
        return {"key": key, "label": label, "available": False}
    used, total = int(row[used_key]), int(row[total_key])
    pct = round(used / total * 100, 1) if total else 0.0
    prev_pct = round(prev[used_key] / prev[total_key] * 100, 1) if prev and prev[total_key] else None
    status = status_for_pct(pct)
    free = total - used
    return {
        "key": key, "label": label, "available": True, "as_of": row["date"],
        "value": pct, "unit": "%", "used": used, "total": total,
        "summary": f"{free} of {total} {noun} free",
        "formula": f"{used} in use ÷ {total} total × 100 = {pct}%",
        "low_stock": status == "critical",
        "warning": f"Only {free} {noun} free" if status == "critical" else None,
        "trend": trend(pct, prev_pct, higher_is_worse=True),
        **_status(status),
    }


def _nurse_card(rows):
    row, prev = _latest_with(rows, "nurses_on_duty", "nurses_required")
    if not row:
        return {"key": "nurses", "label": "Nurses", "available": False}
    on_duty, required = int(row["nurses_on_duty"]), int(row["nurses_required"])
    coverage = round(on_duty / required * 100, 1) if required else 100.0
    prev_cov = (round(prev["nurses_on_duty"] / prev["nurses_required"] * 100, 1)
                if prev and prev["nurses_required"] else None)
    if coverage < LOW_STOCK["nurse_coverage_critical_below"]:
        status = "critical"
    elif coverage < LOW_STOCK["nurse_coverage_warning_below"]:
        status = "warning"
    else:
        status = "normal"
    gap = max(required - on_duty, 0)
    return {
        "key": "nurses", "label": "Nurses", "available": True, "as_of": row["date"],
        "value": coverage, "unit": "% of required on duty", "used": on_duty, "total": required,
        "summary": f"{on_duty} on duty of {required} required",
        "formula": f"{on_duty} on duty ÷ {required} required × 100 = {coverage}% coverage",
        "low_stock": status != "normal",
        "warning": f"Short by {gap} nurses" if gap else None,
        "trend": trend(coverage, prev_cov, higher_is_worse=False),
        **_status(status),
    }


def _oxygen_card(rows):
    row, prev = _latest_with(rows, "oxygen_stock_hours")
    if not row:
        return {"key": "oxygen", "label": "Oxygen stock", "available": False}
    hours = round(float(row["oxygen_stock_hours"]), 1)
    if hours < LOW_STOCK["oxygen_hours_critical"]:
        status = "critical"
    elif hours < LOW_STOCK["oxygen_hours_warning"]:
        status = "warning"
    else:
        status = "normal"
    return {
        "key": "oxygen", "label": "Oxygen stock", "available": True, "as_of": row["date"],
        "value": hours, "unit": "hours of supply",
        "summary": f"~{hours:g} hours at current usage",
        "formula": (f"hours of supply remaining; warning below {LOW_STOCK['oxygen_hours_warning']:g} h, "
                    f"critical below {LOW_STOCK['oxygen_hours_critical']:g} h"),
        "low_stock": status != "normal",
        "warning": f"Oxygen below {LOW_STOCK['oxygen_hours_warning']:g} hours — reorder now" if status != "normal" else None,
        "trend": trend(hours, prev["oxygen_stock_hours"] if prev else None, higher_is_worse=False),
        **_status(status),
    }


def _blood_card(rows):
    keys = [f"blood_{g}" for g in BLOOD_GROUPS]
    row, prev = _latest_with(rows, *keys)
    if not row:
        return {"key": "blood", "label": "Blood stock", "available": False}
    groups, low = [], []
    for g in BLOOD_GROUPS:
        units = int(row[f"blood_{g}"])
        if units < LOW_STOCK["blood_units_critical"]:
            status = "critical"
        elif units < LOW_STOCK["blood_units_warning"]:
            status = "warning"
        else:
            status = "normal"
        if status != "normal":
            low.append(BLOOD_LABELS[g])
        groups.append({"group": BLOOD_LABELS[g], "units": units, **_status(status)})
    total = sum(g["units"] for g in groups)
    prev_total = sum(int(prev[k]) for k in keys) if prev else None
    worst = "critical" if any(g["status"] == "critical" for g in groups) else (
        "warning" if low else "normal")
    return {
        "key": "blood", "label": "Blood stock", "available": True, "as_of": row["date"],
        "value": total, "unit": "units", "groups": groups,
        "summary": f"{total} units across {len(groups)} groups",
        "formula": (f"units per blood group; low below {LOW_STOCK['blood_units_warning']} units, "
                    f"critical below {LOW_STOCK['blood_units_critical']}"),
        "low_stock": bool(low),
        "warning": f"Low stock: {', '.join(low)}" if low else None,
        "trend": trend(total, prev_total, higher_is_worse=False),
        **_status(worst),
    }


def resource_cards(rows: list[dict]) -> list[dict]:
    return [
        _utilisation_card(rows, "ventilators", "Ventilators", "ventilators_in_use", "ventilators_total", "ventilators"),
        _utilisation_card(rows, "operation_theatres", "Operation theatres", "ot_in_use", "ot_total", "theatres"),
        _nurse_card(rows),
        _oxygen_card(rows),
        _blood_card(rows),
    ]
