# Indian Stock Return Forecasting with Machine Learning

An ML mini-project (UE24CS352A) that adapts the method of the Stanford CS229 report *"Quantitative Trading with Machine Learning"* (R. M. Glawion, 2021) to Indian stocks. The paper predicts Volkswagen's returns from the past returns of its suppliers' stocks. We do the same for an Indian automaker, **Maruti Suzuki (`MARUTI.NS`)**, using its listed suppliers and the NIFTY 50 index, and we add the stock's own price/volume features, which the paper listed as future work.

> Educational project only. Historical backtests are not evidence of future profitability and are not financial advice.

## What it does
- Downloads daily data for a target stock and optional supplier/peer stocks via `yfinance` (or reads saved CSVs).
- Builds 11 own price/volume features plus lagged daily returns of each peer (default 5 lags; the paper used 28).
- Predicts the forward **h-day return** (h = 1, 5 or 20) with **Elastic Net, Decision Tree, Random Forest and Gradient Boosting**.
- Compares every model with two baselines: **predict 0** (the paper's footnote 3) and **historical mean**.
- **Tunes hyperparameters** on a validation set, then scores each model once on an untouched test set.
- Checks whether the supplier/peer features help (**ablation**: the same model with and without them).
- Runs a **long/flat trading backtest** with transaction costs, and reports return, volatility, Sharpe ratio, max drawdown and number of trades. Includes a **threshold sensitivity table**, like the paper's Table 2.
- **Robustness checks**: walk-forward evaluation over 5 periods, and a horizon comparison table like the paper's Table 1.
- A Streamlit dashboard for the live demo, a command-line script that saves every result table for the write-up, and automated tests.

## Quick start (Windows)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
If PowerShell blocks activation, use Command Prompt: `.venv\Scripts\activate.bat`

macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`, then the same `pip` and `streamlit` commands.

## Reproduce the results for the write-up
```bash
python run_experiment.py --ticker MARUTI.NS              # with suppliers + NIFTY 50
python run_experiment.py --ticker MARUTI.NS --no-peers   # own features only, for comparison
```
Everything is saved to `reports/results/<ticker>/`. That includes `summary.md` (all tables, ready to copy), CSVs of every table, `equity_curve.png`, and the downloaded data (`data_target.csv`, `data_peers.csv`), which you can reuse offline:
```bash
python run_experiment.py --csv reports/results/MARUTI.NS/data_target.csv --peers-csv reports/results/MARUTI.NS/data_peers.csv
```
Other options: `--horizon 1|5|20`, `--peer-lags 28`, `--threshold 0.25`, `--cost 0.05`, `--no-tune`, `--peers T1 T2 ...`.

## Run the tests
```bash
python -m pytest -q
```
The tests check that features never use future prices, that the target equals the forward return, that the split is time-ordered with an embargo, that late-listed peers are dropped, that the predict-0 baseline is computed correctly, and that the backtest signal is lagged and pays costs.

## Data
| Role | Tickers (Yahoo Finance) |
|---|---|
| Target | `MARUTI.NS` (Maruti Suzuki) |
| Auto components | `MOTHERSON.NS`, `BOSCHLTD.NS`, `UNOMINDA.NS`, `ENDURANCE.NS` |
| Tyres / batteries | `MRF.NS`, `APOLLOTYRE.NS`, `EXIDEIND.NS` |
| Steel | `TATASTEEL.NS`, `JSWSTEEL.NS` |
| Market | `^NSEI` (NIFTY 50) |

These are publicly listed companies in Maruti's broad supplier base (components, tyres, batteries, steel). The list is our own selection, not a verified supply-contract dataset. Any ticker can be entered in the app or passed with `--peers`.

**Missing data.** A peer that covers less than 90% of the target's trading days (e.g. a late listing) is dropped and reported. Short gaps caused by different holidays are forward-filled for at most 5 days, using past prices only. Rows that still have missing values are removed. We never fill with 0, which is what the paper did.

**Offline demo.** `data/synthetic_demo.csv` and `data/synthetic_peers_demo.csv` are **simulated** data, made by `scripts/make_synthetic_peers.py`. They exist only so the app works without internet. They are not market data and must not be reported as results.

**CSV format.** For the target: `Date, Open, High, Low, Close, Volume` (`Datetime` is also accepted). For peers: `Date`, then one closing-price column per ticker.

## Methodology
1. **Features (at day t, using data up to day t only).**
   - Own features: 1-, 5- and 20-day returns; price vs 5/20/50-day moving average; 10- and 20-day volatility; volume change; intraday range; close location within the day's range.
   - Peer features: each peer's daily return on days t, t−1, …, t−(L−1).
2. **Target.** `Close[t+h] / Close[t] − 1`.
3. **Split.** Chronological 60% train / 20% validation / 20% test. The last h rows before each boundary are dropped (an embargo), so no training target overlaps a later block.
4. **Models and tuning.** Each model is tuned over a small grid on validation RMSE.
   - Elastic Net: `alpha` ∈ {1e-4, 1e-3, 1e-2}, `l1_ratio` ∈ {0.1, 0.5, 1}. The `l1_ratio` grid mirrors the paper's α ∈ {0, .5, 1}. scikit-learn's `alpha` is the overall penalty strength; the paper's α is the L1/L2 mix, which scikit-learn calls `l1_ratio`.
   - Decision Tree: `max_depth` ∈ {3, 5, 8}, `min_samples_leaf` ∈ {10, 30}.
   - Random Forest (150 trees): `max_depth` ∈ {4, 8}, `min_samples_leaf` ∈ {5, 20}.
   - Gradient Boosting (scikit-learn's `HistGradientBoostingRegressor`, similar to LightGBM): `learning_rate` ∈ {0.05, 0.1}, `max_depth` ∈ {2, 3}.
   - The model with the lowest validation RMSE is selected. Every model is then refit on train+validation and scored **once** on test.
5. **Metrics.** RMSE, MAE, direction accuracy, and **skill vs predict-0** = 1 − SSE(model) / SSE(predict 0). A positive value means the model beats always guessing "no change".
6. **Ablation.** The selected model is retrained with own features only, to measure what the peers add.
7. **Backtest.** Long/flat. Hold the stock on day t only if the forecast made at the close of day t−1 is above the threshold; otherwise hold cash. Each buy or sell costs the chosen percentage (default 0.05%). Positions are held one day at a time, so overlapping h-day forecasts are not double-counted. Results are compared with buy-and-hold over the same days.
8. **Walk-forward.** The second half of the history is cut into 5 consecutive test periods. For each one, models are trained on all earlier data (minus the embargo) with default settings. This is closer to the paper's 109-step rolling window.

**Limitations.** One split for tuning; fixed small grids; no slippage, taxes or liquidity limits; the supplier list is hand-picked; correlation is not causation; and markets change over time.

## Differences from the Stanford paper
| | Paper | This project |
|---|---|---|
| Target | Volkswagen (Frankfurt) | Maruti Suzuki (NSE), or any ticker |
| Features | 30 suppliers × 28 lags + macro | ~10 peers × L lags + 11 own price/volume features |
| Models | Elastic Net, Decision Tree, XGBoost, LightGBM | Elastic Net, Decision Tree, Random Forest, Gradient Boosting |
| Baseline | Footnote only | Predict-0 and historical-mean rows in every table |
| Missing values | Filled with 0 | Late listings dropped; short gaps forward-filled |
| Evaluation | Rolling, 109 refits | Single tuned split + 5-period walk-forward |
| Strategy | Long/short, no costs | Long/flat, with costs |
| Risk | Not reported | Volatility, Sharpe ratio, max drawdown, trades |

## Project structure
```text
app.py                         Streamlit dashboard (live demo)
trading_ml.py                  data, features, models, evaluation, backtest
run_experiment.py              command-line run that saves all tables/charts
tests/test_pipeline.py         leakage and correctness tests
scripts/make_synthetic_peers.py  generator for the simulated peer demo data
data/                          simulated demo CSVs (not market data)
reports/                       write-up and presentation outline; results/ is created by run_experiment.py
```

## Team contributions
- **[Member 1]:** [fill in, e.g. data pipeline, feature engineering, tests]
- **[Member 2]:** [fill in, e.g. models and tuning, backtest, dashboard, write-up]

## Submission checklist
- [ ] Private GitHub repository, shared with faculty/TAs
- [ ] Ran `run_experiment.py` on real data and pasted the numbers into the write-up and slides
- [ ] Write-up exported as PDF
- [ ] Saved data CSVs as a backup in case Yahoo fails during the demo
- [ ] Team contributions filled in above
