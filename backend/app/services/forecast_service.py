import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def forecast_values(values: list[float], horizon: int = 7) -> dict:
    if len(values) < 14:
        average = sum(values) / len(values)
        return {
            "method": "moving_average_fallback",
            "forecast": [round(average, 2)] * horizon,
            "quality": "limited",
        }

    series = pd.Series(values)
    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal=None,
        initialization_method="estimated",
    )
    fitted = model.fit()
    forecast = fitted.forecast(horizon)

    return {
        "method": "holt_winters",
        "forecast": [round(float(v), 2) for v in forecast],
        "quality": "moderate",
    }
