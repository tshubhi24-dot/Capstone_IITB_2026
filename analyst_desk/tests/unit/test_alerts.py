import io
import json
import os
import unittest
from unittest.mock import patch

from analystdesk.monitoring.alerts import PrometheusUnavailable
from analystdesk.monitoring.alerts import alert_panel_data
from analystdesk.monitoring.alerts import fetch_active_alerts


class AlertsTests(unittest.TestCase):
    def test_fetch_active_alerts_maps_prometheus_response(self):
        payload = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "state": "firing",
                        "labels": {
                            "alertname": "VerifiedShareBelow98",
                            "severity": "warning",
                        },
                        "annotations": {"summary": "Verified share below threshold"},
                        "activeAt": "2026-11-05T10:00:00Z",
                    }
                ]
            },
        }
        with patch(
            'analystdesk.monitoring.alerts.urlopen',
            return_value=io.BytesIO(json.dumps(payload).encode()),
        ):
            self.assertEqual(
                fetch_active_alerts(),
                [
                    {
                        "state": "firing",
                        "name": "VerifiedShareBelow98",
                        "severity": "warning",
                        "summary": "Verified share below threshold",
                        "active_at": "2026-11-05T10:00:00Z",
                    }
                ],
            )

    def test_no_active_alerts_are_returned_as_empty_list(self):
        with patch(
            'analystdesk.monitoring.alerts.urlopen',
            return_value=io.BytesIO(
                json.dumps({"status": "success", "data": {"alerts": None}}).encode()
            ),
        ):
            self.assertEqual(fetch_active_alerts(), [])

    def test_invalid_prometheus_response_is_reported(self):
        with patch(
            'analystdesk.monitoring.alerts.urlopen',
            return_value=io.BytesIO(json.dumps({"status": "error"}).encode()),
        ):
            with self.assertRaises(PrometheusUnavailable):
                fetch_active_alerts()

    def test_invalid_prometheus_url_is_reported(self):
        with patch.dict(os.environ, {"PROMETHEUS_URL": "prometheus:9090"}):
            with self.assertRaises(PrometheusUnavailable):
                fetch_active_alerts()

    def test_panel_distinguishes_no_alerts_from_unavailable_monitoring(self):
        def unavailable():
            raise PrometheusUnavailable("offline")

        self.assertEqual(
            alert_panel_data(lambda: []),
            ("✅ Monitoring is connected; there are no active alerts.", []),
        )
        self.assertEqual(
            alert_panel_data(unavailable),
            ("⚠️ Monitoring is unavailable; Prometheus could not be reached.", []),
        )


if __name__ == "__main__":
    unittest.main()
