# World Bank project outcomes explorer

An executive dashboard of historical **IEG development outcome ratings** for evaluated World Bank projects. It compares the percentage rated *moderately satisfactory or above* across closing-year cohorts by World Bank region or global practice, and provides a deliberately simple three-year extrapolation. The [GitHub Pages dashboard](https://lugureign.github.io/world-bank-outcomes/) is generated from the same analysis as the Streamlit app. This is a portfolio learning exercise, not an official World Bank dashboard.

## Source and measure

- [Independent Evaluation Group (IEG) World Bank Project Performance Ratings](https://financesone.worldbank.org/ieg-world-bank-project-performance-ratings/DS00053), resource `RS00055`. [API explorer](https://financesone.worldbank.org/api-explorer?id=DS00053).
- One source row describes a project assessment; the published dataset retains the latest evaluation for a project. We additionally deduplicate by project ID and keep the latest evaluation fiscal year in case the export changes.
- The **MS+ share** is `count(outcome ∈ {Moderately Satisfactory, Satisfactory, Highly Satisfactory}) / count(projects with a recognized outcome rating)`. Each project counts once. The [IEG six-point rating scale](https://ieg.worldbankgroup.org/evaluations/results-and-performance-world-bank-group-2024/chapter-2-world-bank) is an assessment of development outcome, **not** a project results-framework indicator, beneficiary count, or causal estimate of impact.
- The grouping variable `wb_region` is the source's current World Bank administrative region; `global_practice` is used as the sector-like breakdown. These are **not** historical sector/region classifications. The year is `final_closing_fy`, not the evaluation year.
- Attribution: World Bank Group, IEG World Bank Project Performance Ratings, CC BY 4.0; downloaded on the date the user refreshes the data. The source is updated, so results can change on refresh.

## Run, step by step

1. Create a Python 3.12 environment in this folder and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Download the official records (internet access to `datacatalogapi.worldbank.org` required):

   ```bash
   python fetch.py
   ```

   Alternatively, export the dataset from the official source as CSV and save it to `data/ieg_ratings.csv`, preserving the column names listed in `fetch.py`. Local CSV snapshots are ignored by default; the GitHub refresh workflow deliberately commits a verified snapshot. The app never substitutes example data for live observations. If the API schema changes, the importer fails before writing a partial snapshot.

3. Run the dashboard:

   ```bash
   streamlit run app.py
   ```

4. Run the small pipeline tests:

   ```bash
   python -m unittest discover -s tests -v
   ```

5. To put it on **your GitHub**, create an empty repository named `world-bank-outcomes`, then in this folder run:

   ```bash
   git init
   git add .
   git commit -m "Build World Bank outcomes dashboard"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/world-bank-outcomes.git
   git push -u origin main
   ```

   GitHub requires you to authenticate for the push. In the repository's **Actions** tab, run **Refresh official IEG snapshot** once. It fetches and commits the public source file and `docs/index.html`, then repeats monthly. Ensure repository Actions have permission to write contents. Enable GitHub Pages from the `main` branch `/docs` folder in **Settings → Pages**. The Streamlit version can also run locally from `app.py`.

## Analysis design

`fetch.py` downloads API pages of 1,000, verifies the source columns, and atomically saves a snapshot. `analysis.py` validates ratings, removes duplicates, drops missing/unrecognized ratings and invalid years, then excludes closing years newer than three years before the source snapshot's calendar year to reduce the evaluation lag. Using the snapshot avoids treating future-dated source rows as the maturity anchor. Annual rates are shown only when at least ten projects have valid ratings.

For a selected region or global practice with at least eight eligible annual cohorts, two models compete: the mean of the last three eligible annual rates and a five-cohort linear trend (clipped to [0, 1]). Expanding-window, one-year-ahead backtests use only consecutive fiscal years, require at least three comparisons, and select the model with lower mean absolute error (MAE). The selected model forecasts the next three closing-year cohorts. The shaded ±MAE band is an **illustrative scenario**, not a confidence or prediction interval. The method treats cohort rates equally, while the charts also show denominators for interpretation.

## Assumptions and limits

- Evaluated projects are selected and evaluated with delays. Even a three-year lag may leave incomplete cohorts, and revisions to older ratings can change trends.
- Projects have equal weight, regardless of financing, reach, or complexity. Ratings are ordinal; binarizing them loses detail. Unrated and unrecognized values are excluded; cohort counts must be read alongside percentages.
- Region and practice definitions may change. Within-group project mix can change. Comparisons are descriptive and cannot identify why ratings differ.
- The next three future closing-year cohorts cannot be assumed to resemble past evaluated cohorts. Projection errors are evaluated only on available historical cohorts; the small historical MAE is not a guarantee of future accuracy.
- This dataset does not contain the underlying project outcome-indicator actuals, baselines, and targets. Adding those would require a separate and carefully validated document extraction pipeline.
