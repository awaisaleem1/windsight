
import pandas as pd
import pytest

from app.analytics.metrics import calculate_forecast_metrics


def test_calculate_forecast_metrics():
    df = pd.DataFrame(
        {
            "actual": [100, 200, 300],
            "forecast": [110, 180, 330],
        }
    )

    result = calculate_forecast_metrics(df)

    assert result["observations"] == 3
    assert result["mae"] == pytest.approx(20.0)
    assert result["rmse"] == pytest.approx(21.6025, abs=0.0001)
    assert result["bias"] == pytest.approx(6.6667, abs=0.0001)
    assert result["wape_percent"] == pytest.approx(10.0)


def test_missing_values_are_excluded():
    df = pd.DataFrame(
        {
            "actual": [100, None, 300],
            "forecast": [110, 200, 330],
        }
    )

    result = calculate_forecast_metrics(df)

    assert result["observations"] == 2
    assert result["mae"] == pytest.approx(20.0)


def test_missing_columns_raise_error():
    df = pd.DataFrame({"actual": [100, 200]})

    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_forecast_metrics(df)


def test_no_valid_pairs_raise_error():
    df = pd.DataFrame(
        {
            "actual": [None, None],
            "forecast": [100, 200],
        }
    )

    with pytest.raises(ValueError, match="no valid actual/forecast pairs"):
        calculate_forecast_metrics(df)


def test_zero_actual_total_returns_no_wape():
    df = pd.DataFrame(
        {
            "actual": [0, 0],
            "forecast": [10, 20],
        }
    )

    result = calculate_forecast_metrics(df)

    assert result["mae"] == pytest.approx(15.0)
    assert result["wape_percent"] is None
