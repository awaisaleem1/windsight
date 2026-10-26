import pandas as pd


from app.services.elexon_client import fetch_fuelhh_actuals
from app.services.forecast_client import fetch_wind_forecasts


def _parse_utc_timestamp(value: str) -> pd.Timestamp:
    """Parse a timestamp and convert it to UTC."""
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")

    if pd.isna(timestamp):
        raise ValueError(f"Invalid timestamp: {value}")

    return timestamp


def _get_daily_cutoff(
    delivery_time: pd.Timestamp,
    decision_time_utc: str,
) -> pd.Timestamp:
    """
    Calculate the decision cutoff for a delivery date.

    Example:
        Delivery date: 2026-01-15
        Decision time: 10:00:00 UTC
        Cutoff:        2026-01-14 10:00:00 UTC
    """
    delivery_date = delivery_time.normalize()

    try:
        hours, minutes, seconds = map(
            int,
            decision_time_utc.split(":"),
        )
    except (ValueError, AttributeError):
        raise ValueError(
            "decision_time_utc must use HH:MM:SS format, "
            "for example '10:00:00'."
        )

    if not (
        0 <= hours <= 23
        and 0 <= minutes <= 59
        and 0 <= seconds <= 59
    ):
        raise ValueError(
            "decision_time_utc contains an invalid time."
        )

    return (
        delivery_date
        - pd.Timedelta(days=1)
        + pd.Timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
        )
    )


async def build_forecast_comparison(
    settlement_date_from: str,
    settlement_date_to: str,
    decision_time_utc: str = "10:00:00",
    forecast_lookback_days: int = 7,
) -> pd.DataFrame:
    """
    Compare hourly WINDFOR forecasts with hourly FUELHH actuals.

    Actuals:
        Half-hourly FUELHH generation values aggregated to hourly
        averages. An hour requires both half-hourly observations.

    Forecasts:
        For each delivery hour, select the latest WINDFOR forecast
        published on or before the decision cutoff for that delivery
        date.

    Args:
        settlement_date_from: First settlement date, YYYY-MM-DD.
        settlement_date_to: Last settlement date, YYYY-MM-DD.
        decision_time_utc: Daily decision time in UTC, HH:MM:SS.
            Defaults to 10:00:00 UTC as an illustrative assumption.
        forecast_lookback_days: Publication history to retrieve before
            the earliest decision cutoff.

    Returns:
        A DataFrame with hourly actuals, forecasts, publication
        timestamps, cutoff timestamps and coverage information.

    Important:
        The default decision time is an assumption, not a verified
        procurement deadline. Configure it to match the business
        requirement when that deadline is known.
    """
    if forecast_lookback_days < 1:
        raise ValueError(
            "forecast_lookback_days must be at least 1."
        )

    output_columns = [
        "startTime",
        "actual",
        "forecast",
        "forecast_publish_time",
        "decision_cutoff",
        "actual_half_hourly_periods",
    ]

    # ---------------------------------------------------------
    # 1. Fetch actual wind generation
    # ---------------------------------------------------------
    actual_records = await fetch_fuelhh_actuals(
        settlement_date_from=settlement_date_from,
        settlement_date_to=settlement_date_to,
        fuel_type="WIND",
    )

    actuals = pd.DataFrame(actual_records)

    if actuals.empty:
        return pd.DataFrame(columns=output_columns)

    required_actual_columns = {"startTime", "generation"}
    missing_actual_columns = (
        required_actual_columns - set(actuals.columns)
    )

    if missing_actual_columns:
        raise ValueError(
            "FUELHH response is missing required fields: "
            f"{sorted(missing_actual_columns)}"
        )

    actuals["startTime"] = pd.to_datetime(
        actuals["startTime"],
        utc=True,
        errors="coerce",
    )

    actuals["generation"] = pd.to_numeric(
        actuals["generation"],
        errors="coerce",
    )

    actuals = actuals.dropna(
        subset=["startTime", "generation"]
    )

    # Ensure one record per half-hourly delivery timestamp.
    actuals = (
        actuals.sort_values("startTime")
        .drop_duplicates(
            subset=["startTime"],
            keep="last",
        )
    )

    # ---------------------------------------------------------
    # 2. Aggregate actuals to hourly averages
    # ---------------------------------------------------------
    actuals["hour"] = actuals["startTime"].dt.floor("h")

    actuals_hourly = (
        actuals.groupby("hour")
        .agg(
            actual=("generation", "mean"),
            actual_half_hourly_periods=("generation", "count"),
        )
        .reset_index()
        .rename(columns={"hour": "startTime"})
    )

    # An incomplete hour must not be treated as a complete actual.
    actuals_hourly.loc[
        actuals_hourly["actual_half_hourly_periods"] != 2,
        "actual",
    ] = float("nan")

    if actuals_hourly.empty:
        return pd.DataFrame(columns=output_columns)

    # ---------------------------------------------------------
    # 3. Calculate a cutoff for each delivery date
    # ---------------------------------------------------------
    actuals_hourly["decision_cutoff"] = (
        actuals_hourly["startTime"].apply(
            lambda delivery_time: _get_daily_cutoff(
                delivery_time,
                decision_time_utc,
            )
        )
    )

    earliest_cutoff = actuals_hourly[
        "decision_cutoff"
    ].min()

    latest_cutoff = actuals_hourly[
        "decision_cutoff"
    ].max()

    # Retrieve publication history covering all required cutoffs.
    publication_from = (
        earliest_cutoff
        - pd.Timedelta(days=forecast_lookback_days)
    ).isoformat()

    publication_to = latest_cutoff.isoformat()

    # ---------------------------------------------------------
    # 4. Fetch historical forecasts
    # ---------------------------------------------------------
    forecast_records = await fetch_wind_forecasts(
        publish_time_from=publication_from,
        publish_time_to=publication_to,
    )

    forecasts = pd.DataFrame(forecast_records)

    if forecasts.empty:
        actuals_hourly["forecast"] = float("nan")
        actuals_hourly["forecast_publish_time"] = pd.NaT

        return (
            actuals_hourly[output_columns]
            .sort_values("startTime")
            .reset_index(drop=True)
        )

    required_forecast_columns = {
        "publishTime",
        "startTime",
        "generation",
    }

    missing_forecast_columns = (
        required_forecast_columns - set(forecasts.columns)
    )

    if missing_forecast_columns:
        raise ValueError(
            "WINDFOR response is missing required fields: "
            f"{sorted(missing_forecast_columns)}"
        )

    forecasts["publishTime"] = pd.to_datetime(
        forecasts["publishTime"],
        utc=True,
        errors="coerce",
    )

    forecasts["startTime"] = pd.to_datetime(
        forecasts["startTime"],
        utc=True,
        errors="coerce",
    )

    forecasts["generation"] = pd.to_numeric(
        forecasts["generation"],
        errors="coerce",
    )

    forecasts = forecasts.dropna(
        subset=[
            "publishTime",
            "startTime",
            "generation",
        ]
    )

    # Keep forecasts only for delivery hours in the actual dataset.
    delivery_times = set(actuals_hourly["startTime"])

    forecasts = forecasts[
        forecasts["startTime"].isin(delivery_times)
    ].copy()

    # ---------------------------------------------------------
    # 5. Apply the cutoff for each individual delivery date
    # ---------------------------------------------------------
    cutoff_by_delivery_time = actuals_hourly.set_index(
        "startTime"
    )["decision_cutoff"]

    forecasts["decision_cutoff"] = forecasts[
        "startTime"
    ].map(cutoff_by_delivery_time)

    forecasts = forecasts.dropna(
        subset=["decision_cutoff"]
    )

    # Critical safeguard: exclude forecasts published after
    # the relevant delivery date's decision cutoff.
    forecasts = forecasts[
        forecasts["publishTime"]
        <= forecasts["decision_cutoff"]
    ].copy()

    # ---------------------------------------------------------
    # 6. Select the latest eligible publication per delivery hour
    # ---------------------------------------------------------
    forecasts = forecasts.sort_values(
        ["startTime", "publishTime"]
    )

    forecasts = forecasts.drop_duplicates(
        subset=["startTime"],
        keep="last",
    )

    forecasts = forecasts.rename(
        columns={
            "generation": "forecast",
            "publishTime": "forecast_publish_time",
        }
    )

    # ---------------------------------------------------------
    # 7. Join forecasts to actuals
    # ---------------------------------------------------------
    result = actuals_hourly.merge(
        forecasts[
            [
                "startTime",
                "forecast",
                "forecast_publish_time",
            ]
        ],
        on="startTime",
        how="left",
        validate="one_to_one",
    )

    # Final safety check for the selected publication timestamps.
    invalid = (
        result["forecast_publish_time"].notna()
        & (
            result["forecast_publish_time"]
            > result["decision_cutoff"]
        )
    )

    if invalid.any():
        raise RuntimeError(
            "Look-ahead bias detected: a forecast was published "
            "after its decision cutoff."
        )

    return (
        result[output_columns]
        .sort_values("startTime")
        .reset_index(drop=True)
    )
