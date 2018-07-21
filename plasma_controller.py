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
from typing import Tuple

from plasma.controller.base_controller import BaseController
from plasma.controller.keyboard.keyboard_controller import KeyboardController
from plasma.controller.osc_controller import OSCController
from plasma.interrupter.simple_interrupter import SimpleInterrupter
from plasma.modulator.callback_modulator import CallbackModulator
from plasma.pwm.mock_pwm import MockPWM
from plasma.pwm.pi_pwm import PiHardwarePWM


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the CdF Plasma Controller")

    parser.add_argument(
        "--controller-type",
        type=str,
        default="keyboard",
        choices={"keyboard", "OSC"},
        help="Choose the control method (default: 'keyboard')"
    )
    parser.add_argument(
        "--osc-bind",
        default="0.0.0.0:5005",
        help="The host:port for the OSC server to listen on. "
             "If the port is not specified, the default 5005 "
             "is used.  (default: 0.0.0.0:5005)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="use mock PWM to test controller without a Pi"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="RPi host (default: local daemon)",
    )
    parser.add_argument(
        '--pin',
        type=int,
        choices=(12, 13, 18, 19),
        default=18,
        help="GPIO pin to run hardware PWM (default: 18)",
    )
    parser.add_argument(
        '-m', '--modulator-frequency',
        dest='modulator_frequency',
        type=float,
        default=0.0,
        help="frequency (Hz) of FM modulator (default: 0.0)",
    )
    parser.add_argument(
        '-M', '--modulator-spread',
        dest='modulator_spread',
        type=float,
        default=1.0,
        help="frequency spread (Hz) of FM modulator (default: 1.0)",
    )
    parser.add_argument(
        '-D',
        dest='interrupter_duty_cycle',
        type=float,
        default=1.0,
        help="duty cycle of the interrupter (default: 1.0 == no interrupter)",
    )
    parser.add_argument(
        '-F',
        dest='interrupter_frequency',
        type=float,
        default=100.0,
        help="frequency (Hz) of the interrupter (default: 100.0)",
    )
    parser.add_argument(
        '-d',
        dest='pwm_duty_cycle',
        type=float,
        default=0.5,
        help="duty cycle of the PWM (default: 0.5)",
    )
    parser.add_argument(
        '-f',
        dest='pwm_frequency',
        type=float,
        help="frequency of the PWM",
        required=True
    )
    parser.add_argument(
        '-r', '--osc-roots',
        default="pwm",
        help="OSC address roots to bind, separated by commas (default: pwm)",
    )
    parser.add_argument(
        '-v', '--verbose',
        action="count",
        help="Enable verbose logging. Repeat up to three times for more logging"
    )
    return parser.parse_args()


def set_up_logging(verbosity_level: int=0):
    """Set up custom log formats and levels based on verbosity"""

    if verbosity_level is None:
        verbosity_level = 0

    if verbosity_level >= 3:
        level = logging.DEBUG
        pwm_level = logging.DEBUG
    elif verbosity_level == 2:
        level = logging.DEBUG
        pwm_level = logging.INFO
    elif verbosity_level == 1:
        level = logging.INFO
        pwm_level = logging.WARNING
    else:  # verbosity_level == 0
        level = logging.WARNING
        pwm_level = logging.ERROR

    log_format = "%(levelname)s:%(name)s:%(filename)s:" \
                 "%(funcName)s:%(lineno)d:%(message)s"
    logging.basicConfig(level=level, format=log_format)

    logging.getLogger().setLevel(level)

    mock_logger = logging.getLogger('pwm')
    mock_logger.setLevel(pwm_level)

    logging.getLogger(__name__).debug("verbosity_level: %s", verbosity_level)


def parse_bind_host(osc_bind_arg: str,
                    default_port: int=5005) -> Tuple[str, int]:
    """Parse OSC bind argument "host:port" into (host, port)"""
    parts = osc_bind_arg.split(':')
    host = parts[0]
    if len(parts) > 1:
        port = int(parts[1])
    else:
        port = default_port
    return host, port


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
        host, port = parse_bind_host(args.osc_bind)
        controller = OSCController(host,
                                   port,
                                   modulator,
                                   interrupter,
                                   args.osc_roots.split(','))
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
