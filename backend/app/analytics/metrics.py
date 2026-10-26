
import numpy as np
import pandas as pd


def calculate_forecast_metrics(
    df: pd.DataFrame,
    actual_column: str = "actual",
    forecast_column: str = "forecast",
) -> dict:
    """
    Calculate accuracy metrics for wind generation forecasts.

    Expected DataFrame columns:
        actual: Observed wind generation.
        forecast: Predicted wind generation.

    Error convention:
        error = forecast - actual

    Positive bias means overforecasting.
    Negative bias means underforecasting.

    Returns:
        A dictionary containing MAE, RMSE, bias, WAPE,
        and the number of evaluated observations.
    """
    required_columns = {actual_column, forecast_column}

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    evaluation = df[[actual_column, forecast_column]].copy()

    evaluation[actual_column] = pd.to_numeric(
        evaluation[actual_column],
        errors="coerce",
    )

    evaluation[forecast_column] = pd.to_numeric(
        evaluation[forecast_column],
        errors="coerce",
    )

    # Exclude missing and non-finite values.
    evaluation = evaluation.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    # Do not silently treat missing data as zero.
    if evaluation.empty:
        raise ValueError(
            "Cannot calculate metrics: no valid actual/forecast pairs."
        )

    actual = evaluation[actual_column].to_numpy(dtype=float)
    forecast = evaluation[forecast_column].to_numpy(dtype=float)

    errors = forecast - actual
    absolute_errors = np.abs(errors)

    mae = float(np.mean(absolute_errors))
    rmse = float(np.sqrt(np.mean(errors**2)))
    bias = float(np.mean(errors))

    total_actual = float(np.sum(np.abs(actual)))

    if total_actual > 0:
        wape = float(
            np.sum(absolute_errors) / total_actual * 100
        )
    else:
        wape = None

    return {
        "observations": int(len(evaluation)),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "bias": round(bias, 4),
        "wape_percent": (
            round(wape, 4) if wape is not None else None
        ),
    }
