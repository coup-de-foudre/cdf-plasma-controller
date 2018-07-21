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
from math import log10
from numbers import Real
from typing import Callable

from plasma.controller.base_controller import ControllerException
from plasma.controller.keyboard.converters import unicode_to_curses_int


class KeyboardException(ControllerException):
    pass


class AbstractKeyboardKnob(ABC):
    def __init__(self,
                 name: str,
                 callback: Callable[[Real], None],
                 decrement_key: str,
                 increment_key: str,
                 min_value: Real,
                 max_value: Real,
                 initial_value: Real):
        """Get a keyboard knob

        :param name: Name of the knob to display
        :param callback: Set the value on the knob
        :param decrement_key: Unicode character to decrement knob
        :param increment_key: Unicode character to increment knob
        :param min_value: Minimum knob value
        :param max_value: Maximum knob value
        :param initial_value: The start value for the knob
        """
        self._name = name
        self._setter = callback
        self._decrement_int = unicode_to_curses_int(decrement_key)
        self._increment_int = unicode_to_curses_int(increment_key)
        self._min_value = min_value
        self._max_value = max_value
        self._validate_value(min_value, max_value, initial_value)
        self._value = initial_value

    @staticmethod
    def _validate_value(min_value, max_value, value: Real) -> None:
        if value < min_value or value > max_value:
            raise KeyboardException(
                "Value must be between %d and %d, not %d",
                min_value, max_value, value)

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> Real:
        return self._value

    @property
    def decrement_int(self) -> int:
        return self._decrement_int

    @property
    def increment_int(self) -> int:
        return self._increment_int

    def decrement(self) -> None:
        self._value = max(self._value - self.tick_size, self._min_value)
        self._setter(self._value)

    def increment(self) -> None:
        self._value = min(self._value + self.tick_size, self._max_value)
        self._setter(self._value)

    @property
    @abstractmethod
    def tick_size(self) -> Real:
        raise NotImplementedError


class SimpleKnob(AbstractKeyboardKnob):
    DEFAULT_NUM_TICKS = 100

    def __init__(self,
                 name: str,
                 callback: Callable[[Real], None],
                 decrement_key: str,
                 increment_key: str,
                 min_value: Real,
                 max_value: Real,
                 initial_value: Real,
                 *,
                 num_ticks: int=DEFAULT_NUM_TICKS):

        super().__init__(name, callback, decrement_key, increment_key,
                         min_value, max_value, initial_value)
        self.num_ticks = num_ticks

    @property
    def tick_size(self) -> Real:
        return (self._max_value - self._min_value) / self.num_ticks


class ProportionalTickKnob(AbstractKeyboardKnob):
    @property
    def tick_size(self) -> Real:
        if self._value <= 0.0:
            return 0.0001
        else:
            return 10.0 ** (int(log10(self._value / 2.0))) / 100.0
