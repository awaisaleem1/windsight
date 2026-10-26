import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString("en-GB", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function PerformanceCard({ label, value, unit, description }) {
  return (
    <article className="performance-metric-card">
      <span>{label}</span>
      <strong>
        {value}
        {unit && <small> {unit}</small>}
      </strong>
      <p>{description}</p>
    </article>
  );
}

export default function Performance({
  result,
  startDate,
  endDate,
  decisionTime,
  lastUpdated,
  onRefresh,
  loading: analysisLoading,
}) {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadEvaluation() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/evaluation/january-2026`
      );

      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          payload?.detail ||
            `Unable to load evaluation results (HTTP ${response.status}).`
        );
      }

      if (!payload || !Array.isArray(payload.summary)) {
        throw new Error("The API returned an unexpected evaluation response.");
      }

      setEvaluation(payload);
    } catch (err) {
      setError(
        err.message || "Cannot connect to the WindSight API."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvaluation();
  }, []);

  if (loading) {
    return (
      <main className="performance-page">
        <h1>Forecast Performance</h1>
        <p>Loading January 2026 evaluation results...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="performance-page">
        <h1>Forecast Performance</h1>
        <p className="performance-error">{error}</p>
        <button type="button" onClick={loadEvaluation}>
          Try again
        </button>
      </main>
    );
  }

  const summary = [...(evaluation?.summary ?? [])].sort(
    (a, b) => a.horizon_hours - b.horizon_hours
  );

  const matchedSummary = [...(evaluation?.matched_summary ?? [])].sort(
    (a, b) => a.horizon_hours - b.horizon_hours
  );

  const horizonLabel = (hours) => `${hours}h`;

  const maeData = summary.map((item) => ({
    horizon: horizonLabel(item.horizon_hours),
    mae: item.mae_mw,
  }));

  const rmseData = summary.map((item) => ({
    horizon: horizonLabel(item.horizon_hours),
    rmse: item.rmse_mw,
  }));

  const wapeData = summary.map((item) => ({
    horizon: horizonLabel(item.horizon_hours),
    wape: item.wape_percent,
  }));

  return (
    <main className="performance-page">
      {result && (
        <section className="performance-panel">
          <h2>Selected-period analysis</h2>

          <p>
            Period: {startDate} to {endDate} · Decision cutoff: {decisionTime} UTC
          </p>

          {analysisLoading && <p>Refreshing selected-period analysis...</p>}

          {result.metrics ? (
            <div className="performance-metric-grid">
              <PerformanceCard
                label="Mean Absolute Error"
                value={formatNumber(result.metrics.mae)}
                unit="MW"
                description="Average absolute forecast error"
              />

              <PerformanceCard
                label="Root Mean Squared Error"
                value={formatNumber(result.metrics.rmse)}
                unit="MW"
                description="Penalises larger errors"
              />

              <PerformanceCard
                label="Forecast Bias"
                value={formatNumber(result.metrics.bias)}
                unit="MW"
                description="Positive values indicate overforecasting"
              />

              <PerformanceCard
                label="WAPE"
                value={formatNumber(result.metrics.wape_percent)}
                unit="%"
                description="Error relative to total actual generation"
              />
            </div>
          ) : (
            <p>No matched actual and forecast observations are available.</p>
          )}

          <p>
            Observations: {result.metadata?.observations ?? 0} · Matched observations:{" "}
            {result.metadata?.matched_observations ?? 0}
          </p>

          <button
            type="button"
            onClick={onRefresh}
            disabled={analysisLoading}
          >
            {analysisLoading
              ? "Refreshing..."
              : "Refresh selected-period analysis"}
          </button>

          {lastUpdated && (
            <p>Last updated: {lastUpdated.toLocaleString()}</p>
          )}
        </section>
      )}

      <header className="performance-header">
        <div>
          <p className="performance-eyebrow">
            HISTORICAL MODEL EVALUATION
          </p>
          <h1>Forecast Performance</h1>
          <p>
            UK wind generation forecast accuracy across different
            minimum forecast lead times.
          </p>
        </div>

        <button
          type="button"
          onClick={loadEvaluation}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh evaluation"}
        </button>
      </header>

      <section className="performance-notice">
        <strong>Evaluation period: January 2026</strong>
        <p>
          Times are in UTC. Actual and forecast generation are measured
          in MW. Positive bias indicates overforecasting.
        </p>
      </section>

      <section className="performance-metric-grid">
        <PerformanceCard
          label="Best MAE"
          value={formatNumber(
            summary.reduce(
              (best, item) => item.mae_mw < best.mae_mw ? item : best
            ).mae_mw
          )}
          unit="MW"
          description="Lowest mean absolute error"
        />

        <PerformanceCard
          label="Best WAPE"
          value={formatNumber(
            Math.min(...summary.map((item) => item.wape_percent))
          )}
          unit="%"
          description="Lowest weighted absolute percentage error"
        />

        <PerformanceCard
          label="48-hour coverage"
          value={formatNumber(
            summary.find((item) => item.horizon_hours === 48)
              ?.coverage_percent
          )}
          unit="%"
          description="589 of 744 expected delivery hours"
        />

        <PerformanceCard
          label="Common evaluation hours"
          value={formatNumber(
            matchedSummary[0]?.matched_delivery_hours ?? 0,
            0
          )}
          description="Same delivery hours across all horizons"
        />
      </section>

      <section className="performance-chart-grid">
        <article className="performance-panel">
          <h2>Mean Absolute Error</h2>
          <p>Average absolute forecast error in MW. Lower is better.</p>

          <div className="performance-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={maeData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="horizon" />
                <YAxis />
                <Tooltip
                  formatter={(value) => [`${formatNumber(value)} MW`, "MAE"]}
                />
                <Bar dataKey="mae" name="MAE" fill="#0f766e" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="performance-panel">
          <h2>Root Mean Squared Error</h2>
          <p>Penalises larger errors more heavily. Lower is better.</p>

          <div className="performance-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rmseData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="horizon" />
                <YAxis />
                <Tooltip
                  formatter={(value) => [`${formatNumber(value)} MW`, "RMSE"]}
                />
                <Bar dataKey="rmse" name="RMSE" fill="#6478e8" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="performance-panel">
          <h2>Weighted Absolute Percentage Error</h2>
          <p>Absolute error relative to total actual generation. Lower is better.</p>

          <div className="performance-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wapeData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="horizon" />
                <YAxis />
                <Tooltip
                  formatter={(value) => [`${formatNumber(value)}%`, "WAPE"]}
                />
                <Bar dataKey="wape" name="WAPE" fill="#d97706" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="performance-panel">
        <h2>All available delivery hours</h2>
        <p>
          Each horizon uses all delivery hours for which an eligible
          forecast is available.
        </p>

        <div className="performance-table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Horizon</th>
                <th>Observations</th>
                <th>Coverage</th>
                <th>MAE (MW)</th>
                <th>RMSE (MW)</th>
                <th>Bias (MW)</th>
                <th>WAPE (%)</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((item) => (
                <tr key={item.horizon_hours}>
                  <td>{item.horizon_hours} hours</td>
                  <td>{item.observations}</td>
                  <td>{formatNumber(item.coverage_percent)}%</td>
                  <td>{formatNumber(item.mae_mw)}</td>
                  <td>{formatNumber(item.rmse_mw)}</td>
                  <td className={item.bias_mw > 0 ? "bias-positive" : ""}>
                    {item.bias_mw > 0 ? "+" : ""}
                    {formatNumber(item.bias_mw)}
                  </td>
                  <td>{formatNumber(item.wape_percent)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="performance-panel">
        <h2>Matched-hours comparison</h2>
        <p>
          A fairer comparison using the same 589 delivery hours for
          every horizon.
        </p>

        <div className="performance-table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Horizon</th>
                <th>Matched hours</th>
                <th>MAE (MW)</th>
                <th>RMSE (MW)</th>
                <th>Bias (MW)</th>
                <th>WAPE (%)</th>
              </tr>
            </thead>
            <tbody>
              {matchedSummary.map((item) => (
                <tr key={item.horizon_hours}>
                  <td>{item.horizon_hours} hours</td>
                  <td>{item.matched_delivery_hours}</td>
                  <td>{formatNumber(item.mae_mw)}</td>
                  <td>{formatNumber(item.rmse_mw)}</td>
                  <td>
                    {item.bias_mw > 0 ? "+" : ""}
                    {formatNumber(item.bias_mw)}
                  </td>
                  <td>{formatNumber(item.wape_percent)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="performance-notice">
        <strong>Interpretation</strong>
        <p>
          Positive bias means forecasts exceeded actual generation on
          average. The 48-hour results have lower coverage, so compare
          the matched-hours table when assessing differences between
          horizons.
        </p>
        <p>
          Horizon values represent minimum forecast lead times, not
          exact forecast ages. The selection rule uses the latest
          publication available at or before delivery time minus the
          requested horizon.
        </p>
      </section>
    </main>
  );
}