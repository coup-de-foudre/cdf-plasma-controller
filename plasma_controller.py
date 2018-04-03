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

from controller.keyboard_controller import KeyboardController
from pwm.pi_pwm import PiHardwarePWM
from pwm.simple_interrupter import SimpleInterrupter


def main():
    parser = argparse.ArgumentParser(
        description="Run the CdF Plasma Controller with a keyboard controller")

    parser.add_argument(
        "--host",
        type=str,
        default='localhost',
        help="raspberry PI host (localhost)",
    )

    parser.add_argument(
        '--pin',
        type=int,
        choices=(12, 13, 18, 19),
        default=18,
        help="GPIO pin to run hardware PWM (18)",
    )

    parser.add_argument(
        '-D',
        dest='interrupter_duty_cycle',
        type=float,
        default=1.0,
        help="duty cycle of the interrupter (1.0 = no interrupter by default)",
    )

    parser.add_argument(
        '-d',
        dest='pwm_duty_cycle',
        type=float,
        default=0.5,
        help="duty cycle of the PWM (0.5)",
    )

    parser.add_argument(
        '-F',
        dest='interrupter_frequency',
        type=float,
        default=100.0,
        help="frequency (Hz) of the interrupter (100.0)",
    )

    parser.add_argument(
        '-f',
        dest='pwm_frequency',
        type=float,
        help="frequency of the PWM",
        required=True
    )

    args = parser.parse_args()

    pwm = PiHardwarePWM(args.pin, args.host)
    pwm.frequency = args.pwm_frequency
    pwm.duty_cycle = args.pwm_duty_cycle

    interrupter = SimpleInterrupter(pwm,
                                    args.interrupter_frequency,
                                    args.interrupter_duty_cycle)

    controller = KeyboardController(interrupter)

    # Try-catch-finally is a workaround for issue here:
    # https://www.raspberrypi.org/forums/viewtopic.php?t=66445&start=175#p1156097
    try:
        controller.run()
    except AttributeError:
        pass
    finally:
        pwm.stop()


if __name__ == '__main__':
    sys.exit(main())
