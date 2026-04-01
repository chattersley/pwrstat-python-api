import subprocess
import unittest
from unittest.mock import MagicMock, patch

from pwrstat_api.parser import PwrstatError, _parse_output, get_pwrstat_status

# Realistic pwrstat -status output used across multiple tests
SAMPLE_OUTPUT = """\
The UPS information shows as following:

\tProperties:
\t\tModel Name................... CP1500PFCLCD
\t\tFirmware Number.............. BFZE108.F5 .I
\t\tRating Voltage............... 120 V
\t\tRating Power................. 1000 Watt(900 VA)

\tCurrent UPS status:
\t\tState........................ Normal
\t\tPower Supply by.............. Utility Power
\t\tUtility Voltage.............. 120 V
\t\tOutput Voltage............... 120 V
\t\tBattery Capacity............. 100 %
\t\tRemaining Runtime............ 60 min.
\t\tLoad......................... 180 Watt(18 %)
\t\tLine Interaction............. None
\t\tTest Result.................. Unknown
\t\tLast Power Event............. None
"""


class TestParseOutput(unittest.TestCase):
    def test_parses_simple_value(self):
        result = _parse_output("Model Name................... CP1500PFCLCD\n")
        self.assertEqual(result["Model Name"], "CP1500PFCLCD")

    def test_preserves_dots_in_value(self):
        """Firmware numbers contain dots that must not be stripped."""
        result = _parse_output("Firmware Number.............. BFZE108.F5 .I\n")
        self.assertEqual(result["Firmware Number"], "BFZE108.F5 .I")

    def test_preserves_trailing_unit(self):
        result = _parse_output("Battery Capacity............. 100 %\n")
        self.assertEqual(result["Battery Capacity"], "100 %")

    def test_full_sample_output_key_count(self):
        result = _parse_output(SAMPLE_OUTPUT)
        self.assertEqual(len(result), 14)

    def test_full_sample_output_values(self):
        result = _parse_output(SAMPLE_OUTPUT)
        self.assertEqual(result["Model Name"], "CP1500PFCLCD")
        self.assertEqual(result["State"], "Normal")
        self.assertEqual(result["Battery Capacity"], "100 %")
        self.assertEqual(result["Remaining Runtime"], "60 min.")
        self.assertEqual(result["Load"], "180 Watt(18 %)")

    def test_ignores_header_lines(self):
        """Lines without the dot-separator pattern are silently skipped."""
        result = _parse_output("The UPS information shows as following:\n\nProperties:\n")
        self.assertEqual(result, {})

    def test_empty_input(self):
        self.assertEqual(_parse_output(""), {})

    def test_whitespace_only_input(self):
        self.assertEqual(_parse_output("   \n\t\n  "), {})

    def test_strips_leading_and_trailing_whitespace_from_keys(self):
        result = _parse_output("\t\t  Model Name................... CP1500PFCLCD\n")
        self.assertIn("Model Name", result)

    def test_single_dot_separator_not_matched(self):
        """A single dot is not a valid separator — line should be ignored."""
        result = _parse_output("Key. Value\n")
        self.assertEqual(result, {})

    def test_does_not_overwrite_duplicate_keys(self):
        """Last occurrence wins when the same key appears twice."""
        output = "State........................ Normal\nState........................ On Battery\n"
        result = _parse_output(output)
        self.assertEqual(result["State"], "On Battery")


class TestGetPwrstatStatus(unittest.TestCase):
    @patch("pwrstat_api.parser.Path")
    def test_raises_file_not_found_when_binary_missing(self, mock_path):
        mock_path.return_value.is_file.return_value = False
        with self.assertRaises(FileNotFoundError):
            get_pwrstat_status()

    @patch("pwrstat_api.parser.subprocess.run")
    @patch("pwrstat_api.parser.Path")
    def test_returns_parsed_dict_on_success(self, mock_path, mock_run):
        mock_path.return_value.is_file.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout=SAMPLE_OUTPUT)

        result = get_pwrstat_status()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["Model Name"], "CP1500PFCLCD")
        self.assertEqual(result["State"], "Normal")

    @patch("pwrstat_api.parser.subprocess.run")
    @patch("pwrstat_api.parser.Path")
    def test_raises_pwrstat_error_on_nonzero_exit(self, mock_path, mock_run):
        mock_path.return_value.is_file.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        with self.assertRaises(PwrstatError):
            get_pwrstat_status()

    @patch("pwrstat_api.parser.subprocess.run")
    @patch("pwrstat_api.parser.Path")
    def test_propagates_timeout(self, mock_path, mock_run):
        mock_path.return_value.is_file.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pwrstat", timeout=10)

        with self.assertRaises(subprocess.TimeoutExpired):
            get_pwrstat_status()

    @patch("pwrstat_api.parser.subprocess.run")
    @patch("pwrstat_api.parser.Path")
    def test_invokes_correct_command(self, mock_path, mock_run):
        mock_path.return_value.is_file.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout=SAMPLE_OUTPUT)

        get_pwrstat_status()

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["/usr/sbin/pwrstat", "-status"])
        self.assertFalse(kwargs.get("shell", False))

    @patch("pwrstat_api.parser.subprocess.run")
    @patch("pwrstat_api.parser.Path")
    def test_uses_timeout(self, mock_path, mock_run):
        mock_path.return_value.is_file.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout=SAMPLE_OUTPUT)

        get_pwrstat_status()

        _, kwargs = mock_run.call_args
        self.assertIn("timeout", kwargs)
        self.assertGreater(kwargs["timeout"], 0)


if __name__ == "__main__":
    unittest.main()
