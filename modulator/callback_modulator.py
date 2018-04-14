#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
#
# This file is part of the CdF Plasma Controller.
#
# The CdF Plasma Controller is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# CdF Plasma Controller is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with the Cdf Plasma Controller.  If not, see
# <http://www.gnu.org/licenses/>.

import threading
import time
from concurrent.futures import ThreadPoolExecutor
import math
from numbers import Real
from typing import Callable

from modulator.base_modulator import BaseModulator


_2PI = 2 * math.pi


class CallbackModulator(BaseModulator):

    def __init__(self,
                 callback: Callable[[Real], None],
                 frequency: Real,
                 intensity: Real,
                 center: Real,
                 update_frequency: Real = 60.0,
                 waveform: Callable[[Real], Real]=math.sin,
                 ):

        super().__init__()
        self._callback = callback
        self._frequency = frequency
        self._intensity = intensity
        self._center = center
        self._update_frequency = update_frequency
        self._waveform = waveform

        self._phase_offset = 0.0
        self._previous_frequency = frequency

        self._is_stopped = True
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._run_future = None
        self._stop_signal = False

        self._time_error = 0.0
        self._run_lock = threading.Lock()

    def __del__(self):
        self.stop()

    @property
    def frequency(self) -> Real:
        return self._frequency

    @frequency.setter
    def frequency(self, value: Real) -> None:
        self._frequency = value

    @property
    def intensity(self) -> Real:
        return self._intensity

    @intensity.setter
    def intensity(self, value: Real):
        self._intensity = value

    @property
    def center(self) -> Real:
        return self._center

    @center.setter
    def center(self, value: Real) -> None:
        self._center = value

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    def start(self) -> None:
        if self.is_stopped:
            self._stop_signal = False
            self._run_future = self._executor.submit(self._run)

    def stop(self) -> None:
        if not self.is_stopped:
            self._stop_signal = True
            self._wait_for_run_to_finish()

    def _wait_for_run_to_finish(self):
        self._run_future.result()

    def _run(self) -> None:
        with self._run_lock:
            self._is_stopped = False
            self._is_stopped = True
            self._run_timing_loop()

    def _run_timing_loop(self) -> None:
        while not self._stop_signal:
            callback_start_time = time.time()
            self._do_callback(callback_start_time)
            callback_seconds = time.time() - callback_start_time
            wait_seconds = max(
                0.0, 1.0 / self._update_frequency - callback_seconds)
            self._spin_wait(wait_seconds)

    def _do_callback(self, current_time: Real) -> None:
        self._callback(self._compute_callback_arg(current_time))

    def _compute_callback_arg(self, current_time: Real):
        # Compute the new phase offset so that frequency changes
        # do not create a discontinuities
        self._phase_offset = (
                self._phase_offset + _2PI * current_time * (
                    1.0 / self._previous_frequency - 1.0 / self._frequency
                )) % _2PI

        phase = (
            _2PI * current_time / self.frequency + self._phase_offset) % _2PI

        self._previous_frequency = self._frequency
        return self.intensity * self._waveform(phase) + self.center

    def _spin_wait(self, time_seconds: float):
        start = time.time()
        now = start
        while now < start + time_seconds and not self._stop_signal:
            now = time.time()
