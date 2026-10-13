# Forecasting Indian Stock Returns from Supplier Stocks with Machine Learning
**Course:** UE24CS352A — Machine Learning  
**Project type:** Mini-project  
**Team members:** [Member 1], [Member 2]

## 1. Problem statement
Can the past returns of an Indian automaker's suppliers, together with the stock's own price and volume history, predict its return over the next few trading days better than simply guessing "no change"? And does a simple trading rule built on those forecasts beat buy-and-hold once transaction costs are included?

We adapt the method of René M. Glawion's Stanford CS229 report *Quantitative Trading with Machine Learning* (2021). That report predicted Volkswagen's returns from 30 suppliers' returns and found Elastic Net best across horizons. We apply the same idea to Maruti Suzuki (NSE), add the stock's own OHLCV features (listed as future work in the report), and address several of its limitations: no baseline, zero-filled missing data, no transaction costs and no risk measures.

## 2. Dataset
Daily adjusted prices from Yahoo Finance via `yfinance`, [START DATE] to [END DATE].
- **Target:** `MARUTI.NS`.
- **Peers:** auto components (`MOTHERSON.NS`, `BOSCHLTD.NS`, `UNOMINDA.NS`, `ENDURANCE.NS`), tyres/batteries (`MRF.NS`, `APOLLOTYRE.NS`, `EXIDEIND.NS`), steel (`TATASTEEL.NS`, `JSWSTEEL.NS`) and the NIFTY 50 index (`^NSEI`).
- **Size:** [N] rows after feature engineering. [List any peers dropped for low coverage.]
- **Missing data:** peers covering less than 90% of trading days are dropped. Holiday gaps are forward-filled for at most 5 days, using past prices only. Nothing is filled with zero.

## 3. Approach
**Features at day t (no future data):**
- 11 own features: 1/5/20-day returns, price relative to its 5/20/50-day moving averages, 10/20-day volatility, volume change, intraday range, and close location within the day's range.
- For each peer: its daily return on each of the last [L] days.

**Target:** the forward h-day return, `Close[t+h]/Close[t] − 1`, with h = 5 (also tested at 1 and 20).

**Models:** Elastic Net, Decision Tree, Random Forest and Gradient Boosting, compared with two baselines: predict 0 and historical mean.

**Evaluation:**
- A chronological 60/20/20 train/validation/test split, with an h-row embargo before each boundary so that no training target overlaps a later period.
- Hyperparameters are tuned on validation RMSE. The best model is chosen on validation, and all models are refit on train+validation and scored once on test.
- Metrics: RMSE, MAE, direction accuracy, and skill vs predict-0.
- An ablation retrains the chosen model without peer features.
- A 5-period walk-forward evaluation checks stability over time.

**Backtest:** long/flat. Hold the stock on day t if the forecast made at close t−1 exceeds a threshold; otherwise hold cash. Each trade costs 0.05%. We report total and annual return, volatility, Sharpe ratio, max drawdown and number of trades, compared with buy-and-hold.

## 4. Implementation
- `trading_ml.py` contains data cleaning, peer alignment, feature engineering, splitting, model tuning, metrics, ablation, walk-forward evaluation and the backtest.
- `app.py` is a Streamlit dashboard. It works with Yahoo Finance, uploaded CSVs, or a clearly labelled simulated dataset for offline demos.
- `run_experiment.py` reproduces every table in this report and saves them to `reports/results/`.
- `tests/test_pipeline.py` checks for look-ahead leakage, the correct target, the split embargo and the backtest timing.

## 5. Results
*(Fill in from `reports/results/MARUTI.NS/summary.md` — do not invent numbers or report synthetic-data results.)*

| Model | Test RMSE (%) | MAE (%) | Direction acc. (%) | Skill vs predict-0 (%) |
|---|---|---|---|---|
| Baseline: predict 0 | | | — | 0 |
| [best model] | | | | |
| … | | | | |

- Peers vs own-only (same model): RMSE [x]% vs [y]%.
- Strategy vs buy-and-hold: [x]% vs [y]% total return; max drawdown [x]% vs [y]%; [n] trades.
- Walk-forward: [model] beat predict-0 in [k]/5 periods.

## 6. Conclusion
[Write after running. Questions to answer:]
- Did any model beat predict-0 on test, and consistently across the walk-forward periods?
- Did supplier features improve on own-only features?
- Does the strategy result agree with the forecast metrics, and how much do transaction costs change it?

The paper itself notes that predicting zero gives almost the same RMSE, because daily returns are mostly noise. A small or absent edge is therefore an expected and honest result.

**Limitations:**
- A hand-picked supplier list, not verified contracts
- One tuning split and small grids
- No slippage or taxes
- Correlation, not causation
- Market behaviour changes over time

**Future work:**
- Verified supply-chain data
- Macro variables (bond yields, INR/USD)
- Rolling re-tuning
- Testing other Indian automakers
