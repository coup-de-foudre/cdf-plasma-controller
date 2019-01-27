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

from numbers import Integral, Real

import logging
import threading

import pigpio

from .base_pwm import BasePWM, PWMException


logger = logging.getLogger(__name__)


class PiPWMException(PWMException):
    pass


class PiHardwarePWM(BasePWM):
    """Thread-safe hardware PWM for the RPi"""

    _MAX_DUTY_CYCLE_TICKS = 1000000

    def __init__(self,
                 gpio_pin: Integral,
                 host: str = None,
                 port: Integral = '8888'):

        if host is None:
            self._pi = pigpio.pi()
        else:
            self._pi = pigpio.pi(host, port)
        self._pin = gpio_pin
        self._is_stopped = True
        self._frequency = 0.0
        self._duty_cycle = 0.5
        self._lock = threading.RLock()

        if not self._pi.connected:
            raise PiPWMException(
                "Unable to connect to pi %s:%s", host, port)

        self.stop()

    def __del__(self):
        self.stop()

    def start(self) -> None:
        if self._is_stopped:
            self._is_stopped = self._frequency <= 0.0
            self._sync_hardware()

    def stop(self) -> None:
        if not self._is_stopped:
            self._is_stopped = True
            self._sync_hardware()

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    @property
    def duty_cycle(self) -> Real:
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value: Real):
        self._validate_duty_cycle(value)
        self._duty_cycle = value
        self._sync_hardware()

    @property
    def frequency(self) -> Real:
        return self._frequency

    @frequency.setter
    def frequency(self, value: Real) -> None:
        self._validate_frequency(value)
        self._frequency = value
        self._sync_hardware()

    def _sync_hardware(self):
        with self._lock:
            set_frequency = int(0 if self.is_stopped else self._frequency)
            self._pi.hardware_PWM(self._pin,
                                  set_frequency,
                                  self._duty_cycle_ticks())

    def _duty_cycle_ticks(self):
        return int(self._duty_cycle * self._MAX_DUTY_CYCLE_TICKS)

    @staticmethod
    def _validate_frequency(frequency: Real):
        if frequency < 0:
            raise PiPWMException(
                "PWM frequency should be non-negative, not %s",
                frequency)

    @staticmethod
    def _validate_duty_cycle(duty_cycle: Real):
        # noinspection PyTypeChecker
        if duty_cycle < 0 or duty_cycle > 1:
            raise PiPWMException(
                "PWM duty cycle should be in [0,1], not %s", duty_cycle)
