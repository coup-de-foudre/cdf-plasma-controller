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


class PWMException(Exception):
    """Base class for all exceptions in this module"""
    pass


class BasePWM(ABC):

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
        """Set the duty cycle without starting or stopping the PWM"""
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
        """Set the frequency without starting or stopping the PWM"""
        raise NotImplementedError

    def get_frequency(self) -> Real:
        return self.frequency

    def set_frequency(self, value: Real) -> None:
        self.frequency = value

    def __str__(self):
        return ("{}("
                "frequency={}, "
                "duty_cycle={}, "
                "is_stopped={}"
                ")".format(self.__class__.__name__,
                           self.frequency,
                           self.duty_cycle,
                           self.is_stopped,
                           ))

    def __repr__(self):
        return "<{} at 0x{:02X}>".format(self, id(self))
