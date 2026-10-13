# Presentation outline (7 slides + live demo)

## Slide 1 — Title and motivation
Forecasting Indian Stock Returns from Supplier Stocks with ML. Team: [names]. Course: UE24CS352A.
Motivation: carmakers depend on their suppliers. Do suppliers' stock moves help predict the carmaker's stock? Based on a Stanford CS229 report about Volkswagen.

## Slide 2 — The reference paper in one slide
- VW plus 30 suppliers × 28 days of lagged returns, plus macro data
- Models: Elastic Net, Decision Tree, XGBoost, LightGBM; Elastic Net was best
- Strategy: +21.49% vs +7.98% buy-and-hold
- Its gaps, which we address: no baseline (predict-0 is almost as good), missing values filled with 0, no transaction costs, no risk measures, best result picked from 96 strategy variants

## Slide 3 — Problem and data
- Target: Maruti Suzuki (MARUTI.NS), forward 5-day return
- Peers: 9 supplier stocks + the NIFTY 50
- Source: Yahoo Finance, [dates], [N] rows
- Missing data: late listings dropped, short gaps forward-filled

## Slide 4 — Features and models
- Own features: momentum, moving-average gaps, volatility, volume, intraday range
- Peer features: each peer's last L daily returns
- Models: Elastic Net, Decision Tree, Random Forest, Gradient Boosting, plus predict-0 and historical-mean baselines

## Slide 5 — Experimental design
- Time-ordered 60/20/20 split with an embargo
- Tune on validation, test once
- Ablation: with vs without peers
- Walk-forward over 5 periods
- Metrics: RMSE, MAE, direction accuracy, skill vs predict-0

## Slide 6 — Results + live demo
- Test metrics table (with baselines)
- Peer ablation
- Importance by source
- Equity curve vs buy-and-hold, and the threshold table
- Walk-forward summary
- Label the data source and period

## Slide 7 — Conclusion, limitations, contributions
- What the results do and do not show
- How transaction costs change the strategy
- Limitations and future work
- Each member's contribution

## Live demo script (~2 min)
1. App already running. Select Yahoo Finance and MARUTI.NS (or Upload CSV with the saved backup files).
2. Data overview: rows, dates, which peers were used or dropped.
3. Click Train. Show the selected model and whether it beats predict-0.
4. Show importance by source and the with/without-peers table.
5. Strategy: move the cost slider and show the result change instantly.
6. Click walk-forward and show how stable the results are across periods.
