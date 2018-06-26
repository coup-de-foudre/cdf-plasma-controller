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

from numbers import Real
import logging

from .base_pwm import BasePWM


class MockPWM(BasePWM):

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._log = self._logger.info
        self._duty_cycle = 0.5
        self._frequency = 1.0
        self._is_stopped = False

    @property
    def duty_cycle(self) -> Real:
        self._log("%s", locals())
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value: Real):
        self._log("%s", locals())
        self._duty_cycle = value

    @property
    def frequency(self) -> Real:
        self._log("%s", locals())
        return self._frequency

    @frequency.setter
    def frequency(self, value: Real):
        self._log("%s", locals())
        self._frequency = value

    @property
    def is_stopped(self) -> bool:
        self._log("%s", locals())
        return self._is_stopped

    def start(self) -> None:
        self._log("%s", locals())
        self._is_stopped = False

    def stop(self) -> None:
        self._log("%s", locals())
        self._is_stopped = True
