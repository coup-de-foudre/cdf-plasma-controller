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

from controller.keyboard.keyboard_controller import KeyboardController
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
        default=1.0,
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


def main():
    sys.setswitchinterval(5e-4)
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
        update_frequency=40,
    )

    controller = KeyboardController(pwm_frequency_modulator, interrupter)

    # Try-catch-finally is a workaround for issue here:
    # https://www.raspberrypi.org/forums/viewtopic.php?t=66445&start=175#p1156097
    with controller as c:
        c.run()


if __name__ == '__main__':
    sys.exit(main())
