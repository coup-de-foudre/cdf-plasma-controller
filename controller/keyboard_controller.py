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

from interrupter.base_interrupter import BaseInterrupter
from interrupter.simple_interrupter import SimpleInterrupter
from modulator.callback_modulator import CallbackModulator
from pwm.base_pwm import BasePWM
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


def format_curses_int(curses_int: int) -> str:
    """Convert a curses int to an interpretable character"""
    return _CURSES_INT_TO_UNICODE.get(curses_int, chr(curses_int))


class AbstractKeyboardKnob(ABC):
    def __init__(self,
                 name: str,
                 callback: Callable[[Real], None],
                 decrement_key: int,
                 increment_key: int,
                 min_value: Real,
                 max_value: Real,
                 initial_value: Real):
        """

        :param name: Name of the knob to display
        :param callback: Set the value on the knob
        :param decrement_key: Character (int) from curses to decrement knob
        :param increment_key: Character (int) from curses to increment knob
        :param min_value: Minimum knob value
        :param max_value: Maximum knob value
        :param initial_value: The start value for the knob
        """
        self._name = name
        self._setter = callback
        self._decrement_int = decrement_key
        self._increment_int = increment_key
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
                 decrement_key: int,
                 increment_key: int,
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

    def __init__(self, interrupter: SimpleInterrupter):
        self._screen = None
        self._interrupter = interrupter
        self._pwm = interrupter.pwm
        self._break_int = ord('q')

        self._pwm_frequency_modulator = CallbackModulator(
            lambda f: self._pwm.set_frequency(f),
            frequency=0.0,
            intensity=0.0,
            center=self._pwm.frequency,
        )

        self._interrupter_frequency_knob = ProportionalTickKnob(
            "Interrupter frequency (Hz)",
            lambda f: self._interrupter.set_frequency(f),
            KEY_LEFT,
            KEY_RIGHT,
            0.0,
            float("inf"),
            self._interrupter.frequency,
        )

        self._interrupter_duty_cycle_knob = SimpleKnob(
            "Interrupter duty cycle",
            lambda d: self._interrupter.set_duty_cycle(d),
            ord('{'),
            ord('}'),
            0.0,
            1.0,
            self._interrupter.duty_cycle,
        )

        self._pwm_frequency_knob = ProportionalTickKnob(
            "PWM frequency (Hz)",
            lambda c: self._pwm_frequency_modulator.set_center(c),
            KEY_DOWN,
            KEY_UP,
            0.0,
            float("inf"),
            self._pwm_frequency_modulator.center,
        )

        self._pwm_frequency_modulation_freq_knob = SimpleKnob(
            "PWM modulation frequency (Hz)",
            lambda f: self._pwm_frequency_modulator.set_frequency(f),
            ord("_"),
            ord("+"),
            min_value=0.0,
            max_value=30.0,
            initial_value=0.0,
            num_ticks=30,
        )

        self._pwm_freqency_modulation_intensity_knob = ProportionalTickKnob(
            "PWM modulation intensity (Hz)",
            lambda i: self._pwm_frequency_modulator.set_intensity(i),
            ord("("),
            ord(")"),
            min_value=0.0,
            max_value=float("inf"),
            initial_value=self._pwm_frequency_modulator.center/100.0,
        )

        self._pwm_duty_cycle_knob = SimpleKnob(
            "PWM duty cycle",
            lambda d: self._pwm.set_duty_cycle(d),
            ord('<'),
            ord('>'),
            0.0,
            1.0,
            self._pwm.duty_cycle,
        )

        self._knobs = [
            self._interrupter_frequency_knob,
            self._pwm_frequency_knob,
            self._pwm_frequency_modulation_freq_knob,
            self._pwm_freqency_modulation_intensity_knob,
            self._interrupter_duty_cycle_knob,
            self._pwm_duty_cycle_knob,
        ]

        self._keys_to_knobs = self._get_keys_to_knobs(self._knobs)

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
            self._render_knob(knob, window_line=knob_num + start_line)

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
    def pwm(self) -> BasePWM:
        return self._pwm

    @property
    def interrupter(self) -> BaseInterrupter:
        return self._interrupter
