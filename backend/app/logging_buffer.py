"""In-memory log ring buffer for the DevOps dashboard."""
from __future__ import annotations

import logging
from collections import deque

BUFFER: deque[dict[str, str]] = deque(maxlen=500)


class BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            BUFFER.append(
                {
                    "time": self.format(record).split(" ")[0],
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
            )
        except Exception:  # noqa: BLE001
            pass


def install() -> None:
    root = logging.getLogger()
    if not any(isinstance(h, BufferHandler) for h in root.handlers):
        handler = BufferHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.INFO)
