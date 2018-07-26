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
from numbers import Real
from concurrent.futures import ThreadPoolExecutor
import time

from plasma.interrupter.base_interrupter import (
    BaseInterrupter, InterrupterException)
from plasma.pwm.base_pwm import BasePWM


class SimpleInterrupter(BaseInterrupter):
    """Interrupter that uses PWM start/stop calls to turn on and off a PWM

    This class is prone to jitter, particularly when the on/off calls to the
    PWM go over a network.
    """

    def __init__(self,
                 pwm: BasePWM,
                 frequency: float,
                 duty_cycle: float=0.5):

        self._validate_frequency(frequency)
        self._validate_duty_cycle(duty_cycle)

        self._pwm = pwm
        self._frequency = frequency
        self._duty_cycle = duty_cycle
        self._is_stopped = True

        self._executor = ThreadPoolExecutor(max_workers=1)
        self._run_future = None
        self._stop_signal = True

        self._time_error = 0.0
        self._run_lock = threading.Lock()

    def __del__(self):
        self.stop()

    @staticmethod
    def _validate_frequency(frequency: Real):
        if frequency < 0:
            raise InterrupterException(
                "Interrupter frequency should be non-negative, not %s",
                frequency)

    @staticmethod
    def _validate_duty_cycle(duty_cycle: float):
        if duty_cycle < 0 or duty_cycle > 1:
            raise InterrupterException(
                "Interrupter duty cycle should be in [0,1], not %s",
                duty_cycle)

    @property
    def frequency(self) -> Real:
        return self._frequency

    @frequency.setter
    def frequency(self, value: Real):
        self._validate_frequency(value)
        self._frequency = value

    @property
    def duty_cycle(self) -> float:
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value: float):
        self._validate_duty_cycle(value)
        self._duty_cycle = value

    @property
    def pwm(self) -> BasePWM:
        return self._pwm

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    def start(self) -> None:
        if self.is_stopped:
            self._run_future = self._executor.submit(self._run)

    def stop(self) -> None:
        if not self.is_stopped:
            self._stop_signal = True
            self._wait_for_run_to_finish()

    def _wait_for_run_to_finish(self):
        self._run_future.result()

    def _run(self) -> None:
        self._stop_signal = False
        with self._run_lock:
            self._is_stopped = False
            while not self._stop_signal:
                self._toggle_and_wait()
            self._is_stopped = True

    def _toggle_and_wait(self):
        toggle_time = time.time()
        toggle_seconds = 0.0
        if self._pwm.is_stopped and self.duty_cycle > 0.0:
            toggle_seconds = (
                1.0 / self.frequency * self.duty_cycle - self._time_error)
            self._pwm.start()
        elif self.duty_cycle < 1.0:
            toggle_seconds = (
                1.0 / self.frequency * (1 - self.duty_cycle)
                - self._time_error)
            self._pwm.stop()
        if toggle_seconds > 0:
            self._spin_wait(toggle_seconds)
        self._time_error = time.time() - toggle_time - toggle_seconds

    def _spin_wait(self, time_seconds: float):
        start = time.time()
        now = start
        while now < start + time_seconds and not self._stop_signal:
            now = time.time()
