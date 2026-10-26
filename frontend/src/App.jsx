
import { useCallback, useState } from "react";
import Performance from "./Performance";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "./App.css";

const API_URL = import.meta.env.VITE_API_BASE_URL || "";

const INITIAL_START_DATE = "2026-01-15";
const INITIAL_END_DATE = "2026-01-16";

function number(value, decimals = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString("en-GB", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatTime(value) {
  if (!value) return "Unavailable";

  return new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function MetricCard({ label, value, unit, description }) {
  return (
    <article className="metric-card">
      <span className="metric-label">{label}</span>

      <div className="metric-value">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>

      <p className="metric-description">{description}</p>
    </article>
  );
}

function App() {
  const [activePage, setActivePage] = useState("overview");
  const [startDate, setStartDate] = useState(INITIAL_START_DATE);
  const [endDate, setEndDate] = useState(INITIAL_END_DATE);
  const [decisionTime, setDecisionTime] = useState("10:00");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadData = useCallback(
    async (event) => {
      event?.preventDefault();

      if (startDate > endDate) {
        setError("Start date cannot be after end date.");
        return;
      }

      setLoading(true);
      setError("");

      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        decision_time_utc: decisionTime.length === 5
          ? `${decisionTime}:00`
          : decisionTime,
      });

      try {
        const response = await fetch(
          `${API_URL}/api/forecast?${params.toString()}`
        );

        const payload = await response.json();

        if (!response.ok) {
          throw new Error(
            payload.detail || "The forecast request failed."
          );
        }

        setResult(payload);
        setLastUpdated(new Date());
      } catch (err) {
        setError(
          err.message ||
            "Cannot connect to the API. Check that your backend is running."
        );
      } finally {
        setLoading(false);
      }
    },
    [startDate, endDate, decisionTime]
  );

  const metadata = result?.metadata;
  const metrics = result?.metrics;
  const rows = result?.data ?? [];

  const chartRows = rows.map((row) => ({
    ...row,
    chartTime: formatTime(row.startTime),
  }));

  const matchedCount = rows.filter(
    (row) => row.actual != null && row.forecast != null
  ).length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview">
          <span className="brand-mark">W</span>

          <span className="brand-copy">
            <strong>WindSight</strong>
            <small>Forecast Intelligence</small>
          </span>
        </a>

        <p className="sidebar-label">WORKSPACE</p>

        <nav className="sidebar-nav">
          <button
            type="button"
            className={`nav-link ${activePage === "overview" ? "active" : ""}`}
            onClick={() => setActivePage("overview")}
          >
            <span>◈</span> Overview
          </button>

          <button
            type="button"
            className={`nav-link ${activePage === "performance" ? "active" : ""}`}
            onClick={() => setActivePage("performance")}
          >
            <span>▤</span> Performance
          </button>

          <button
            type="button"
            className="nav-link"
            onClick={() => {
              setActivePage("overview");
              setTimeout(() => {
                document.getElementById("hourly-data")?.scrollIntoView({
                  behavior: "smooth",
                });
              }, 0);
            }}
          >
            <span>▦</span> Hourly data
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="connection-status">
            <span className="status-dot" />
            WindSight analytics
          </div>

          <p>UK wind generation</p>
          <small>Prototype · v1.0</small>
        </div>
      </aside>

      <main className="main-content" id="overview">
        {activePage === "performance" ? (
          <Performance
            result={result}
            startDate={startDate}
            endDate={endDate}
            decisionTime={decisionTime}
            lastUpdated={lastUpdated}
            onRefresh={loadData}
            loading={loading}
          />
        ) : (
          <>
        <header className="page-header">
          <div>
            <p className="eyebrow">ENERGY INTELLIGENCE / UNITED KINGDOM</p>
            <h1>Wind Forecast Dashboard</h1>

            <p className="page-description">
              Explore day-ahead wind generation forecast accuracy.
            </p>
          </div>

          <button
            className="secondary-button"
            type="button"
            onClick={() => loadData()}
            disabled={loading}
          >
            {loading ? "Loading..." : "↻ Refresh data"}
          </button>
        </header>

        <section className="filter-panel">
          <div className="section-heading">
            <div>
              <h2>Analysis period</h2>
              <p>Choose a settlement period to analyse.</p>
            </div>

            <span className="timezone-label">Times shown in UTC</span>
          </div>

          <form className="filter-form" onSubmit={loadData}>
            <label>
              <span>Start date</span>
              <input
                type="date"
                value={startDate}
                max={endDate}
                required
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>

            <label>
              <span>End date</span>
              <input
                type="date"
                value={endDate}
                min={startDate}
                required
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>

            <label>
              <span>Decision cutoff (UTC)</span>
              <input
                type="time"
                step="60"
                value={decisionTime.slice(0, 5)}
                required
                onChange={(event) => setDecisionTime(event.target.value)}
              />
            </label>

            <button className="primary-button" type="submit" disabled={loading}>
              Run analysis <span>→</span>
            </button>
          </form>

          <p className="assumption-note">
            The 10:00 UTC cutoff is illustrative and has not been verified as
            the utility's actual procurement deadline.
          </p>
        </section>

        {error && (
          <div className="error-message" role="alert">
            <strong>Data request failed</strong>
            <span>{error}</span>

            <button type="button" onClick={() => loadData()}>
              Try again
            </button>
          </div>
        )}

        {loading && !result ? (
          <section className="loading-panel">
            <div className="spinner" />
            <h2>Loading forecast data</h2>
            <p>Requesting historical observations from WindSight's API.</p>
          </section>
        ) : (
          <>
            <section className="metrics-section" id="performance">
              <div className="section-heading">
                <div>
                  <h2>Forecast performance</h2>
                  <p>Calculated from periods with matched actuals and forecasts.</p>
                </div>

                <span className="count-label">
                  {matchedCount.toLocaleString("en-GB")} matched periods
                </span>
              </div>

              <div className="metrics-grid">
                <MetricCard
                  label="Mean Absolute Error"
                  value={number(metrics?.mae)}
                  unit="MW"
                  description="Average absolute forecast error"
                />

                <MetricCard
                  label="Root Mean Squared Error"
                  value={number(metrics?.rmse)}
                  unit="MW"
                  description="Penalises larger errors more heavily"
                />

                <MetricCard
                  label="Forecast Bias"
                  value={number(metrics?.bias)}
                  unit="MW"
                  description={
                    metrics?.bias > 0
                      ? "Positive bias · overforecasting"
                      : metrics?.bias < 0
                        ? "Negative bias · underforecasting"
                        : "Average forecast minus actual"
                  }
                />

                <MetricCard
                  label="Weighted Absolute Percentage Error"
                  value={number(metrics?.wape_percent)}
                  unit="%"
                  description="Absolute error relative to total actual generation"
                />
              </div>
            </section>

            <section className="summary-grid">
              <article className="summary-card">
                <span className="summary-icon">◷</span>

                <div>
                  <p>Hourly observations</p>
                  <strong>{metadata?.observations ?? 0}</strong>
                  <small>Delivery hours returned</small>
                </div>
              </article>

              <article className="summary-card">
                <span className="summary-icon">✓</span>

                <div>
                  <p>Forecast coverage</p>
                  <strong>
                    {number(metadata?.forecast_coverage_percent)}%
                  </strong>
                  <small>Periods with matched forecasts</small>
                </div>
              </article>

              <article className="summary-card">
                <span className="summary-icon">!</span>

                <div>
                  <p>Missing forecasts</p>
                  <strong>
                    {metadata?.missing_forecast_observations ?? 0}
                  </strong>
                  <small>No eligible forecast available</small>
                </div>
              </article>
            </section>

            <section className="content-panel chart-panel">
              <div className="section-heading">
                <div>
                  <h2>Actual vs forecast generation</h2>
                  <p>Hourly wind generation across the selected period.</p>
                </div>

                <span className="unit-label">MW</span>
              </div>

              {rows.length > 0 ? (
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartRows}
                      margin={{
                        top: 12,
                        right: 20,
                        left: 12,
                        bottom: 16,
                      }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                      />

                      <XAxis
                        dataKey="chartTime"
                        tick={{ fontSize: 11 }}
                        minTickGap={28}
                      />

                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickFormatter={(value) =>
                          Number(value).toLocaleString("en-GB")
                        }
                        width={75}
                      />

                      <Tooltip
                        formatter={(value, name) => [
                          `${number(value)} MW`,
                          name,
                        ]}
                        labelFormatter={(label) => `${label} UTC`}
                      />

                      <Legend />

                      <Line
                        type="monotone"
                        dataKey="actual"
                        name="Actual generation"
                        stroke="#0f766e"
                        strokeWidth={2.5}
                        dot={false}
                        connectNulls={false}
                      />

                      <Line
                        type="monotone"
                        dataKey="forecast"
                        name="Day-ahead forecast"
                        stroke="#6478e8"
                        strokeWidth={2.5}
                        strokeDasharray="6 4"
                        dot={false}
                        connectNulls={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="empty-state">
                  <h3>No hourly observations found</h3>
                  <p>Try another date range.</p>
                </div>
              )}
            </section>

            <section className="content-panel table-panel" id="hourly-data">
              <div className="section-heading">
                <div>
                  <h2>Hourly observations</h2>
                  <p>Actuals, selected forecasts, and publication cutoffs.</p>
                </div>

                <span className="count-label">
                  {rows.length.toLocaleString("en-GB")} rows
                </span>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Delivery time (UTC)</th>
                      <th>Actual (MW)</th>
                      <th>Forecast (MW)</th>
                      <th>Error (MW)</th>
                      <th>Published (UTC)</th>
                      <th>Decision cutoff (UTC)</th>
                      <th>Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {rows.map((row) => {
                      const matched =
                        row.actual != null && row.forecast != null;

                      const errorValue = matched
                        ? Number(row.forecast) - Number(row.actual)
                        : null;

                      return (
                        <tr key={row.startTime}>
                          <td className="time-cell">
                            {formatTime(row.startTime)}
                          </td>

                          <td>{number(row.actual)}</td>
                          <td>{number(row.forecast)}</td>

                          <td
                            className={
                              errorValue == null
                                ? ""
                                : errorValue > 0
                                  ? "positive-error"
                                  : errorValue < 0
                                    ? "negative-error"
                                    : ""
                            }
                          >
                            {number(errorValue)}
                          </td>

                          <td>{formatTime(row.forecast_publish_time)}</td>
                          <td>{formatTime(row.decision_cutoff)}</td>

                          <td>
                            <span
                              className={`record-status ${
                                matched ? "status-matched" : "status-missing"
                              }`}
                            >
                              {matched ? "Matched" : "Missing"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
          </>
        )}

        <footer className="page-footer">
          <div>
            <strong>WindSight</strong>
            <span>Day-Ahead Wind Forecast Intelligence</span>
          </div>

          <div className="footer-meta">
            <span>
              {lastUpdated
                ? `Last updated ${lastUpdated.toLocaleTimeString("en-GB")}`
                : "Waiting for data"}
            </span>

            <span>Data source: Elexon BMRS</span>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
