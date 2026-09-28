import unittest
import pandas as pd
from analysis import prepare, aggregate, forecast


class PipelineTests(unittest.TestCase):
    def test_dedup_rating_and_maturity(self):
        raw = pd.DataFrame([
            {"project_id": "P1", "final_closing_fy": 2019, "evaluation_fy": 2020,
             "outcome": "Unsatisfactory", "wb_region": "A", "global_practice": "Health"},
            {"project_id": "P1", "final_closing_fy": 2019, "evaluation_fy": 2022,
             "outcome": "Moderately Satisfactory", "wb_region": "A", "global_practice": "Health"},
            {"project_id": "P2", "final_closing_fy": 2025, "evaluation_fy": 2026,
             "outcome": "Satisfactory", "wb_region": "A", "global_practice": "Health"},
            {"project_id": "P3", "final_closing_fy": 2022, "evaluation_fy": 2023,
             "outcome": "unknown", "wb_region": "A", "global_practice": "Health"},
        ])
        data, summary = prepare(raw)
        self.assertEqual(summary["unique_projects"], 3)
        self.assertEqual(summary["cohort_cutoff"], 2022)
        self.assertEqual(len(data), 1)
        self.assertEqual(data.iloc[0].success, 1)
        self.assertEqual(aggregate(data, "wb_region").iloc[0].rate, 1)

    def test_forecast_is_bounded_and_backtested(self):
        years = list(range(2011, 2023))
        cohorts = pd.DataFrame({"final_closing_fy": years, "projects": [20] * len(years),
                                "rate": [0.55 + .02 * i for i in range(len(years))]})
        projection, scores = forecast(cohorts)
        self.assertEqual(projection.final_closing_fy.tolist(), [2023, 2024, 2025])
        self.assertEqual(int(projection.backtest_years.iloc[0]), 7)
        self.assertTrue(projection.projected_rate.between(0, 1).all())
        self.assertEqual(len(scores), 2)

    def test_snapshot_date_anchors_maturity_despite_future_year(self):
        raw = pd.DataFrame([
            {"project_id": "P1", "final_closing_fy": 2023, "evaluation_fy": 2024,
             "outcome": "Satisfactory", "wb_region": "A", "global_practice": "Health", "as_of_date": "25-Sep-2026"},
            {"project_id": "P2", "final_closing_fy": 2027, "evaluation_fy": 2026,
             "outcome": "Satisfactory", "wb_region": "A", "global_practice": "Health", "as_of_date": "25-Sep-2026"},
        ])
        data, quality = prepare(raw)
        self.assertEqual(quality["cohort_cutoff"], 2023)
        self.assertEqual(data.project_id.tolist(), ["P1"])


if __name__ == "__main__":
    unittest.main()
