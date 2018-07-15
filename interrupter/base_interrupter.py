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

from abc import ABC, abstractmethod
from numbers import Real

from pwm.base_pwm import BasePWM


class InterrupterException(Exception):
    pass


class BaseInterrupter(ABC):
    """Cycle on and off PWM at a fixed interval"""

    @property
    @abstractmethod
    def pwm(self) -> BasePWM:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_stopped(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def duty_cycle(self) -> Real:
        raise NotImplementedError

    @duty_cycle.setter
    @abstractmethod
    def duty_cycle(self, duty_cycle: Real) -> None:
        raise NotImplementedError

    def get_duty_cycle(self) -> Real:
        return self.duty_cycle

    def set_duty_cycle(self, value: Real) -> None:
        self.duty_cycle = value

    @property
    @abstractmethod
    def frequency(self) -> Real:
        raise NotImplementedError

    @frequency.setter
    @abstractmethod
    def frequency(self, value: Real) -> None:
        raise NotImplementedError

    def get_frequency(self) -> Real:
        return self.frequency

    def set_frequency(self, value: Real) -> None:
        self.frequency = value

    def __str__(self):
        return (f"{self.__class__.__name__}("
                f"frequency={self.frequency}, " 
                f"duty_cycle={self.duty_cycle}, " 
                f"is_stopped={self.is_stopped}"
                f"pwm={self.pwm!r})")

    def __repr__(self):
        return f"<{self} at 0x{id(self):02X}>"
