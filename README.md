# WindSight — Day-Ahead Wind Forecast Intelligence

WindSight is a web-based analytics platform for evaluating UK national wind-generation forecasts against actual generation. It helps electricity procurement teams understand forecast accuracy at different lead times and identify systematic overforecasting or underforecasting.

The project uses data from the **Elexon Balancing Mechanism Reporting Service (BMRS)** and provides a React dashboard backed by a FastAPI service.

> **Scope:** This pilot evaluates existing published wind-generation forecasts for January 2026. It does not train a new forecasting model or provide a complete electricity-trading strategy.

## Key Findings

The January 2026 evaluation compares forecasts selected at minimum lead times of 6, 12, 24, and 48 hours.

| Minimum lead time | Evaluated hours | MAE (MW) | RMSE (MW) | Bias (MW) |   WAPE | Coverage |
| ----------------- | --------------: | -------: | --------: | --------: | -----: | -------: |
| 6 hours           |             744 | 1,881.05 |  2,357.46 | +1,683.60 | 16.24% |     100% |
| 12 hours          |             744 | 1,907.18 |  2,384.45 | +1,704.37 | 16.47% |     100% |
| 24 hours          |             744 | 2,064.14 |  2,524.28 | +1,854.60 | 17.82% |     100% |
| 48 hours          |             589 | 2,386.92 |  2,939.43 | +1,867.78 | 20.67% |   79.17% |

**Interpretation:** All horizons show positive bias, meaning the selected forecasts tended to overestimate actual wind generation. The 6-hour horizon has the lowest MAE and WAPE among these results.

The 48-hour horizon has forecasts available for only 589 of the 744 expected January hours. Its results must therefore be interpreted alongside its lower coverage.

### Matched-Hour Comparison

To make the horizon comparison fairer, a second evaluation compares all four horizons over the same 589 delivery hours.

| Minimum lead time | Matched hours | MAE (MW) | RMSE (MW) | Bias (MW) |   WAPE |
| ----------------- | ------------: | -------: | --------: | --------: | -----: |
| 6 hours           |           589 | 1,803.51 |  2,253.73 | +1,564.88 | 15.62% |
| 12 hours          |           589 | 1,871.07 |  2,328.73 | +1,624.86 | 16.20% |
| 24 hours          |           589 | 2,025.12 |  2,472.28 | +1,768.96 | 17.54% |
| 48 hours          |           589 | 2,386.92 |  2,939.43 | +1,867.78 | 20.67% |

This matched-hour comparison avoids attributing differences in performance solely to the forecast horizon when the available delivery hours differ.

## Features

* Interactive forecast and actual-generation analysis by delivery-date range and decision cutoff.
* Forecast performance metrics: MAE, RMSE, bias, and WAPE.
* January 2026 historical evaluation across four forecast horizons.
* All-available-hours and matched-hours comparisons.
* FastAPI endpoints for forecast data, health checks, and historical evaluation.
* Docker Compose setup for running the frontend and backend together.

## Data Sources

WindSight uses the two Elexon BMRS datasets specified in the project requirements:

* **FUELHH — actual generation:** [Elexon FUELHH API documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
* **WINDFOR — wind-generation forecasts:** [Elexon WINDFOR API documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)

Actual generation is aggregated from half-hourly readings into hourly values using the mean of the two readings. Hours without both expected readings are excluded rather than imputed.

All evaluation timestamps use UTC, and generation values are expressed in megawatts (MW).

## Evaluation Methodology

For each delivery hour \(t\) and requested minimum lead time \(H\), WindSight selects the latest available forecast publication satisfying:

$$
p \leq t-H
$$

where \(p\) is the forecast publication time.

This ensures that a forecast published after the required cutoff is not used to evaluate that horizon.

The evaluation reports:

* **MAE:** mean absolute forecast error.
* **RMSE:** root mean squared error, which gives greater weight to large errors.
* **Bias:** mean of forecast minus actual generation. Positive values indicate overforecasting.
* **WAPE:** total absolute error divided by total actual generation, expressed as a percentage.
* **Coverage:** matched delivery hours divided by the 744 expected hours in January 2026.

Two evaluation views are provided:

1. **All available hours:** each horizon uses every eligible delivery hour available for that horizon.
2. **Matched hours:** every horizon uses the same delivery hours for a more directly comparable assessment.

The 48-hour evaluation covers 589 hours. The other horizons cover all 744 hours. The absence of eligible forecasts in the queried API history for the remaining 155 hours is a data-availability limitation; it does not establish that no forecasts ever existed.

## Architecture

```text
┌────────────────────────────┐
│       React + Vite         │
│ Forecast and performance UI│
└─────────────┬──────────────┘
              │ HTTP /api/*
              ▼
┌────────────────────────────┐
│       Nginx frontend       │
│ Static files + API proxy   │
└─────────────┬──────────────┘
              ▼
┌────────────────────────────┐
│        FastAPI             │
│ Routes, data services,     │
│ analytics and evaluation   │
└─────────────┬──────────────┘
              │
       ┌──────┴────────┐
       ▼               ▼
 Elexon BMRS      Historical CSV
 API services     evaluation reports
```

### Technology Stack

* **Frontend:** React, Vite, JavaScript, CSS, Recharts.
* **Backend:** Python, FastAPI, Uvicorn.
* **Data processing:** Pandas and NumPy.
* **Testing:** Pytest.
* **Containerization and serving:** Docker, Docker Compose, Nginx.

## Project Structure

```text
windsight/
├── backend/
│   ├── app/
│   │   ├── analytics/
│   │   │   └── metrics.py
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── services/
│   │   │   ├── elexon_client.py
│   │   │   ├── forecast_client.py
│   │   │   └── forecast_service.py
│   │   └── main.py
│   ├── reports/
│   │   ├── january_fixed_lead_time_details.csv
│   │   ├── january_fixed_lead_time_matched_summary.csv
│   │   └── january_fixed_lead_time_summary.csv
│   ├── tests/
│   │   └── test_metrics.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── Performance.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

* Docker Desktop with Docker Compose.
* Git, if cloning the repository.

### Run with Docker Compose

From the project root:

```bash
docker compose up --build -d
```

Open the application:

* **Web application:** `http://localhost:8080`
* **Health check:** `http://localhost:8080/api/health`
* **January evaluation:** `http://localhost:8080/api/evaluation/january-2026`

View container logs:

```bash
docker compose logs -f
```

Stop the application:

```bash
docker compose down
```

The backend uses the historical CSV reports included in the repository for the January evaluation. Forecast queries that retrieve new data from Elexon may require internet connectivity.

## API Endpoints

| Method | Endpoint                                                                             | Purpose                                                                       |
| ------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| GET    | `/api/health`                                                                        | Check backend health                                                          |
| GET    | `/api/forecast?start_date=2026-01-15&end_date=2026-01-16&decision_time_utc=10:00:00` | Retrieve forecast and actual data for the selected period and decision cutoff |
| GET    | `/api/evaluation/january-2026`                                                       | Retrieve January 2026 historical evaluation summaries and observations        |

The forecast endpoint accepts a delivery-date range and a UTC decision-time parameter. Refer to the route implementation for parameter validation and response details.

The API is served through Nginx when using Docker Compose. The backend application also exposes FastAPI's interactive documentation when accessed directly on its own port.

## Tests

Run the backend tests in an environment where the dependencies in `backend/requirements.txt` are installed:

```bash
cd backend
python -m pytest -v
```

The tests cover the evaluation metrics. The Docker-based API checks also confirmed successful responses from the health, forecast, and January evaluation endpoints in the local environment.

## Assumptions and Limitations

* The evaluation covers January 2026 only.
* The analysis is limited to UK national wind generation.
* Hourly actual generation requires both expected half-hourly readings.
* Forecast selection depends on the publication times available in the retrieved data.
* The 48-hour horizon has incomplete coverage and should not be compared without considering this limitation.
* Forecast accuracy alone does not determine an optimal procurement decision; demand, prices, market rules, and other generation sources are outside this pilot.
* Historical evaluation reports are snapshots and will not automatically update when new source data becomes available.
* The application is a pilot, not a production-hardened trading system.

## AI Tools and Development Assistance

ChatGPT was used as an AI-assisted development tool to help with implementation planning, debugging, code review, evaluation methodology discussions, and documentation. Generated suggestions were reviewed and tested against the project where practical. The project uses the Elexon BMRS datasets described above as its source data.

## Deployment Status

The application has been built and tested locally using Docker Compose. A public deployment URL has not yet been configured.

Before production deployment, the application would require appropriate hosting, HTTPS, security configuration, operational monitoring, logging, and further validation of source-data availability and decision-time assumptions.

## Future Improvements

* Expand the evaluation period beyond January 2026.
* Investigate and document missing 48-hour forecast coverage.
* Add automated data-quality and source-availability monitoring.
* Add broader statistical comparisons across delivery periods and wind-generation levels.
* Evaluate how forecast errors affect procurement decisions when demand and market-price data are available.
* Add deployment monitoring and production-grade operational safeguards.
