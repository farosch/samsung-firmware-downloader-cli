from __future__ import annotations

import time
from typing import Callable, TextIO

UNITS = ("B", "KiB", "MiB", "GiB")


def format_bytes(count: float) -> str:
    for unit in UNITS[:-1]:
        if abs(count) < 1024:
            return f"{count:.1f} {unit}"
        count /= 1024
    return f"{count:.1f} {UNITS[-1]}"


def format_seconds(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_status(received: int, total: int | None, elapsed: float, width: int = 30) -> str:
    speed = received / elapsed if elapsed > 0 else 0.0
    speed_text = f"{format_bytes(speed)}/s"
    if not total:
        return f"{format_bytes(received)} {speed_text}"
    fraction = min(received / total, 1.0)
    filled = int(width * fraction)
    bar = "#" * filled + "-" * (width - filled)
    eta = f" ETA {format_seconds((total - received) / speed)}" if speed > 0 else ""
    return (
        f"[{bar}] {fraction * 100:3.0f}% "
        f"{format_bytes(received)}/{format_bytes(total)} {speed_text}{eta}"
    )


class ProgressBar:
    """Single status line redrawn in place; redraws are throttled to `interval` seconds."""

    def __init__(self, stream: TextIO, total: int | None,
                 clock: Callable[[], float] = time.monotonic, interval: float = 0.1):
        self._stream = stream
        self._total = total
        self._clock = clock
        self._interval = interval
        self._start = clock()
        self._last_draw: float | None = None
        self._received = 0
        self._finished = False

    def update(self, received: int) -> None:
        self._received = received
        now = self._clock()
        if self._last_draw is not None and now - self._last_draw < self._interval:
            return
        self._draw(now)

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._draw(self._clock())
        self._stream.write("\n")
        self._stream.flush()

    def _draw(self, now: float) -> None:
        self._last_draw = now
        line = format_status(self._received, self._total, now - self._start)
        self._stream.write("\r\x1b[2K" + line)
        self._stream.flush()
