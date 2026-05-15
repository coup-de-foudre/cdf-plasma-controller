#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller. See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""GPIO button watcher.

Wraps pigpio edge callbacks and a threshold timer so consumers see only two
high-level events: short press and long press.

Wiring: a single SPST switch between the GPIO pin and ground, with the
internal pull-up enabled. Switch closed → falling edge → 0; switch open →
rising edge → 1.

Long-press semantics (per the design): the moment the threshold timer
expires *while the button is still held*, the long-press handler fires
immediately. The runner reacts (kill the tube), and the eventual rising edge
when the user finally releases the button is consumed and ignored. This
gives the user immediate audio/visual feedback that their hold registered.
"""
import logging
import threading
from typing import Callable

import pigpio


logger = logging.getLogger(__name__)


class ButtonWatcher:
    def __init__(self,
                 pi: 'pigpio.pi',
                 gpio_pin: int,
                 on_short_press: Callable[[], None],
                 on_long_press: Callable[[], None],
                 on_press: Callable[[], None] = lambda: None,
                 hold_threshold_s: float = 1.0):
        self._pi = pi
        self._pin = gpio_pin
        self._on_short = on_short_press
        self._on_long = on_long_press
        self._on_press = on_press
        self._hold_threshold_s = hold_threshold_s

        self._lock = threading.Lock()
        self._timer = None
        # Set when the long-press timer has already fired for the current
        # hold; the next rising edge is consumed silently.
        self._long_consumed = False

        self._falling_cb = None
        self._rising_cb = None

    def start(self) -> None:
        self._pi.set_mode(self._pin, pigpio.INPUT)
        self._pi.set_pull_up_down(self._pin, pigpio.PUD_UP)
        # 5 ms glitch filter — debounces mechanical bounce without affecting
        # the 1 s threshold detection.
        self._pi.set_glitch_filter(self._pin, 5000)
        self._falling_cb = self._pi.callback(
            self._pin, pigpio.FALLING_EDGE, self._on_edge)
        self._rising_cb = self._pi.callback(
            self._pin, pigpio.RISING_EDGE, self._on_edge)
        logger.info("ButtonWatcher armed on BCM %d (pull-up, active-low)",
                    self._pin)

    def stop(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if self._falling_cb is not None:
            self._falling_cb.cancel()
        if self._rising_cb is not None:
            self._rising_cb.cancel()

    def _on_edge(self, _gpio: int, level: int, _tick: int) -> None:
        # `level` semantics from pigpio: 0 = falling, 1 = rising,
        # 2 = watchdog timeout (we don't set one).
        if level == 0:
            self._handle_press()
        elif level == 1:
            self._handle_release()

    def _handle_press(self) -> None:
        with self._lock:
            self._long_consumed = False
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                self._hold_threshold_s, self._on_threshold_expired)
            self._timer.daemon = True
            self._timer.start()
        # Notify outside the lock — the handler may take its own lock or
        # send OSC, neither of which should serialize with our timer state.
        try:
            self._on_press()
        except Exception:
            logger.exception("on_press handler raised")

    def _handle_release(self) -> None:
        with self._lock:
            timer = self._timer
            self._timer = None
            consumed = self._long_consumed
            self._long_consumed = False
            if timer is not None:
                timer.cancel()
        if consumed:
            # Long-press already fired; this rising edge is the trailing
            # release and should be ignored.
            return
        try:
            self._on_short()
        except Exception:
            logger.exception("on_short_press handler raised")

    def _on_threshold_expired(self) -> None:
        with self._lock:
            # If the timer was canceled between the firing decision and our
            # acquiring the lock, this branch is a no-op.
            if self._timer is None:
                return
            self._timer = None
            self._long_consumed = True
        try:
            self._on_long()
        except Exception:
            logger.exception("on_long_press handler raised")
