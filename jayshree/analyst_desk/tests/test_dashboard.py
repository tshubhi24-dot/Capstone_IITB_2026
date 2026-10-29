import importlib
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from analystdesk.note import MetricRow, ResearchNote


with patch("threading.Thread.start"), redirect_stdout(io.StringIO()):
    app = importlib.import_module("app")


def _dashboard_note():
    return ResearchNote(
        title="Dashboard data",
        status="draft",
        rows=[
            MetricRow(
                company="Microsoft",
                fiscal_year=2022,
                period_end="2022-06-30",
                revenue_usd_m=100.0,
                operating_income_usd_m=40.0,
                operating_margin_pct=40.0,
                revenue_fact_id="revenue-msft",
                operating_income_fact_id="income-msft",
            ),
            MetricRow(
                company="JPMorgan Chase",
                fiscal_year=2022,
                period_end="2022-12-31",
                revenue_usd_m=200.0,
                operating_income_usd_m=None,
                operating_margin_pct=None,
                revenue_fact_id="revenue-jpm",
                operating_income_fact_id=None,
                margin_basis="pretax",
                pretax_income_usd_m=50.0,
                pretax_margin_pct=25.0,
                pretax_income_fact_id="income-jpm",
            ),
        ],
    )


class DashboardTests(unittest.TestCase):
    def test_dashboard_uses_selected_companies_and_headline_metrics(self):
        selected = ["Microsoft", "JPMorgan Chase"]
        with (
            patch.object(app, "_get_baseline_data", return_value=_dashboard_note()) as load_data,
            patch.object(app, "_passage_stats", return_value=(2, 20)),
        ):
            revenue, margin, income, rows, summary = app.load_dashboard(selected)

        load_data.assert_called_once_with(selected)
        self.assertEqual([trace.name for trace in revenue.data], selected)
        self.assertEqual(
            [trace.name for trace in margin.data],
            ["Microsoft (Operating)", "JPMorgan Chase (Pre-tax)"],
        )
        self.assertEqual(list(margin.data[1].y), [25.0])
        self.assertEqual(
            [trace.name for trace in income.data],
            ["Microsoft (Operating income)", "JPMorgan Chase (Pre-tax income)"],
        )
        self.assertEqual(rows[1][4:7], ["$50.0M", "25.0%", "✅"])
        self.assertIn("Selected companies | Microsoft, JPMorgan Chase", summary)
        self.assertNotIn("C0 baseline pair", summary)

    def test_dashboard_rejects_empty_selection(self):
        with self.assertRaises(app.gr.Error):
            app.load_dashboard([])

    def test_dashboard_dropdown_contains_supported_companies_and_defaults(self):
        config = app.demo.get_config_file()
        dropdown = next(
            component for component in config["components"]
            if component.get("props", {}).get("label") == "Companies"
        )

        self.assertTrue(dropdown["props"]["multiselect"])
        self.assertEqual(
            dropdown["props"]["value"],
            ["Microsoft", "Alphabet"],
        )
        self.assertEqual(
            [choice[0] if isinstance(choice, tuple) else choice
             for choice in dropdown["props"]["choices"]],
            [company.name for company in app.COMPANIES],
        )
        refresh_events = [
            event for event in config["dependencies"]
            if event.get("api_name", "").startswith("refresh_dashboard")
        ]
        self.assertEqual(len(refresh_events), 2)
        self.assertTrue(all(dropdown["id"] in event["inputs"] for event in refresh_events))


if __name__ == "__main__":
    unittest.main()
