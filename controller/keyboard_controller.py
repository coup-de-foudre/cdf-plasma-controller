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

from pwm.abstract_interrupter import AbstractPWMInterrupter
from pwm.abstract_pwm import AbstractPWM
from .abstract_controller import AbstractController, ControllerException

logger = logging.getLogger(__name__)


class KeyboardException(ControllerException):
    pass


_CURSES_INT_TO_UNICODE = {
    KEY_LEFT: "←",
    KEY_UP: "↑",
    KEY_RIGHT: "→",
    KEY_DOWN: "↓",
}


def format_curses_int(curses_int: int) -> str:
    """Convert a curses int to an interpretable character"""
    return _CURSES_INT_TO_UNICODE.get(curses_int, chr(curses_int))


class AbstractKeyboardKnob(ABC):
    def __init__(self,
                 name: str,
                 setter: Callable[[Real], None],
                 decrement_int: int,
                 increment_int: int,
                 min_value: Real,
                 max_value: Real,
                 initial_value: Real):
        self._name = name
        self._setter = setter
        self._decrement_int = decrement_int
        self._increment_int = increment_int
        self._min_value = min_value
        self._max_value = max_value
        self._validate_value(min_value, max_value, initial_value)
        self._value = initial_value

    @staticmethod
    def _validate_value(min_value, max_value, value) -> None:
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
    num_ticks = 100

    @property
    def tick_size(self) -> Real:
        return (self._max_value - self._min_value) / self.num_ticks


class ProportionalTickKnob(AbstractKeyboardKnob):
    @property
    def tick_size(self) -> Real:
        return 10.0 ** (int(log10(self._value / 2.0))) / 100.0


class KeyboardController(AbstractController):
    def __init__(self, interrupter: AbstractPWMInterrupter):
        self._screen = None
        self._interrupter = interrupter
        self._pwm = interrupter.pwm
        self._break_int = ord('q')

        self._interrupter_frequency_knob = ProportionalTickKnob(
            "Interrupter frequency (Hz)",
            lambda f: self._interrupter_frequency_setter(f),
            KEY_LEFT,
            KEY_RIGHT,
            0.0,
            float("inf"),
            self._interrupter.frequency,
        )

        self._interrupter_duty_cycle_knob = SimpleKnob(
            "Interrupter duty cycle",
            lambda d: self._interrupter_duty_cycle_setter(d),
            ord('{'),
            ord('}'),
            0.0,
            1.0,
            self._interrupter.duty_cycle,
        )

        self._pwm_frequency_knob = ProportionalTickKnob(
            "PWM frequency (Hz)",
            lambda f: self._pwm_frequency_setter(f),
            KEY_DOWN,
            KEY_UP,
            0.0,
            float("inf"),
            self._pwm.frequency,
        )

        self._pwm_duty_cycle_knob = SimpleKnob(
            "PWM duty cycle",
            lambda d: self._pwm_duty_cycle_setter(d),
            ord('<'),
            ord('>'),
            0.0,
            1.0,
            self._pwm.duty_cycle,
        )

        self._knobs = [
            self._interrupter_frequency_knob,
            self._pwm_frequency_knob,
            self._interrupter_duty_cycle_knob,
            self._pwm_duty_cycle_knob,
        ]

        self._keys_to_knobs = self._get_keys_to_knobs(self._knobs)

    def _interrupter_frequency_setter(self, value: Real) -> None:
        self._interrupter.frequency = value

    def _interrupter_duty_cycle_setter(self, value: Real) -> None:
        self._interrupter.duty_cycle = value

    def _pwm_frequency_setter(self, value: Real) -> None:
        self._pwm.frequency = value

    def _pwm_duty_cycle_setter(self, value: Real) -> None:
        self._pwm.duty_cycle = value

    @staticmethod
    def _get_keys_to_knobs(knobs: List[AbstractKeyboardKnob]) -> Dict[
            int, Callable[[], None]]:
        keys_to_knobs = {}
        for knob in knobs:
            keys_to_knobs[knob.increment_int] = knob.increment
            keys_to_knobs[knob.decrement_int] = knob.decrement
        return keys_to_knobs

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
            format_curses_int(self._break_int))
        message += " " * (width - len(message))
        self._screen.addstr(0, 0, message, A_STANDOUT)

    def _render_knobs(self, start_line):
        for knob_num, knob in enumerate(self._knobs):
            self._render_knob(knob, window_line=knob_num+start_line)

    def _render_knob(self, knob: AbstractKeyboardKnob, window_line: int):
        details = "{:30.29} ({}=dec, {}=inc): {:4.2f}".format(
                knob.name,
                format_curses_int(knob.decrement_int),
                format_curses_int(knob.increment_int),
                knob.value,
        )
        self._screen.addstr(window_line, 0, details)

    def run(self):
        self.interrupter.start()
        wrapper(self._run_with_screen)
        self.interrupter.stop()

    @property
    def pwm(self) -> AbstractPWM:
        return self._pwm

    @property
    def interrupter(self) -> AbstractPWMInterrupter:
        return self._interrupter
