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
import logging

from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher

from controller.base_controller import BaseController
from interrupter.base_interrupter import BaseInterrupter
from pwm.base_pwm import BasePWM


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
                 pwm: BasePWM,
                 interrupter: BaseInterrupter,
                 ):
        """
        :param osc_bind: The ip:port for the OSC server to listen on
        :param pwm: The PWM to use
        :param interrupter: The interrupter to use
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("%s", locals())

        self.osc_bind_host, self.osc_bind_port = osc_bind.split(':')
        self._pwm = pwm
        self._interrupter = interrupter

        self._pwm_center_frequency = pwm.frequency
        self._pwm_offset_factor = 0.0
        self._set_pwm_frequency_with_offset()
        self._pwm.duty_cycle = pwm.duty_cycle

    def _set_pwm_frequency_with_offset(self):
        self._pwm.frequency = self._pwm_center_frequency * (
                1 + self._pwm_offset_factor)

    def set_pwm_center_frequency(self,
                                 osc_path,
                                 center_frequency,
                                 offset_factor: float=None):
        """Set the new center frequency

        :param osc_path: OSC path that this is called with
        :param center_frequency: Center frequency in Hz
        :param offset_factor: Optional new offset factor. By default, it's
             reset to zero.
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        if offset_factor is None:
            offset_factor = 0.0
        self._pwm_center_frequency = center_frequency
        self._pwm_offset_factor = offset_factor
        self._set_pwm_frequency_with_offset()

    def set_pwm_offset_factor(self, osc_path, offset_factor: float):
        """Set the PWM frequency offset factor

        :param osc_path: OSC path that this is called with
        :param offset_factor: A number between -1 and 1. The output
            frequency is center_frequency * (1+offset_factor).
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_offset_factor = offset_factor
        self._set_pwm_frequency_with_offset()

    def set_pwm_duty_cycle(self, osc_path, duty_cycle: float):
        """Set the duty cycle of the PWM

        :param osc_path: OSC path that this is called with
        :param duty_cycle: A number between -1 and 1.
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm.duty_cycle = duty_cycle

    def set_interrupter_frequency(self, osc_path, frequency: float):
        """Set the interrupter frequency

        :param osc_path: OSC path that this is called with
        :param frequency: The interrupter frequency in Hz
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._interrupter.frequency = frequency

    def set_interrupter_duty_cycle(self, osc_path, duty_cycle: float):
        """Handler to set the interrupter duty cycle

        :param osc_path: OSC path that this is called with
        :param duty_cycle: A number in [0,1]. If set to 1, no interruption.
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._interrupter.duty_cycle = duty_cycle

    def start(self):
        """Start the PWM"""
        self.logger.debug("Starting")
        self._pwm.start()
        self._interrupter.start()

    def shutdown(self):
        """Gracefully stop the pwm"""
        self.logger.debug("Shutting down")
        self._pwm.stop()
        self._interrupter.stop()

    def run(self):
        """Start the controller and block thread execution"""
        self.logger.debug("Running")
        dispatcher = self._get_dispatcher()
        server = osc_server.ThreadingOSCUDPServer(
            (self.osc_bind_host, int(self.osc_bind_port)), dispatcher)
        server.serve_forever()

    def _get_dispatcher(self) -> Dispatcher:
        self.logger.debug("Creating dispatcher")
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

    def __enter__(self) -> BaseController:
        self.logger.debug("Entering 'with' statement")
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug("%s", locals())
        self.shutdown()
