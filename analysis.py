"""Transparent cohort summaries and small-sample trend projections."""
import numpy as np
import pandas as pd

POSITIVE = {"highly satisfactory", "satisfactory", "moderately satisfactory", "hs", "s", "ms"}
NEGATIVE = {"moderately unsatisfactory", "unsatisfactory", "highly unsatisfactory", "mu", "u", "hu"}
REQUIRED = {"project_id", "final_closing_fy", "evaluation_fy", "outcome", "wb_region", "global_practice"}
MIN_PROJECTS = 10
MATURITY_LAG = 3


def prepare(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required source columns: {sorted(missing)}")
    data = raw.copy()
    n_source = len(data)
    data["project_id"] = data["project_id"].astype("string").str.strip()
    for col in ("final_closing_fy", "evaluation_fy"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["rating"] = data["outcome"].astype("string").str.strip().str.lower()
    data["success"] = data["rating"].map(lambda value: 1 if value in POSITIVE else (0 if value in NEGATIVE else np.nan))
    data = data.loc[data["project_id"].notna() & data["project_id"].ne("")]
    data = data.sort_values(["project_id", "evaluation_fy"], kind="stable").drop_duplicates("project_id", keep="last")
    n_unique = len(data)
    data = data.loc[data["success"].notna() & data["final_closing_fy"].between(1995, 2100)].copy()
    if data.empty:
        raise ValueError("No rated projects with valid closing years")
    max_closing = int(data["final_closing_fy"].max())
    cutoff = max_closing - MATURITY_LAG
    data = data.loc[data["final_closing_fy"] <= cutoff].copy()
    data["final_closing_fy"] = data["final_closing_fy"].astype(int)
    for col in ("wb_region", "global_practice"):
        data[col] = data[col].fillna("Unspecified").replace("", "Unspecified")
    return data, {"source_rows": n_source, "unique_projects": n_unique,
                  "included_projects": len(data), "latest_closing_fy": max_closing,
                  "cohort_cutoff": cutoff}


def aggregate(data: pd.DataFrame, group: str) -> pd.DataFrame:
    if group not in ("wb_region", "global_practice"):
        raise ValueError("Group must be wb_region or global_practice")
    result = data.groupby([group, "final_closing_fy"], as_index=False).agg(
        projects=("success", "size"), satisfactory=("success", "sum"))
    result["rate"] = result["satisfactory"] / result["projects"]
    return result


def _predict(history: pd.DataFrame, future_years: np.ndarray, method: str) -> np.ndarray:
    rates = history["rate"].to_numpy(dtype=float)
    years = history["final_closing_fy"].to_numpy(dtype=float)
    if method == "recent 3-year mean":
        predicted = np.full(len(future_years), rates[-3:].mean())
    elif method == "linear trend":
        # Rolling five years guards against fitting decades of changing practice.
        slope, intercept = np.polyfit(years[-5:], rates[-5:], 1)
        predicted = slope * future_years + intercept
    else:
        raise ValueError(method)
    return np.clip(predicted, 0, 1)


def forecast(cohorts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Choose by expanding one-year backtests, then project three cohorts."""
    history = cohorts.loc[cohorts["projects"] >= MIN_PROJECTS].sort_values("final_closing_fy").copy()
    if len(history) < 8:
        return pd.DataFrame(), pd.DataFrame()
    methods = ("recent 3-year mean", "linear trend")
    errors = {method: [] for method in methods}
    for index in range(5, len(history)):
        train = history.iloc[:index]
        target = history.iloc[index]
        # Only evaluate genuinely next-year cohorts; avoid backtest over gaps.
        if int(target["final_closing_fy"]) != int(train.iloc[-1]["final_closing_fy"]) + 1:
            continue
        for method in methods:
            estimate = _predict(train, np.array([target["final_closing_fy"]]), method)[0]
            errors[method].append(abs(estimate - target["rate"]))
    if min(map(len, errors.values())) < 3:
        return pd.DataFrame(), pd.DataFrame()
    mae = {method: float(np.mean(err)) for method, err in errors.items()}
    method = min(methods, key=lambda name: mae[name])
    last = int(history["final_closing_fy"].max())
    future_years = np.arange(last + 1, last + 4)
    predictions = _predict(history, future_years, method)
    output = pd.DataFrame({"final_closing_fy": future_years, "projected_rate": predictions,
                           "lower_scenario": np.clip(predictions - mae[method], 0, 1),
                           "upper_scenario": np.clip(predictions + mae[method], 0, 1),
                           "method": method, "backtest_mae": mae[method],
                           "backtest_years": len(errors[method])})
    scores = pd.DataFrame([{"method": name, "mae": mae[name], "backtest_years": len(errors[name])}
                           for name in methods])
    return output, scores
