import unittest

from monitor import MonitorError, parse_station_status


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
                {"id": "DESWDE000020102", "status": "Frei", "seit": "10:42", "typ": "Typ 2"},
            ],
        )

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

