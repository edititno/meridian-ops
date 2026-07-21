"""Demand forecasting: per-SKU weekly forecasts with a seasonal-trend linear model.

Approach: ordinary least squares on (week_index, month dummies) per SKU.
Simple, explainable, and appropriate for ~18 months of weekly history.
Outputs point forecast plus a naive 80% band from residual std.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def forecast_sku(weekly: pd.DataFrame, horizon_weeks: int = 12) -> pd.DataFrame:
    """weekly: DataFrame with columns [week (datetime), units] for one SKU."""
    df = weekly.sort_values("week").reset_index(drop=True).copy()
    df["t"] = np.arange(len(df))
    df["month"] = pd.to_datetime(df["week"]).dt.month

    X = np.column_stack([
        df["t"].values,
        np.column_stack([(df["month"] == m).astype(int) for m in range(2, 13)])
    ])
    y = df["units"].values

    model = LinearRegression().fit(X, y)
    resid_std = float(np.std(y - model.predict(X)))

    last_week = pd.to_datetime(df["week"].iloc[-1])
    future_weeks = [last_week + pd.Timedelta(weeks=i) for i in range(1, horizon_weeks + 1)]
    ft = np.arange(len(df), len(df) + horizon_weeks)
    fmonth = np.array([w.month for w in future_weeks])
    FX = np.column_stack([
        ft,
        np.column_stack([(fmonth == m).astype(int) for m in range(2, 13)])
    ])
    point = np.clip(model.predict(FX), 0, None)

    return pd.DataFrame({
        "week": future_weeks,
        "forecast": point.round(1),
        "lo80": np.clip(point - 1.28 * resid_std, 0, None).round(1),
        "hi80": (point + 1.28 * resid_std).round(1),
    })
