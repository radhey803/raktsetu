# ADR-003: Postponement of Machine Learning Forecasting until >= 60 Days of Real History

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Product Lead, Principal Data Engineer

---

## Context & Problem Statement
A common anti-pattern in early data products is marketing "AI/ML Blood Shortage Prediction" before sufficient real ground-truth time series exist. In blood banking:
- Inventory patterns exhibit strong weekly seasonality (blood donation drives occur on weekends; surgical procedures peak Tuesday-Thursday).
- Seasonal disease outbreaks (Dengue, Malaria in monsoon) cause dramatic plateaus and depletion spikes.
- Fitting an ARIMA, Prophet, or LSTM model on fewer than 2 months of daily data yields spurious trendlines, dangerous false-confidence alerts, and reputational risk.

---

## Decision
1. **No Mock Forecasts**: We strictly refuse to ship synthetic regression curves or pretend to forecast stock levels.
2. **Feature Flag & Requirement Stub**: `/v1/reports/forecast` returns an honest HTTP 200 payload with `status: "INSUFFICIENT_REAL_DATA"`, indicating the exact number of days currently accumulated vs. the required 60 days.
3. **Trigger Threshold**: Machine learning model training will activate only after $\ge 60$ consecutive days of verified daily snapshots exist in `fct_stock_snapshot`.

---

## Consequences
- **Positive**:
  - Builds clinical credibility with hospital blood bank officers and NGOs who immediately detect fake trends.
  - Avoids false alarm fatigue or erroneous shortage panics.
- **Negative**:
  - Delays marketing bullet point "AI-driven stock forecasting" during initial soft launch.
