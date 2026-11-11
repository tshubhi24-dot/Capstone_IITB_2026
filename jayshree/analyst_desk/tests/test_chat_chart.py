import unittest
from unittest.mock import patch

from analystdesk.chat_chart import build_chat_chart, _metric_from_question


def _financials(revenue, operating_income=None, pretax_income=None):
    def fact(value):
        return {"val": value} if value is not None else None

    return {
        "revenue": fact(revenue),
        "operating_income": fact(operating_income),
        "pretax_income": fact(pretax_income),
    }


class ChatChartTests(unittest.TestCase):
    @patch("analystdesk.chat_chart.get_financials")
    def test_company_comparison_builds_annual_revenue_chart_without_chart_keyword(self, get_financials):
        get_financials.side_effect = [
            _financials(35000000000),
            _financials(28000000000),
        ]

        figure, notice = build_chat_chart(
            "Visa vs Mastercard net revenue in 2024", [2024]
        )

        self.assertIsNone(notice)
        self.assertEqual(figure.layout.title.text, "Annual Revenue — EDGAR XBRL")
        self.assertEqual([trace.name for trace in figure.data], ["Visa", "Mastercard"])
        self.assertEqual(list(figure.data[0].x), ["FY2024"])
        self.assertEqual(list(figure.data[0].y), [35000.0])
        self.assertEqual(list(figure.data[1].y), [28000.0])
        self.assertEqual(get_financials.call_count, 2)

    @patch("analystdesk.chat_chart.get_quarterly_financials")
    def test_quarterly_chart_uses_companies_and_periods_from_question(self, get_quarters):
        get_quarters.side_effect = [
            [
                {"quarter": "Q1", "revenue": {"val": 1000000}, "operating_income": {"val": 200000}},
                {"quarter": "Q2", "revenue": {"val": 1200000}, "operating_income": {"val": 300000}},
            ],
            [
                {"quarter": "Q1", "revenue": {"val": 2000000}, "operating_income": {"val": 500000}},
                {"quarter": "Q2", "revenue": {"val": 2400000}, "operating_income": {"val": 600000}},
            ],
        ]

        figure, notice = build_chat_chart(
            "Compare Visa and Mastercard quarterly operating margin in 2024",
            [2024],
        )

        self.assertIsNone(notice)
        self.assertEqual(figure.layout.title.text, "Quarterly Operating Margin — EDGAR XBRL")
        self.assertEqual(list(figure.data[0].x), ["FY2024 Q1", "FY2024 Q2"])
        self.assertEqual(list(figure.data[0].y), [20.0, 25.0])
        self.assertEqual(list(figure.data[1].y), [25.0, 25.0])

    @patch("analystdesk.chat_chart.get_financials")
    def test_no_chart_for_non_metric_question(self, get_financials):
        self.assertEqual(
            build_chat_chart("What were Visa's main risk factors in 2024?", [2024]),
            (None, None),
        )
        get_financials.assert_not_called()

    def test_specific_margin_is_not_confused_with_generic_margin(self):
        self.assertEqual(_metric_from_question("Visa operating margin in 2024"), "operating_margin")
        self.assertIsNone(
            _metric_from_question("Compare Visa revenue and operating margin in 2024")
        )

    @patch("analystdesk.chat_chart.get_financials")
    def test_missing_edgar_values_return_clear_notice(self, get_financials):
        get_financials.return_value = _financials(None)

        figure, notice = build_chat_chart(
            "Visa vs Mastercard net revenue in 2024", [2024]
        )

        self.assertIsNone(figure)
        self.assertIn("No EDGAR data", notice)


if __name__ == "__main__":
    unittest.main()
