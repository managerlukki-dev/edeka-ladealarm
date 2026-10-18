import os
import unittest
from unittest.mock import MagicMock, patch

from monitor import MonitorError, parse_station_status, push_to_worker


class PushToWorkerTests(unittest.TestCase):
    @patch("monitor.urlopen")
    def test_worker_request_uses_named_user_agent(self, urlopen_mock):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        urlopen_mock.return_value = response

        with patch.dict(
            os.environ,
            {
                "WORKER_URL": "https://worker.example.workers.dev",
                "PUSH_SECRET": "test-secret",
            },
        ):
            push_to_worker([])

        request = urlopen_mock.call_args.args[0]
        self.assertEqual(
            request.get_header("User-agent"),
            "Edeka-Ladealarm/1.0",
        )
        self.assertEqual(request.get_method(), "POST")


class ParseStationStatusTests(unittest.TestCase):
    def test_extracts_both_exact_charger_statuses(self):
        markup = """
        <ul>
          <li onclick="togglePlugInfo('111');"><p>seit: 10:42</p></li>
          <li id="111"><p>ID: DESWDE000020101</p><p>Stecker: Typ 2</p><p>Status: Belegt</p></li>
          <li onclick="togglePlugInfo('222');"><p>seit: Mo 19:45</p></li>
          <li id="222"><p>ID: DESWDE000020102</p><p>Stecker: Typ 2</p><p>Status: Frei</p></li>
        </ul>
        """

        self.assertEqual(
            parse_station_status(markup),
            [
                {"id": "DESWDE000020101", "status": "Belegt", "seit": "10:42", "typ": "Typ 2"},
                {"id": "DESWDE000020102", "status": "Frei", "seit": "19:45", "typ": "Typ 2"},
            ],
        )

    def test_does_not_guess_when_timestamp_dom_link_is_missing_or_ambiguous(self):
        markup = """
        <ul>
          <li onclick="togglePlugInfo('111');"><p>seit: 19:45</p></li>
          <li onclick="togglePlugInfo('111');"><p>seit: 19:46</p></li>
          <li id="111"><p>ID: DESWDE000020101</p><p>Status: Frei</p></li>
          <li id="222"><p>ID: DESWDE000020102</p><p>Status: Belegt</p></li>
        </ul>
        """

        statuses = parse_station_status(markup)

        self.assertEqual([item["status"] for item in statuses], ["Frei", "Belegt"])
        self.assertEqual([item["seit"] for item in statuses], ["", ""])

    def test_accepts_out_of_service_as_a_known_nonavailability_state(self):
        markup = """
        <ul><li id="111"><p>ID: DESWDE000020101</p><p>Status: Außer Betrieb</p></li>
        <li id="222"><p>ID: DESWDE000020102</p><p>Status: Frei</p></li></ul>
        """

        self.assertEqual(parse_station_status(markup)[0]["status"], "Außer Betrieb")

    def test_rejects_missing_charger(self):
        with self.assertRaises(MonitorError):
            parse_station_status('<ul><li id="111"><p>ID: DESWDE000020101</p><p>Status: Frei</p></li></ul>')

    def test_rejects_unknown_instead_of_turning_it_into_free_or_occupied(self):
        markup = """
        <ul><li id="111"><p>ID: DESWDE000020101</p><p>Status: Unbekannt</p></li>
        <li id="222"><p>ID: DESWDE000020102</p><p>Status: Frei</p></li></ul>
        """

        with self.assertRaises(MonitorError):
            parse_station_status(markup)

    def test_rejects_missing_status(self):
        markup = """
        <ul><li id="111"><p>ID: DESWDE000020101</p><p>Stecker: Typ 2</p></li>
        <li id="222"><p>ID: DESWDE000020102</p><p>Status: Frei</p></li></ul>
        """

        with self.assertRaises(MonitorError):
            parse_station_status(markup)


if __name__ == "__main__":
    unittest.main()
