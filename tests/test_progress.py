import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from samsung_firmware import progress  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FormatTests(unittest.TestCase):
    def test_format_bytes_uses_binary_units(self):
        self.assertEqual(progress.format_bytes(512), "512.0 B")
        self.assertEqual(progress.format_bytes(1024), "1.0 KiB")
        self.assertEqual(progress.format_bytes(3 * 1024 * 1024), "3.0 MiB")

    def test_format_seconds_shows_hours_only_when_needed(self):
        self.assertEqual(progress.format_seconds(7), "0:07")
        self.assertEqual(progress.format_seconds(125), "2:05")
        self.assertEqual(progress.format_seconds(3725), "1:02:05")

    def test_format_status_with_known_total_shows_bar_percent_speed_and_eta(self):
        line = progress.format_status(512, 1024, elapsed=1.0, width=10)
        self.assertEqual(line, "[#####-----]  50% 512.0 B/1.0 KiB 512.0 B/s ETA 0:01")

    def test_format_status_without_total_shows_bytes_and_speed(self):
        self.assertEqual(progress.format_status(2048, None, elapsed=2.0), "2.0 KiB 1.0 KiB/s")

    def test_format_status_handles_zero_elapsed_time(self):
        line = progress.format_status(0, 100, elapsed=0.0, width=4)
        self.assertEqual(line, "[----]   0% 0.0 B/100.0 B 0.0 B/s")


class ProgressBarTests(unittest.TestCase):
    def test_updates_are_throttled_and_finish_draws_final_state(self):
        clock = FakeClock()
        stream = io.StringIO()
        bar = progress.ProgressBar(stream, total=100, clock=clock, interval=0.1)
        bar.update(10)
        clock.now = 0.05
        bar.update(20)
        self.assertEqual(stream.getvalue().count("\r"), 1)
        clock.now = 0.2
        bar.update(50)
        self.assertEqual(stream.getvalue().count("\r"), 2)
        bar.update(100)
        bar.finish()
        self.assertEqual(stream.getvalue().count("\r"), 3)
        self.assertIn("100%", stream.getvalue().split("\r")[-1])
        self.assertTrue(stream.getvalue().endswith("\n"))

    def test_finish_is_idempotent(self):
        stream = io.StringIO()
        bar = progress.ProgressBar(stream, total=10, clock=FakeClock())
        bar.update(10)
        bar.finish()
        bar.finish()
        self.assertEqual(stream.getvalue().count("\n"), 1)


if __name__ == "__main__":
    unittest.main()
