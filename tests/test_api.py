import subprocess
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from pwrstat_api.main import app
from pwrstat_api.parser import PwrstatError

SAMPLE_STATUS = {
    "Model Name": "CP1500PFCLCD",
    "Firmware Number": "BFZE108.F5 .I",
    "State": "Normal",
    "Battery Capacity": "100 %",
    "Remaining Runtime": "60 min.",
    "Load": "180 Watt(18 %)",
}


class TestPwrstatEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("pwrstat_api.main.get_pwrstat_status", return_value=SAMPLE_STATUS)
    def test_returns_200_with_status_dict(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), SAMPLE_STATUS)

    @patch("pwrstat_api.main.get_pwrstat_status", return_value=SAMPLE_STATUS)
    def test_response_content_type_is_json(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertIn("application/json", response.headers["content-type"])

    @patch("pwrstat_api.main.get_pwrstat_status", side_effect=FileNotFoundError)
    def test_returns_503_when_binary_missing(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertEqual(response.status_code, 503)

    @patch(
        "pwrstat_api.main.get_pwrstat_status",
        side_effect=subprocess.TimeoutExpired(cmd="pwrstat", timeout=10),
    )
    def test_returns_503_on_timeout(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertEqual(response.status_code, 503)

    @patch(
        "pwrstat_api.main.get_pwrstat_status",
        side_effect=PwrstatError("exit code 1"),
    )
    def test_returns_503_on_pwrstat_error(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertEqual(response.status_code, 503)

    @patch(
        "pwrstat_api.main.get_pwrstat_status",
        side_effect=RuntimeError("unexpected"),
    )
    def test_returns_500_on_unexpected_error(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertEqual(response.status_code, 500)

    @patch("pwrstat_api.main.get_pwrstat_status", return_value={})
    def test_returns_503_when_status_is_empty(self, _mock):
        response = self.client.get("/pwrstat")
        self.assertEqual(response.status_code, 503)

    @patch("pwrstat_api.main.get_pwrstat_status", side_effect=FileNotFoundError)
    def test_error_detail_does_not_leak_internals(self, _mock):
        """Error responses must not expose file paths or exception messages."""
        response = self.client.get("/pwrstat")
        body = response.text
        self.assertNotIn("/usr/sbin", body)
        self.assertNotIn("Traceback", body)

    @patch("pwrstat_api.main.get_pwrstat_status", return_value=SAMPLE_STATUS)
    def test_post_not_allowed(self, _mock):
        response = self.client.post("/pwrstat")
        self.assertEqual(response.status_code, 405)

    def test_unknown_route_returns_404(self):
        response = self.client.get("/unknown")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
