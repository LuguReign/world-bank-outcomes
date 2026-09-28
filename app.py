"""Executive dashboard for evaluated World Bank project cohorts."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from analysis import aggregate, forecast, prepare, MIN_PROJECTS

st.set_page_config(page_title="World Bank project outcomes", page_icon="📊", layout="wide")
st.title("World Bank project outcomes")
st.caption("Independent Evaluation Group · percentage rated moderately satisfactory or above · by project closing fiscal year")
path = Path(__file__).parent / "data" / "ieg_ratings.csv"
if not path.exists():
    st.info("No source snapshot is installed. Run `python fetch.py` in the project folder, then refresh this page.")
    st.stop()

try:
    raw = pd.read_csv(path)
    data, quality = prepare(raw)
except (ValueError, OSError) as error:
    st.error(f"Source data could not be validated: {error}")
    st.stop()

st.sidebar.header("Explore")
dimension = st.sidebar.radio("Compare by", ["World Bank region", "Global practice"])
field = "wb_region" if dimension == "World Bank region" else "global_practice"
options = sorted(data[field].unique())
selected = st.sidebar.selectbox(dimension, options)
view = data[data[field] == selected]
annual = aggregate(view, field)
eligible = annual[annual["projects"] >= MIN_PROJECTS].copy()
if eligible.empty:
    st.warning("This group has no cohorts with at least ten evaluated projects.")
    st.stop()

latest = eligible.iloc[-1]
previous = eligible.iloc[-2] if len(eligible) >= 2 else None
col1, col2, col3 = st.columns(3)
col1.metric("Latest eligible cohort", f"FY{int(latest.final_closing_fy)}")
col2.metric("Rated MS or above", f"{latest.rate:.1%}",
            f"{(latest.rate - previous.rate) * 100:+.1f} pp vs previous eligible cohort" if previous is not None else None)
col3.metric("Evaluated projects in cohort", f"{int(latest.projects):,}")

projection, scores = forecast(annual)
figure = go.Figure()
figure.add_trace(go.Scatter(x=eligible.final_closing_fy, y=eligible.rate, mode="lines+markers",
                            name="Observed evaluated cohorts", customdata=eligible.projects,
                            hovertemplate="FY%{x}<br>Rate %{y:.1%}<br>Projects %{customdata}<extra></extra>"))
if not projection.empty:
    figure.add_trace(go.Scatter(x=projection.final_closing_fy, y=projection.projected_rate,
                                mode="lines+markers", line=dict(dash="dash"), name="Exploratory projection"))
    figure.add_trace(go.Scatter(x=list(projection.final_closing_fy) + list(projection.final_closing_fy[::-1]),
                                y=list(projection.upper_scenario) + list(projection.lower_scenario[::-1]),
                                fill="toself", fillcolor="rgba(43,111,180,0.12)", line=dict(color="rgba(0,0,0,0)"),
                                name="± historical backtest MAE"))
figure.update_layout(height=440, yaxis=dict(title="Share rated MS or above", tickformat=".0%", range=[0, 1]),
                     xaxis_title="Project final closing fiscal year", legend_title="Series")
st.plotly_chart(figure, use_container_width=True)

left, right = st.columns([2, 1])
with left:
    st.subheader("Regional / practice comparison")
    comparison = aggregate(data, field)
    comparison = comparison[comparison.final_closing_fy == int(latest.final_closing_fy)]
    comparison = comparison[comparison.projects >= MIN_PROJECTS].sort_values("rate", ascending=False)
    comparison["rate"] = comparison["rate"] * 100
    st.dataframe(comparison.rename(columns={field: dimension, "final_closing_fy": "Closing FY",
                                             "projects": "Projects", "satisfactory": "MS+ projects",
                                             "rate": "MS+ share"}), hide_index=True,
                 column_config={"MS+ share": st.column_config.NumberColumn(format="%.1f%%")})
with right:
    st.subheader("Forecast check")
    if projection.empty:
        st.write("Insufficient consecutive, eligible closing-year cohorts for a three-year projection.")
    else:
        st.write(f"Selected method: **{projection.method.iloc[0]}**")
        st.write(f"Expanding one-year backtests: **{int(projection.backtest_years.iloc[0])}**; mean absolute error: **{projection.backtest_mae.iloc[0]:.1%}**.")
        st.dataframe(scores, hide_index=True, column_config={"mae": st.column_config.NumberColumn(format="%.3f")})
        st.caption("Shading is a descriptive ±MAE scenario, not a calibrated confidence interval.")

with st.expander("Data quality, definitions, and limits", expanded=True):
    st.write(f"Source rows: {quality['source_rows']:,}; unique project IDs: {quality['unique_projects']:,}; "
             f"included rated projects: {quality['included_projects']:,}. Latest observed closing year: "
             f"FY{quality['latest_closing_fy']}; snapshot: {quality['snapshot_date']}; "
             f"cohorts after FY{quality['cohort_cutoff']} excluded "
             "to reduce evaluation-lag bias.")
    st.write("Each project receives one equal weight. The source keeps its latest evaluation. "
             "Rates are conditional on projects evaluated by the snapshot date; missing ratings are excluded. "
             "Region and global practice use the current classifications in the source. "
             "A cohort with fewer than ten projects is hidden. The chosen group may differ from the portfolio mix.")
    st.write("Projected future closing cohorts extrapolate past evaluated-cohort ratings; they are exploratory "
             "and do not predict an individual project's result or measure attributable development impact. "
             "Recent cohorts can still be incomplete after the three-year exclusion. "
             "No causal conclusions or claims about beneficiaries follow from this dashboard.")
    st.markdown("[Official IEG dataset](https://financesone.worldbank.org/ieg-world-bank-project-performance-ratings/DS00053) · "
                "[IEG rating definitions](https://ieg.worldbankgroup.org/evaluations/results-and-performance-world-bank-group-2024/chapter-2-world-bank)")
