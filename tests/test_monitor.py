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
        <div>ID: DESWDE000020101 Stecker: Typ 2 Status: Belegt</div>
        <div>ID: DESWDE000020102 Stecker: Typ 2 Status: Frei seit: Mo 10:42</div>
        """

        self.assertEqual(
            parse_station_status(markup),
            [
                {"id": "DESWDE000020101", "status": "Belegt", "seit": "", "typ": "Typ 2"},
                {"id": "DESWDE000020102", "status": "Frei", "seit": "", "typ": "Typ 2"},
            ],
        )


    def test_omits_times_that_cannot_be_tied_to_the_correct_charger(self):
        markup = """
        <div>ID: DESWDE000020101 Stecker: Typ 2 Status: Frei seit: 19:45</div>
        <div>ID: DESWDE000020102 Stecker: Typ 2 Status: Belegt seit: 12:22</div>
        """

        statuses = parse_station_status(markup)

        self.assertEqual([item["status"] for item in statuses], ["Frei", "Belegt"])
        self.assertEqual([item["seit"] for item in statuses], ["", ""])

    def test_accepts_out_of_service_as_a_known_nonavailability_state(self):
        markup = """
        <div>ID: DESWDE000020101 Stecker: Typ 2 Status: Außer Betrieb</div>
        <div>ID: DESWDE000020102 Stecker: Typ 2 Status: Frei</div>
        """

        self.assertEqual(parse_station_status(markup)[0]["status"], "Außer Betrieb")

    def test_rejects_missing_charger(self):
        with self.assertRaises(MonitorError):
            parse_station_status("ID: DESWDE000020101 Stecker: Typ 2 Status: Frei")

    def test_rejects_unknown_instead_of_turning_it_into_free_or_occupied(self):
        markup = """
        <div>ID: DESWDE000020101 Stecker: Typ 2 Status: Unbekannt</div>
        <div>ID: DESWDE000020102 Stecker: Typ 2 Status: Frei</div>
        """

        with self.assertRaises(MonitorError):
            parse_station_status(markup)

    def test_rejects_missing_status(self):
        markup = """
        <div>ID: DESWDE000020101 Stecker: Typ 2</div>
        <div>ID: DESWDE000020102 Stecker: Typ 2 Status: Frei</div>
        """

        with self.assertRaises(MonitorError):
            parse_station_status(markup)


if __name__ == "__main__":
    unittest.main()

