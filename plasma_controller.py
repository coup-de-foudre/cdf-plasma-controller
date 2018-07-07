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
import logging
import sys

from controller.base_controller import BaseController
from controller.keyboard.keyboard_controller import KeyboardController
from controller.osc_controller import OSCController
from interrupter.simple_interrupter import SimpleInterrupter
from modulator.callback_modulator import CallbackModulator
from pwm.mock_pwm import MockPWM
from pwm.pi_pwm import PiHardwarePWM


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the CdF Plasma Controller")

    parser.add_argument("--controller-type",
                        type=str,
                        default="keyboard",
                        choices={"keyboard", "OSC"},
                        help="Choose the control method (default='keyboard')")

    parser.add_argument("--osc-bind",
                        default="0.0.0.0:5005",
                        help="The ip:port for the OSC server to listen on")

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

    parser.add_argument('-v', '--verbose',
                        action="store_true",
                        help="Enable verbose logging")

    parser.add_argument(
        '-f',
        dest='pwm_frequency',
        type=float,
        help="frequency of the PWM",
        required=True
    )

    return parser.parse_args()


def set_up_logging(verbose=False):
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.WARN
    log_format = "%(levelname)s:%(name)s:%(filename)s:%(funcName)s:%(lineno)d:%(message)s"
    logging.basicConfig(level=level, format=log_format)


def get_controller(args: argparse.Namespace) -> BaseController:
    if args.mock:
        pwm = MockPWM()
    else:
        pwm = PiHardwarePWM(args.pin, args.host)

    pwm.frequency = args.pwm_frequency
    pwm.duty_cycle = args.pwm_duty_cycle

    interrupter = SimpleInterrupter(pwm,
                                    args.interrupter_frequency,
                                    args.interrupter_duty_cycle)

    modulator = CallbackModulator(
        lambda f: pwm.set_frequency(f),
        frequency=args.modulator_frequency,
        spread=args.modulator_spread,
        center=pwm.frequency,
        update_frequency=40,
    )

    if args.controller_type == "keyboard":
        controller = KeyboardController(modulator, interrupter)
    elif args.controller_type == "OSC":
        controller = OSCController(args.osc_bind, modulator, interrupter)
    else:
        raise ValueError("Unknown controller type %s", args.controller_type)

    return controller


def main():
    sys.setswitchinterval(5e-4)
    args = parse_arguments()
    set_up_logging(args.verbose)
    logger = logging.getLogger(__name__)
    logger.debug("Arguments: %s", args)

    with get_controller(args) as c:
        c.run()


if __name__ == '__main__':
    sys.exit(main())
