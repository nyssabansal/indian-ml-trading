from pathlib import Path

import pandas as pd
import streamlit as st

from trading_ml import (
    DEFAULT_PEERS, DEFAULT_TARGET, backtest, compare_horizons, download_peer_closes,
    download_yfinance, make_features, normalize_peers, own_vs_peer_ablation,
    threshold_table, train_and_evaluate, walk_forward,
)

ROOT = Path(__file__).parent
DEMO_PATH = ROOT / "data" / "synthetic_demo.csv"
DEMO_PEERS_PATH = ROOT / "data" / "synthetic_peers_demo.csv"

st.set_page_config(page_title="SentinelQuant | Indian ML Trading Lab", page_icon="📈", layout="wide")
st.title("📈 SentinelQuant")
st.caption("Indian stock-return forecasting with machine learning — educational research prototype")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1 · Data")
    source = st.radio("Source", ["Bundled synthetic demo", "Upload CSV", "Download from Yahoo Finance"])
    uploaded = uploaded_peers = None
    ticker, peer_text, period, use_demo_peers = DEFAULT_TARGET, ", ".join(DEFAULT_PEERS), "10y", True
    if source == "Bundled synthetic demo":
        use_demo_peers = st.checkbox("Include synthetic peer stocks", True)
    elif source == "Upload CSV":
        uploaded = st.file_uploader("Target stock OHLCV CSV", type=["csv"])
        uploaded_peers = st.file_uploader("Optional: supplier/peer closes CSV", type=["csv"],
                                          help="Columns: Date, then one closing-price column per ticker.")
    else:
        ticker = st.text_input("Target ticker", DEFAULT_TARGET,
                               help="e.g. MARUTI.NS, RELIANCE.NS, TCS.NS")
        peer_text = st.text_area("Supplier / peer tickers (comma separated, optional)", peer_text,
                                 help="Their past returns become extra features, as in the Stanford paper.")
        period = st.selectbox("History", ["5y", "10y", "max"], index=1)

    st.header("2 · Model")
    horizon = st.selectbox("Forecast horizon (trading days)", [1, 5, 20], index=1)
    peer_lags = st.slider("Peer return lags (days)", 1, 28, 5,
                          help="The paper used 28 days of lagged supplier returns.")
    tune = st.checkbox("Tune hyperparameters on validation set", True)

    st.header("3 · Strategy")
    threshold = st.slider("Buy threshold: predicted return above (%)", 0.0, 2.0, 0.25, 0.05)
    costs = st.slider("Transaction cost per buy/sell (%)", 0.0, 0.5, 0.05, 0.01)


# ---------------------------------------------------------------- loading
@st.cache_data(show_spinner=False)
def load_demo(with_peers: bool):
    peers = pd.read_csv(DEMO_PEERS_PATH) if with_peers else None
    return pd.read_csv(DEMO_PATH), peers


@st.cache_data(show_spinner=False, ttl=3600)
def load_yahoo(tkr: str, peers_csv: str, per: str):
    frame = download_yfinance(tkr, per)
    peer_list = [p.strip() for p in peers_csv.split(",") if p.strip()]
    peers, failed = download_peer_closes(peer_list, per) if peer_list else (None, [])
    return frame, peers, failed


frame = peers_raw = None
failed_peers = []
try:
    if source == "Bundled synthetic demo":
        frame, peers_raw = load_demo(use_demo_peers)
        st.info("You are using **simulated** data for an offline demo. "
                "Its results say nothing about real markets.")
    elif source == "Upload CSV":
        if uploaded is None:
            st.warning("Upload a CSV with Date, Open, High, Low, Close, Volume columns.")
        else:
            frame = pd.read_csv(uploaded)
            peers_raw = pd.read_csv(uploaded_peers) if uploaded_peers is not None else None
    else:
        with st.spinner(f"Downloading {ticker} and peers…"):
            frame, peers_raw, failed_peers = load_yahoo(ticker.strip(), peer_text, period)
except Exception as exc:
    st.error(f"Could not load data: {exc}")

if frame is None:
    st.stop()

if failed_peers:
    st.warning("No data for: " + ", ".join(failed_peers) + ". They were skipped — check the tickers on finance.yahoo.com.")

try:
    peers = normalize_peers(peers_raw) if peers_raw is not None else None
    data, features, info = make_features(frame, horizon, peers, peer_lags)
except Exception as exc:
    st.error(f"Data validation / feature engineering failed: {exc}")
    st.stop()


# ---------------------------------------------------------------- 1. data
st.subheader("1. Data overview")
a, b, c, d = st.columns(4)
a.metric("Rows used", f"{len(data):,}")
b.metric("First date", str(data["Date"].min().date()))
c.metric("Last date", str(data["Date"].max().date()))
d.metric("Features", f"{len(features)}")
st.line_chart(data.set_index("Date")["Close"])
peer_msg = (f"Peers used: {', '.join(info['peers_used'])} × {info['peer_lags']} lags."
            if info["peers_used"] else "No peer stocks — own price/volume features only.")
if info["peers_dropped"]:
    peer_msg += " Dropped (too little history, % coverage): " + ", ".join(
        f"{k} ({v}%)" for k, v in info["peers_dropped"].items())
st.caption(f"Target: forward {horizon}-day return. {peer_msg}")

if source == "Download from Yahoo Finance":
    with st.expander("Save this data for an offline backup"):
        st.download_button("Download target CSV", frame.to_csv(index=False).encode(),
                           f"{ticker}_ohlcv.csv", "text/csv")
        if peers_raw is not None:
            st.download_button("Download peers CSV", peers_raw.to_csv(index=False).encode(),
                               f"{ticker}_peers.csv", "text/csv")
        st.caption("If Yahoo fails during the demo, use 'Upload CSV' with these files.")

config = (source, ticker, peer_text, period, use_demo_peers, horizon, peer_lags, tune,
          getattr(uploaded, "name", None), getattr(uploaded_peers, "name", None))
if st.button("Train models and evaluate", type="primary"):
    with st.spinner("Tuning and evaluating models…"):
        result = train_and_evaluate(data, features, horizon, tune)
        result["ablation"] = own_vs_peer_ablation(
            data, features, result["best_name"], result["best_params"][result["best_name"]], horizon)
        st.session_state.update(result=result, config=config, wf=None)

if "result" not in st.session_state:
    st.stop()
result = st.session_state["result"]
if st.session_state.get("config") != config:
    st.warning("Settings changed since the last training run — click **Train** again to update.")


# ---------------------------------------------------------------- 2. models
st.divider()
st.subheader("2. Model evaluation (test set)")
metrics = result["metrics"]
best = result["best_name"]
zero_rmse = metrics.loc[metrics["Model"] == "Baseline: predict 0", "RMSE (%)"].iloc[0]
best_rmse = metrics.loc[metrics["Model"] == best, "RMSE (%)"].iloc[0]
verdict = "beats" if best_rmse < zero_rmse else "does **not** beat"
params_str = ", ".join(f"{k}={v}" for k, v in result["best_params"][best].items())
st.success(f"Selected on validation RMSE: **{best}** ({params_str}). "
           f"Test RMSE {best_rmse:.3f}% {verdict} the predict-0 baseline ({zero_rmse:.3f}%).")
st.dataframe(metrics.round(3), hide_index=True)
st.caption("Skill vs predict-0 > 0 means fewer squared errors than always guessing 'no change'. "
           "Direction accuracy is blank for predict-0 because it never says up or down. "
           f"Rows — train {result['n_train']:,}, validation {result['n_validation']:,}, "
           f"test {result['n_test']:,}; {horizon} rows dropped before each boundary (embargo).")
dates = result["dates"]
st.caption(" · ".join(f"{k}: {v[0].date()} → {v[1].date()}" for k, v in dates.items()))
with st.expander("Hyperparameter tuning (validation RMSE for every setting tried)"):
    st.dataframe(result["tuning"].round(4), hide_index=True)


# ---------------------------------------------------------------- 3. features
st.subheader("3. What drove the predictions?")
imp, groups = result["feature_importance"], result["group_importance"]
if imp.empty or imp["Importance"].sum() == 0:
    st.info(f"{best} gave every feature zero weight — it is effectively predicting the historical "
            "average. That means no feature carried a reliable signal in this data.")
else:
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Top features** ({imp['Method'].iloc[0]})")
        st.dataframe(imp.head(10)[["Feature", "Importance"]].round(5), hide_index=True)
    with right:
        st.markdown("**Importance by source**")
        st.bar_chart(groups.set_index("Source")["Share (%)"])
if result.get("ablation") is not None:
    st.markdown("**Do supplier/peer stocks help?** Same model, trained with and without them:")
    st.dataframe(result["ablation"].round(3), hide_index=True)


# ---------------------------------------------------------------- 4. strategy
st.divider()
st.subheader("4. Illustrative historical strategy (test period)")
model_choices = [m for m in metrics["Model"] if m != "Baseline: predict 0"]
strategy_model = st.selectbox("Model driving the strategy", model_choices,
                              index=model_choices.index(best))
bt, summary = backtest(result["predictions"], strategy_model, threshold, costs)
st.caption(f"Hold the stock on a day only if yesterday's forecast was above {threshold:.2f}%; "
           f"otherwise hold cash. Every buy or sell costs {costs:.2f}%. Sliders update this instantly.")
st.dataframe(summary.round(2), hide_index=True)
st.line_chart(bt.set_index("Date")[["strategy_equity", "buy_hold_equity"]])
st.markdown("**Threshold sensitivity** (like Table 2 in the Stanford paper)")
st.dataframe(threshold_table(result["predictions"], strategy_model,
                             transaction_cost_pct=costs).round(2), hide_index=True)


# ---------------------------------------------------------------- 5. robustness
st.divider()
st.subheader("5. Robustness checks")
st.caption("A single test period can be lucky. These re-run the models across several periods "
           "and horizons, closer to the paper's rolling procedure.")
col1, col2 = st.columns(2)
if col1.button("Run walk-forward evaluation (5 periods)"):
    with st.spinner("Running walk-forward…"):
        st.session_state["wf"] = walk_forward(data, features, horizon)
if col2.button("Compare horizons 1 / 5 / 20 days"):
    with st.spinner("Training at three horizons…"):
        st.session_state["hz"] = compare_horizons(frame, peers, (1, 5, 20), peer_lags, tune)
if st.session_state.get("wf") is not None:
    folds, wf_summary = st.session_state["wf"]
    st.markdown("**Walk-forward summary** (default settings, expanding training window)")
    st.dataframe(wf_summary.round(3), hide_index=True)
    with st.expander("Per-period results"):
        st.dataframe(folds.round(3), hide_index=True)
if st.session_state.get("hz") is not None:
    st.markdown("**Test RMSE (%) by horizon** (like Table 1 in the paper)")
    st.dataframe(st.session_state["hz"].round(3), hide_index=True)


# ---------------------------------------------------------------- 6. predictions
st.divider()
st.subheader("6. Test-set predictions")
view = result["predictions"].copy()
view["Actual forward return (%)"] = view.pop("target") * 100
for m in model_choices + ["Baseline: predict 0"]:
    view[m] = view[m] * 100
num = view.select_dtypes("number").columns
view[num] = view[num].round(3)
st.dataframe(view.tail(100), hide_index=True)
st.download_button("Download test predictions CSV", view.to_csv(index=False).encode("utf-8"),
                   "test_predictions.csv", "text/csv")
st.download_button("Download strategy results CSV", bt.to_csv(index=False).encode("utf-8"),
                   "strategy_results.csv", "text/csv")

st.divider()
st.caption("Research prototype only • No financial advice • Past performance does not guarantee future results")
