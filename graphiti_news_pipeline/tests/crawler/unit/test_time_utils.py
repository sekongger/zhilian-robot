import time
import unittest
from datetime import datetime, timezone

from crawler.utils.time_utils import parse_datetime_to_utc


class TimeUtilsTests(unittest.TestCase):
    def test_parse_rfc2822_with_timezone(self) -> None:
        value = "Mon, 15 Apr 2024 10:30:00 +0800"
        parsed = parse_datetime_to_utc(value)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.isoformat(), "2024-04-15T02:30:00+00:00")

    def test_parse_naive_datetime_defaults_to_cn_timezone(self) -> None:
        value = "2024-04-15 10:30:00"
        parsed = parse_datetime_to_utc(value)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.isoformat(), "2024-04-15T02:30:00+00:00")

    def test_parse_struct_time(self) -> None:
        st = time.struct_time((2024, 4, 15, 10, 30, 0, 0, 0, 0))
        parsed = parse_datetime_to_utc(st)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.isoformat(), "2024-04-15T10:30:00+00:00")

    def test_parse_datetime_instance(self) -> None:
        dt = datetime(2024, 4, 15, 10, 30, tzinfo=timezone.utc)
        parsed = parse_datetime_to_utc(dt)
        self.assertEqual(parsed.isoformat(), "2024-04-15T10:30:00+00:00")


if __name__ == "__main__":
    unittest.main()
