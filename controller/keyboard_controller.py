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

import logging
from abc import ABC, abstractmethod
from curses import (wrapper, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN,
                    flash as flash_screen, A_STANDOUT)
from math import log10
from numbers import Real
from typing import Callable, List, Dict

from .base_controller import BaseController, ControllerException

logger = logging.getLogger(__name__)


class KeyboardException(ControllerException):
    pass


_CURSES_INT_TO_UNICODE = {
    KEY_LEFT: "←",
    KEY_UP: "↑",
    KEY_RIGHT: "→",
    KEY_DOWN: "↓",
}

_UNICODE_TO_CURSES_INT = {v: k for k, v in _CURSES_INT_TO_UNICODE.items()}


def curses_int_to_unicode(curses_int: int) -> str:
    """Convert a curses int to an interpretable character"""
    return _CURSES_INT_TO_UNICODE.get(curses_int, chr(curses_int))


def unicode_to_curses_int(unicode_chr: str) -> int:
    if len(unicode_chr) != 1:
        raise KeyboardException("Cannot convert {} to curses integer: "
                                "length must equal one".format(unicode_chr))
    return _UNICODE_TO_CURSES_INT.get(unicode_chr, ord(unicode_chr))


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
        return 10.0 ** (int(log10(self._value / 2.0))) / 100.0


class KeyboardController(BaseController):

    """Control a set of knobs with a keyboard.

    Note that whatever the knobs are controlling should be "running"
    before calling this function
    """

    def __init__(self, knobs: List[AbstractKeyboardKnob]):
        self._knobs = knobs
        self._screen = None
        self._break_int = ord('q')
        self._keys_to_knobs = self._get_keys_to_knobs(self._knobs)

    def _get_keys_to_knobs(self, knobs: List[AbstractKeyboardKnob]) -> Dict[
            int, Callable[[], None]]:
        keys_to_knobs = {}
        for knob in knobs:
            self._add_knob_to_dict(keys_to_knobs,
                                   knob.increment_int,
                                   knob.increment)
            self._add_knob_to_dict(keys_to_knobs,
                                   knob.decrement_int,
                                   knob.decrement)
        return keys_to_knobs

    @staticmethod
    def _add_knob_to_dict(keys_to_knobs: Dict[int, Callable[[], None]],
                          key_int: int,
                          control: Callable[[], None]):
        if key_int in keys_to_knobs:
            raise KeyboardException("Key already used: {}"
                                    "".format(curses_int_to_unicode(key_int)))
        keys_to_knobs[key_int] = control

    def _run_with_screen(self, screen) -> None:
        """
        :param screen: The standard curses window object to run in.
        """
        self._screen = screen
        while True:
            self._draw_screen()
            c = self._screen.getch()
            if c == self._break_int:
                break
            self._keys_to_knobs.get(c, flash_screen)()

    def _draw_screen(self):
        self._screen.clear()
        self._render_top_line()
        self._render_knobs(start_line=2)
        self._screen.refresh()

    def _render_top_line(self):
        _, width = self._screen.getmaxyx()
        message = "To quit, type '{}'".format(
            curses_int_to_unicode(self._break_int))
        message += " " * (width - len(message))
        self._screen.addstr(0, 0, message, A_STANDOUT)

    def _render_knobs(self, start_line):
        for knob_num, knob in enumerate(self._knobs):
            self._render_knob(knob, window_line=knob_num + start_line)

    def _render_knob(self, knob: AbstractKeyboardKnob, window_line: int):
        details = "{:30.29} ({}=dec, {}=inc): {:4.2f}".format(
            knob.name,
            curses_int_to_unicode(knob.decrement_int),
            curses_int_to_unicode(knob.increment_int),
            knob.value,
        )
        self._screen.addstr(window_line, 0, details)

    def run(self):
        wrapper(self._run_with_screen)
