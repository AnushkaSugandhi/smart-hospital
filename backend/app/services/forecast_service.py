import warnings
from functools import lru_cache

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def forecast_values(values: list[float], horizon: int = 7) -> dict:
    # Cached: the dashboard, alerts and chatbot forecast the same series repeatedly.
    result = dict(_forecast(tuple(round(float(v), 6) for v in values), int(horizon)))
    result["forecast"] = list(result["forecast"])  # never hand out the cached list
    return result


@lru_cache(maxsize=128)
def _forecast(values: tuple, horizon: int) -> tuple:
    # Ratios (0-1) need more precision than counts.
    digits = 4 if max(abs(v) for v in values) <= 1.5 else 2
    if len(values) < 14:
        average = sum(values) / len(values)
        return (
            ("method", "moving_average_fallback"),
            ("forecast", [round(average, digits)] * horizon),
            ("quality", "limited"),
        )

    series = pd.Series(values)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=None,
            initialization_method="estimated",
        )
        fitted = model.fit()
        forecast = fitted.forecast(horizon)

    return (
        ("method", "holt_winters"),
        ("forecast", [round(float(v), digits) for v in forecast]),
        ("quality", "moderate"),
    )
