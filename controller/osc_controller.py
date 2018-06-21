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

"""Controller for the OSC input

The following OSC addresses are defined:

    /pwm/center-frequency <float>
         PWM center frequency in Hz. Optionally accepts an additional
         float which specifies the offset factor; otherwise, the
         offset factor is reset to zero.

    /pwm/frequency-offset-factor <float>
        Offset factor for the center frequency. Should be between [-1, 1].
        The true frequency is given by

            center-frequency * (1 + offset-factor)

        This simplifies implementations of small modulations of the input
        frequency around a fixed center frequency.

    /pwm/duty-cycle <float>
        Set the PWM duty cycle. Generally, we recommend 0.5.

    /interrupter/frequency <float>
        Interrupter frequency in Hz.

    /interrupter/duty-cycle <float>
        Interrupter duty cycle in Hz.

"""
import argparse
import logging
import sys

from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher

from controller.base_controller import BaseController
from interrupter.simple_interrupter import SimpleInterrupter
from pwm.mock_pwm import MockPWM
from pwm.pi_pwm import PiHardwarePWM

logger = logging.getLogger(__name__)


class OSCController(BaseController):

    """Set up OSC controls for the RPi

    To ensure proper startup / shutdown, this class can be used as
    a context manager, e.g.,

        with OSCController(...) as controller:
            controller.run()

    Otherwise, you must manually call the .start() and .stop() methods.
    """

    def __init__(self,
                 osc_bind: str,
                 pwm_pin: int,
                 pwm_host: str,
                 pwm_frequency: float,
                 pwm_duty_cycle: float,
                 interrupter_frequency: float,
                 interrupter_duty_cycle: float,
                 mock: bool=False):
        """
        :param osc_bind: The ip:port for the OSC server to listen on
        :param pwm_pin: GPIO pin number
        :param pwm_host: Hostname of the RPi
        :param pwm_frequency: Frequency of PWM (Hz)
        :param pwm_duty_cycle: Duty cycle of PWM (Hz)
        :param interrupter_frequency: Frequency of interrupter (Hz)
        :param interrupter_duty_cycle: Duty cycle of interrupter in [0,1]
        :param mock: Whether to use a mock PWM for testing.
        """
        logging.debug(f"{locals()}")

        self.osc_bind_host, self.osc_bind_port = osc_bind.split(':')

        if mock:
            self._pwm = MockPWM()
        else:
            self._pwm = PiHardwarePWM(pwm_pin, pwm_host)

        self._pwm_center_frequency = pwm_frequency
        self._pwm_offset_factor = 0.0
        self._set_pwm_frequency_with_offset()
        self._pwm.duty_cycle = pwm_duty_cycle

        self._interrupter = SimpleInterrupter(
            self._pwm,
            interrupter_frequency,
            interrupter_duty_cycle)

    def _set_pwm_frequency_with_offset(self):
        self._pwm.frequency = self._pwm_center_frequency * (
                1 + self._pwm_offset_factor)

    def set_pwm_center_frequency(self,
                                 osc_path,
                                 center_frequency,
                                 offset_factor: float=0.0):
        """Set the new center frequency

        :param osc_path: OSC path that this is called with
        :param center_frequency: Center frequency in Hz
        :param offset_factor: Optional new offset factor. By default, it's
             reset to zero.
        """
        logger.debug(f"{locals()}")
        del osc_path  # unused
        self._pwm_center_frequency = center_frequency
        self._pwm_offset_factor = offset_factor
        self._set_pwm_frequency_with_offset()

    def set_pwm_offset_factor(self, osc_path, offset_factor: float):
        """Set the PWM frequency offset factor

        :param osc_path: OSC path that this is called with
        :param offset_factor: A number between -1 and 1. The output
            frequency is center_frequency * (1+offset_factor).
        """
        logger.debug(f"{locals()}")
        del osc_path  # unused
        self._pwm_offset_factor = offset_factor
        self._set_pwm_frequency_with_offset()

    def set_pwm_duty_cycle(self, osc_path, duty_cycle: float):
        """Set the duty cycle of the PWM

        :param osc_path: OSC path that this is called with
        :param duty_cycle: A number between -1 and 1.
        """
        logger.debug(f"{locals()}")
        del osc_path  # unused
        self._pwm.duty_cycle = duty_cycle

    def set_interrupter_frequency(self, osc_path, frequency: float):
        """Set the interrupter frequency

        :param osc_path: OSC path that this is called with
        :param frequency: The interrupter frequency in Hz
        """
        logger.debug(f"{locals()}")
        del osc_path  # unused
        self._interrupter.frequency = frequency

    def set_interrupter_duty_cycle(self, osc_path, duty_cycle: float):
        """Handler to set the interrupter duty cycle

        :param osc_path: OSC path that this is called with
        :param duty_cycle: A number in [0,1]. If set to 1, no interruption.
        """
        logger.debug(f"{locals()}")
        del osc_path  # unused
        self._interrupter.duty_cycle = duty_cycle

    def start(self):
        """Start the PWM"""
        logger.debug("Starting")
        self._pwm.start()
        self._interrupter.start()

    def shutdown(self):
        """Gracefully stop the pwm"""
        logger.debug("Shutting down")
        self._pwm.stop()
        self._interrupter.stop()

    def _get_dispatcher(self) -> Dispatcher:
        dispatcher = Dispatcher()
        dispatcher.map("/pwm/center-frequency",
                       self.set_pwm_center_frequency)
        dispatcher.map("/pwm/frequency-offset-factor",
                       self.set_pwm_offset_factor)
        dispatcher.map("/pwm/duty-cycle",
                       self.set_pwm_duty_cycle)
        dispatcher.map("/interrupter/frequency",
                       self.set_interrupter_frequency)
        dispatcher.map("/interrupter/duty-cycle",
                       self.set_interrupter_duty_cycle)
        return dispatcher

    def run(self):
        dispatcher = self._get_dispatcher()
        server = osc_server.ThreadingOSCUDPServer(
            (self.osc_bind_host, int(self.osc_bind_port)), dispatcher)
        server.serve_forever()

    def __enter__(self) -> BaseController:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)

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

    parser.add_argument('-v', '--verbose',
                        action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    return args


def set_up_logging(level=logging.DEBUG):
    logging.basicConfig(level=level)


def main():
    set_up_logging()
    sys.setswitchinterval(5e-4)
    args = parse_arguments()

    with OSCController(
            args.osc_bind,
            args.pin,
            args.host,
            args.pwm_frequency,
            args.pwm_duty_cycle,
            args.interrupter_frequency,
            args.interrupter_duty_cycle,
            args.mock) as controller:
        controller.run()


if __name__ == "__main__":
    sys.exit(main())
