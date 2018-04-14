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


class ModulatorException(Exception):
    pass


class BaseModulator(ABC):

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

    @property
    @abstractmethod
    def intensity(self) -> Real:
        raise NotImplementedError

    @intensity.setter
    @abstractmethod
    def intensity(self, value: Real):
        raise NotImplementedError

    def get_intensity(self) -> Real:
        return self.intensity

    def set_intensity(self, value: Real) -> None:
        self.intensity = value

    @property
    @abstractmethod
    def center(self) -> Real:
        raise NotImplementedError

    @center.setter
    @abstractmethod
    def center(self, value: Real) -> None:
        raise NotImplementedError

    def get_center(self) -> Real:
        return self.center

    def set_center(self, value: Real) -> None:
        self.center = value
