from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from httpx import HTTPError

from app.analytics.metrics import calculate_forecast_metrics
from app.services.forecast_service import build_forecast_comparison


router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Check whether the WindSight API is running.
    """
    return {
        "status": "healthy",
        "service": "WindSight API",
    }


@router.get("/forecast")
async def get_forecast(
    start_date: date = Query(
        ...,
        description="First settlement date, inclusive (YYYY-MM-DD).",
    ),
    end_date: date = Query(
        ...,
        description="Last settlement date, inclusive (YYYY-MM-DD).",
    ),
    decision_time_utc: str = Query(
        default="10:00:00",
        description=(
            "Daily day-ahead forecast decision cutoff in UTC, "
            "formatted HH:MM:SS. The default is illustrative."
        ),
    ),
):
    """
    Return hourly actual wind generation and eligible forecasts.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    if (end_date - start_date).days > 40:
        raise HTTPException(
            status_code=400,
            detail="Date range cannot exceed 41 calendar days.",
        )

    try:
        comparison = await build_forecast_comparison(
            settlement_date_from=start_date.isoformat(),
            settlement_date_to=end_date.isoformat(),
            decision_time_utc=decision_time_utc,
        )

        if comparison.empty:
            return {
                "metadata": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "decision_time_utc": decision_time_utc,
                    "timezone": "UTC",
                    "units": "MW",
                    "observations": 0,
                },
                "data": [],
                "metrics": None,
            }

        # Convert pandas missing values and timestamps into
        # JSON-compatible Python values.
        records = comparison.copy()

        timestamp_columns = [
            "startTime",
            "forecast_publish_time",
            "decision_cutoff",
        ]

        for column in timestamp_columns:
            records[column] = records[column].map(
                lambda value: (
                    value.isoformat()
                    if pd.notna(value)
                    else None
                )
            )

        records = records.astype(object).where(
            pd.notna(records),
            None,
        )

        data = records.to_dict(orient="records")

        matched = comparison.dropna(
            subset=["actual", "forecast"]
        )

        metrics = None

        if not matched.empty:
            metrics = calculate_forecast_metrics(matched)

        coverage = (
            len(matched) / len(comparison) * 100
            if len(comparison)
            else 0.0
        )

        return {
            "metadata": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "decision_time_utc": decision_time_utc,
                "timezone": "UTC",
                "units": "MW",
                "observations": len(comparison),
                "matched_observations": len(matched),
                "forecast_coverage_percent": round(
                    coverage,
                    2,
                ),
                "missing_forecast_observations": (
                    len(comparison) - len(matched)
                ),
            },
            "data": data,
            "metrics": metrics,
        }

    except HTTPException:
        raise

    except HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to retrieve wind generation data "
                "from the Elexon API."
            ),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Log the full exception server-side rather than returning
        # internal details to the API consumer.
        import logging

        logging.getLogger(__name__).exception(
            "Unexpected error while building forecast comparison."
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing forecasts.",
        ) from exc


@router.get("/metrics")
async def get_forecast_metrics(
    start_date: date = Query(
        ...,
        description="First settlement date, inclusive (YYYY-MM-DD).",
    ),
    end_date: date = Query(
        ...,
        description="Last settlement date, inclusive (YYYY-MM-DD).",
    ),
    decision_time_utc: str = Query(
        default="10:00:00",
        description="Daily day-ahead decision cutoff in UTC.",
    ),
):
    """
    Return forecast accuracy metrics for a date range.
    """
    response = await get_forecast(
        start_date=start_date,
        end_date=end_date,
        decision_time_utc=decision_time_utc,
    )

    if response["metrics"] is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "No matched actual and forecast observations "
                "are available for metric calculation."
            ),
        )

    return {
        "metadata": response["metadata"],
        "metrics": response["metrics"],
    }


# Directory containing saved evaluation reports.
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def load_evaluation_csv(filename: str) -> pd.DataFrame:
    """
    Load a saved evaluation CSV from the backend reports directory.
    """
    file_path = REPORTS_DIR / filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Evaluation report is unavailable: {filename}",
        )

    try:
        return pd.read_csv(file_path)

    except (OSError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read evaluation report: {filename}",
        ) from exc


def dataframe_to_records(dataframe: pd.DataFrame) -> list[dict]:
    """
    Convert a DataFrame into JSON-compatible records.
    """
    records = dataframe.copy()

    # Convert timestamps to ISO 8601 strings.
    for column in records.columns:
        if "time" in column.lower():
            parsed = pd.to_datetime(
                records[column],
                utc=True,
                errors="coerce",
            )

            records[column] = parsed.map(
                lambda value: (
                    value.isoformat()
                    if pd.notna(value)
                    else None
                )
            )

    # Replace NaN and infinity values with None.
    records = records.astype(object)

    records = records.where(
        pd.notna(records),
        None,
    )

    return records.to_dict(orient="records")


@router.get("/evaluation/january-2026")
async def get_january_2026_evaluation():
    """
    Return saved January 2026 fixed-lead-time evaluation results.

    This endpoint reports historical evaluation results.
    It does not fetch new forecasts or retrain any models.
    """
    summary_df = load_evaluation_csv(
        "january_fixed_lead_time_summary.csv"
    )

    matched_df = load_evaluation_csv(
        "january_fixed_lead_time_matched_summary.csv"
    )

    details_df = load_evaluation_csv(
        "january_fixed_lead_time_details.csv"
    )

    required_summary_columns = {
        "horizon_hours",
        "observations",
        "mae_mw",
        "rmse_mw",
        "bias_mw",
        "wape_percent",
        "coverage_percent",
        "mean_actual_lead_hours",
    }

    required_matched_columns = {
        "horizon_hours",
        "observations",
        "mae_mw",
        "rmse_mw",
        "bias_mw",
        "wape_percent",
        "matched_delivery_hours",
    }

    required_detail_columns = {
        "delivery_time",
        "actual",
        "forecast",
        "forecast_publish_time",
        "horizon_hours",
        "lead_hours",
    }

    if not required_summary_columns.issubset(summary_df.columns):
        raise HTTPException(
            status_code=500,
            detail="The evaluation summary has an unexpected schema.",
        )

    if not required_matched_columns.issubset(matched_df.columns):
        raise HTTPException(
            status_code=500,
            detail="The matched evaluation summary has an unexpected schema.",
        )

    if not required_detail_columns.issubset(details_df.columns):
        raise HTTPException(
            status_code=500,
            detail="The evaluation details have an unexpected schema.",
        )

    # Sort horizons consistently for the frontend.
    summary_df = summary_df.sort_values(
        "horizon_hours",
        ascending=False,
    )

    matched_df = matched_df.sort_values(
        "horizon_hours",
        ascending=False,
    )

    details_df = details_df.sort_values(
        ["delivery_time", "horizon_hours"],
        ascending=[True, False],
    )

    # Convert numeric fields explicitly to avoid returning
    # pandas/numpy-specific values in JSON.
    summary_numeric_columns = [
        "horizon_hours",
        "observations",
        "mae_mw",
        "rmse_mw",
        "bias_mw",
        "wape_percent",
        "coverage_percent",
        "mean_actual_lead_hours",
    ]

    matched_numeric_columns = [
        "horizon_hours",
        "observations",
        "mae_mw",
        "rmse_mw",
        "bias_mw",
        "wape_percent",
        "matched_delivery_hours",
    ]

    for column in summary_numeric_columns:
        summary_df[column] = pd.to_numeric(
            summary_df[column],
            errors="coerce",
        )

    for column in matched_numeric_columns:
        matched_df[column] = pd.to_numeric(
            matched_df[column],
            errors="coerce",
        )

    # Validate and convert detail timestamps.
    details_df["delivery_time"] = pd.to_datetime(
        details_df["delivery_time"],
        utc=True,
        errors="coerce",
    )

    details_df["forecast_publish_time"] = pd.to_datetime(
        details_df["forecast_publish_time"],
        utc=True,
        errors="coerce",
    )

    for column in [
        "actual",
        "forecast",
        "horizon_hours",
        "lead_hours",
    ]:
        details_df[column] = pd.to_numeric(
            details_df[column],
            errors="coerce",
        )

    # Do not silently expose invalid rows.
    if (
        summary_df[summary_numeric_columns].isna().any().any()
        or matched_df[matched_numeric_columns].isna().any().any()
        or details_df[list(required_detail_columns)].isna().any().any()
    ):
        raise HTTPException(
            status_code=500,
            detail="An evaluation report contains invalid or missing values.",
        )

    # Return all report rows. The frontend can filter observations
    # by horizon without requesting the files separately.
    return {
        "metadata": {
            "evaluation_period": {
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            },
            "timezone": "UTC",
            "units": "MW",
            "horizons_hours": [6, 12, 24, 48],
            "evaluation_type": "fixed_minimum_lead_time",
            "selection_rule": (
                "For each delivery hour and horizon, select the "
                "latest forecast published at or before delivery "
                "time minus the requested horizon."
            ),
            "bias_definition": "forecast minus actual",
            "coverage_note": (
                "Coverage is calculated against 744 expected January "
                "hours. The 48-hour horizon has 589 eligible hours; "
                "the other horizons have 744."
            ),
            "historical_results": True,
        },
        "summary": dataframe_to_records(summary_df),
        "matched_summary": dataframe_to_records(matched_df),
        "observations": dataframe_to_records(details_df),
    }
