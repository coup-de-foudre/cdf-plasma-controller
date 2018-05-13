#!/usr/bin/env python3

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

import argparse
import sys
from typing import List

from controller.keyboard_controller import KeyboardController, \
    ProportionalTickKnob, SimpleKnob, AbstractKeyboardKnob
from interrupter.base_interrupter import BaseInterrupter
from modulator.base_modulator import BaseModulator
from modulator.callback_modulator import CallbackModulator
from pwm.mock_pwm import MockPWM
from pwm.pi_pwm import PiHardwarePWM
from interrupter.simple_interrupter import SimpleInterrupter


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run the CdF Plasma Controller with a keyboard controller")

    parser.add_argument(
        "--mock",
        action="store_true",
        help="use mock PWM to test controller without a Pi")

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="RPi host (None=local daemon)",
    )

    parser.add_argument(
        '--pin',
        type=int,
        choices=(12, 13, 18, 19),
        default=18,
        help="GPIO pin to run hardware PWM (18)",
    )

    parser.add_argument(
        '-m', '--modulator-frequency',
        dest='modulator_frequency',
        type=float,
        default=0.0,
        help="frequency (Hz) of FM modulator",
    )

    parser.add_argument(
        '-M', '--modulator-spread',
        dest='modulator_spread',
        type=float,
        default=0.0,
        help="frequency spread (Hz) of FM modulator",
    )

    parser.add_argument(
        '-D',
        dest='interrupter_duty_cycle',
        type=float,
        default=1.0,
        help="duty cycle of the interrupter (default == 1.0 == no interrupter)",
    )

    parser.add_argument(
        '-F',
        dest='interrupter_frequency',
        type=float,
        default=100.0,
        help="frequency (Hz) of the interrupter (100.0)",
    )

    parser.add_argument(
        '-d',
        dest='pwm_duty_cycle',
        type=float,
        default=0.5,
        help="duty cycle of the PWM (0.5)",
    )

    parser.add_argument(
        '-f',
        dest='pwm_frequency',
        type=float,
        help="frequency of the PWM",
        required=True
    )

    args = parser.parse_args()

    return args


def keyboard_control_knobs(interrupter: BaseInterrupter,
                           pwm_frequency_modulator: BaseModulator,
                           ) -> List[AbstractKeyboardKnob]:

    pwm = interrupter.pwm

    interrupter_frequency_knob = ProportionalTickKnob(
        "Interrupter frequency (Hz)",
        lambda f: interrupter.set_frequency(f),
        "←",
        "→",
        0.0,
        float("inf"),
        interrupter.frequency,
    )

    interrupter_duty_cycle_knob = SimpleKnob(
        "Interrupter duty cycle",
        lambda d: interrupter.set_duty_cycle(d),
        '{',
        '}',
        0.0,
        1.0,
        interrupter.duty_cycle,
    )

    pwm_frequency_knob = ProportionalTickKnob(
        "PWM frequency (Hz)",
        lambda c: pwm_frequency_modulator.set_center(c),
        "↓",
        "↑",
        0.0,
        float("inf"),
        pwm_frequency_modulator.center,
    )

    pwm_duty_cycle_knob = SimpleKnob(
        "PWM duty cycle",
        lambda d: pwm.set_duty_cycle(d),
        '<',
        '>',
        0.0,
        1.0,
        pwm.duty_cycle,
    )

    pwm_frequency_modulation_freq_knob = SimpleKnob(
        "PWM FM frequency (Hz)",
        lambda f: pwm_frequency_modulator.set_frequency(f),
        "_",
        "+",
        min_value=0.0,
        max_value=30.0,
        initial_value=pwm_frequency_modulator.frequency,
        num_ticks=30,
    )

    pwm_frequency_modulation_intensity_knob = ProportionalTickKnob(
        "PWM FM spread (Hz)",
        lambda i: pwm_frequency_modulator.set_spread(i),
        "(",
        ")",
        min_value=0.0,
        max_value=float("inf"),
        initial_value=pwm_frequency_modulator.spread,
    )

    knobs = [
        interrupter_frequency_knob,
        pwm_frequency_knob,
        interrupter_duty_cycle_knob,
        pwm_duty_cycle_knob,
        pwm_frequency_modulation_freq_knob,
        pwm_frequency_modulation_intensity_knob,
    ]

    return knobs


def main():

    args = parse_arguments()

    if args.mock:
        pwm = MockPWM()
    else:
        pwm = PiHardwarePWM(args.pin, args.host)

    pwm.frequency = args.pwm_frequency
    pwm.duty_cycle = args.pwm_duty_cycle

    interrupter = SimpleInterrupter(pwm,
                                    args.interrupter_frequency,
                                    args.interrupter_duty_cycle)

    pwm_frequency_modulator = CallbackModulator(
        lambda f: pwm.set_frequency(f),
        frequency=args.modulator_frequency,
        spread=args.modulator_spread,
        center=pwm.frequency,
    )

    control_knobs = keyboard_control_knobs(interrupter, pwm_frequency_modulator)
    controller = KeyboardController(control_knobs)

    # Try-catch-finally is a workaround for issue here:
    # https://www.raspberrypi.org/forums/viewtopic.php?t=66445&start=175#p1156097
    try:
        interrupter.start()
        controller.run()
    except AttributeError:
        pass
    finally:
        interrupter.stop()
        pwm.stop()


if __name__ == '__main__':
    sys.exit(main())
