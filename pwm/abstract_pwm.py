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


class AbstractPWM(ABC):

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

    @property
    @abstractmethod
    def frequency(self) -> Real:
        raise NotImplementedError

    @frequency.setter
    @abstractmethod
    def frequency(self, value: Real) -> None:
        """Set the frequency without starting or stopping the PWM"""
        raise NotImplementedError
