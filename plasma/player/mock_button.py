#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller. See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""Stdin-driven mock button for laptop testing.

Reads commands from stdin, one per line:

    <Enter>      → short press
    h <Enter>    → long press (the kill-the-show hold)
    q <Enter>    → quit the player

This is the lazy-but-portable input model: line-buffered so it works on Mac
without termios fiddling, and adequate for verifying the state machine
end-to-end before we touch real hardware.
"""
import logging
import sys
import threading
from typing import Callable


logger = logging.getLogger(__name__)


class MockButtonWatcher:
    def __init__(self,
                 on_short_press: Callable[[], None],
                 on_long_press: Callable[[], None],
                 on_quit: Callable[[], None]):
        self._on_short = on_short_press
        self._on_long = on_long_press
        self._on_quit = on_quit
        self._thread = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="MockButtonWatcher", daemon=True)
        self._thread.start()
        sys.stderr.write(
            "[mock-button] press <Enter> for short, 'h<Enter>' for hold, "
            "'q<Enter>' to quit\n")
        sys.stderr.flush()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        for line in sys.stdin:
            if self._stop.is_set():
                return
            cmd = line.strip().lower()
            if cmd == '':
                logger.info("[mock-button] short press")
                try:
                    self._on_short()
                except Exception:
                    logger.exception("on_short_press handler raised")
            elif cmd in ('h', 'hold'):
                logger.info("[mock-button] long press")
                try:
                    self._on_long()
                except Exception:
                    logger.exception("on_long_press handler raised")
            elif cmd in ('q', 'quit', 'exit'):
                logger.info("[mock-button] quit")
                self._on_quit()
                return
            else:
                sys.stderr.write(
                    "[mock-button] unknown command %r; "
                    "use <Enter>, h, or q\n" % cmd)
                sys.stderr.flush()
