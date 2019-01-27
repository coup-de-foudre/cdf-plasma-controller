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

By default, root address for all commands is `pwm0`. With this root, the
following OSC:

    /pwm0/start
        Start the PWM, but does not turn on the interrupter or the FM
        modulator.

    /pwm0/stop
        Turn the PWM off. Also turns the interrupter and FM modulator off.

    /pwm0/toggle <value>

        Toggle on/off based on the value of the argument. No argument or a
        "falsey" value turns stops, while a "truthy" value starts.

    /pwm0/center-frequency <float>
        PWM center frequency in Hz. Resets the fine control value to zero.

    /pwm0/fine/spread <float>
        Set fine control frequency spread around the center frequency

    /pwm0/fine/value <float>
        Set fine control frequency value. Value is capped between [-1, 1].
        The true frequency is given by

            center-frequency + value * spread

        where spread is set with /pwm/fine/spread.

        This simplifies implementations of small modulations of the input
        frequency around a fixed center frequency.

        Use of this endpoint immediately stops the FM modulator.

    /pwm0/duty-cycle <float>
        Set the PWM duty cycle. Settings other than 0.5 (the default) create a
        DC offset in the output, which may damage some circuit configurations.

    /pwm0/fm/start
        Start FM modulation.

    /pwm0/fm/stop
        Stop FM modulation.

    /pwm0/fm/toggle <value>

        Toggle based on the value of the argument. No argument or a
        "falsey" value turns stops, while a "truthy" value starts.

    /pwm0/fm/spread <float>
        Set the PWM FM spread in Hz.

    /pwm0/fm/frequency <float>
        Set the PWM FM frequency in Hz. Use of this endpoint starts the FM
        modulation.

    /pwm0/interrupter/start
        Start the interrupter.

    /pwm0/interrupter/stop
        Stop the interrupter.

    /pwm0/interrupter/toggle <value>

        Toggle based on the value of the argument. No argument or a
        "falsey" value turns stops, while a "truthy" value starts.

    /pwm0/interrupter/frequency <float>
        Interrupter frequency in Hz.

    /pwm0/interrupter/duty-cycle <float>
        Interrupter duty cycle in Hz. Set duty cycle to 1 for no interruption.

"""
import logging
from itertools import repeat
from numbers import Real
from typing import Callable, Any, Sequence, Dict

from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher

from plasma.controller.base_controller import BaseController
from plasma.interrupter.base_interrupter import BaseInterrupter
from plasma.modulator.base_modulator import BaseModulator
from plasma.pwm.base_pwm import BasePWM


def _toggle_callback(
        on: Callable[[str], None],
        off: Callable[[str], None]) -> Callable[[str, Any], None]:
    """Return an OSC callback for that toggles based on truthiness of arg"""

    def toggle_callback(osc_path: str, truthy: Any = None) -> None:
        logging.getLogger(__name__).debug("%s", locals())
        if truthy:
            return on(osc_path)
        else:
            return off(osc_path)

    return toggle_callback


class _Controls:

    def __init__(self,
                 modulator: BaseModulator,
                 interrupter: BaseInterrupter,
                 center_frequency: Real,
                 duty_cycle: Real,
                 fine_spread: float,
                 immediate_on: bool,
                 ):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("%s", locals())

        self._pwm_frequency_modulator = modulator
        self._interrupter = interrupter
        self._pwm: BasePWM = self._interrupter.pwm
        self._center_frequency = center_frequency
        self._duty_cycle = duty_cycle
        self._immediate_on = immediate_on

        self._pwm_center_frequency = self._pwm.frequency
        self._pwm_fine_spread = fine_spread
        self._pwm_fine_value = 0.0
        self._pwm.duty_cycle = self._pwm.duty_cycle
        self._set_pwm_frequency_with_fine_control()

    def _set_pwm_frequency_with_fine_control(self) -> None:
        self._pwm.frequency = (self._pwm_center_frequency +
                               self._pwm_fine_spread * self._pwm_fine_value)

    def set_pwm_on(self, osc_path: str) -> None:
        """Turn the PWM on

        :param osc_path: OSC path this is called with (unused)
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm.start()

    def set_pwm_off(self, osc_path: str, *_) -> None:
        """Turn the PWM off

        Accepts any length of argument.

        :param osc_path: OSC path this is called with (unused)
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_frequency_modulator.stop()
        self._interrupter.stop()
        self._pwm.stop()

    def set_pwm_center_frequency(self,
                                 osc_path,
                                 center_frequency) -> None:
        """Set the new center frequency

        :param osc_path: OSC path that this is called with
        :param center_frequency: Center frequency in Hz
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_center_frequency = center_frequency
        self._pwm_fine_value = 0.0
        self._set_pwm_frequency_with_fine_control()

    def set_pwm_fine_spread(self, osc_path: str, spread: float) -> None:
        """Set the PWM fine control spread

        :param osc_path: OSC path that this is called with
        :param spread: Spread of the fine control, in Hz.
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_fine_spread = spread
        self._pwm_frequency_modulator.stop()
        self._set_pwm_frequency_with_fine_control()

    def set_pwm_fine_value(self, osc_path: str, value: float) -> None:
        self.logger.debug("%s", locals())
        del osc_path  # unused
        if value > 1:
            self.logger.warning("Clipped value greater than 1: %s", value)
            value = 1
        elif value < -1:
            self.logger.warning("Clipped value less than -1: %s", value)
            value = -1
        self._pwm_fine_value = value
        self._pwm_frequency_modulator.stop()
        self._set_pwm_frequency_with_fine_control()

    def set_pwm_duty_cycle(self, osc_path, duty_cycle: float) -> None:
        """Set the duty cycle of the PWM

        :param osc_path: OSC path that this is called with
        :param duty_cycle: A number between -1 and 1.
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm.duty_cycle = duty_cycle

    def set_pwm_fm_start(self, osc_path: str) -> None:
        """Start the FM modulator

        :param osc_path: Unused
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_frequency_modulator.start()

    def set_pwm_fm_stop(self, osc_path: str) -> None:
        """Stop the FM modulator

        :param osc_path: Unused
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_frequency_modulator.stop()

    def set_pwm_fm_spread(self, osc_path: str, spread: float) -> None:
        """Set the FM spread

        :param osc_path: Unused
        :param spread: Frequency spread in Hz
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_frequency_modulator.set_spread(spread)

    def set_pwm_fm_frequency(self, osc_path: str, frequency: float) -> None:
        """Set the FM frequency

        :param osc_path: Unused
        :param frequency: FM freqeuncy in Hz
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._pwm_frequency_modulator.set_frequency(frequency)
        self._pwm_frequency_modulator.start()

    def set_interrupter_start(self, osc_path: str) -> None:
        """Start the interrupter"""
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._interrupter.start()

    def set_interrupter_stop(self, osc_path: str, *_) -> None:
        """Stop the interrupter"""
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._interrupter.stop()

    def set_interrupter_frequency(self, osc_path: str,
                                  frequency: float) -> None:
        """Set the interrupter frequency

        :param osc_path: OSC path that this is called with
        :param frequency: The interrupter frequency in Hz
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._interrupter.frequency = frequency

    def set_interrupter_duty_cycle(self, osc_path: str,
                                   duty_cycle: float) -> None:
        """Handler to set the interrupter duty cycle

        :param osc_path: OSC path that this is called with
        :param duty_cycle: A number in [0,1]. If set to 1, no interruption.
        """
        self.logger.debug("%s", locals())
        del osc_path  # unused
        self._interrupter.duty_cycle = duty_cycle

    def start(self) -> None:
        """Start the PWM"""
        self._interrupter.start()
        if self._immediate_on:
            self.logger.warning("Turning on PWM immediately")
            self._pwm.start()
        else:
            self.logger.info("Starting OSC controller, but PWM will not start "
                             "until a start command is received.")

    def shutdown(self) -> None:
        """Gracefully stop the pwm"""
        self.logger.debug("Shutting down")
        self._pwm_frequency_modulator.stop()
        self._interrupter.stop()
        self._pwm.stop()


class OSCController(BaseController):

    """Set up OSC controls for the RPi

    This allows multiple PWMs for a single controller. Due to hardware
    restrictions, the PWM output is linked on pins (12, 18) and pins (13, 19).
    You cannot get independent frequencies on these pairs.

    To ensure proper startup / shutdown, this class can be used as
    a context manager, e.g.,

        with OSCController(...) as controller:
            controller.run()

    Otherwise, you must manually call the .start() and .stop() methods.
    """

    def __init__(self, osc_host: str,
                 osc_port: int,
                 pwm_frequency_modulators: Sequence[BaseModulator],
                 interrupters: Sequence[BaseInterrupter],
                 fine_spreads: Sequence[float] = None,
                 address_roots: Sequence[str] = None,
                 immediate_on: bool = False,
                 ):
        """
        :param osc_host: The hostname for the OSC server to listen on
        :param osc_port: The port for the OSC server to listen on
        :param pwm_frequency_modulators: The frequency modulators for the PWM
        :param interrupters: The interrupters to use; corresponds to the
            pwm_frequency_modulators, and hence must be the  same length.
        :param fine_spreads: The initial fine control spread in Hz. Defaults
            to zero for all PWMs.
        :param address_roots: The root addresses to bind (default:
            ['pwm0', 'pwm1', ...]). Leading and trailing slashes have no
            effect, but multiple parts are allowed, e.g., `pwm/channel-01`.
        :param immediate_on: Turn on all PWMs upon initialization (default:
            False)

        :raises ValueError if the sequences do not have the same length
        """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("%s", locals())

        num_modulators = len(pwm_frequency_modulators)
        if fine_spreads is None:
            fine_spreads = list(repeat(0.0, num_modulators))
        if address_roots is None:
            address_roots = list(
                "pwm{}".format(n) for n in range(num_modulators))

        num_interrupters = len(interrupters)
        num_spread = len(fine_spreads)
        num_address_roots = len(address_roots)

        if any(num != num_modulators for num in [
                num_interrupters, num_address_roots, num_spread]):
            raise ValueError(
                "The number of modulators must match the number of "
                "interrupters, address_roots, and fine_spreads.")

        self.osc_bind_host, self.osc_bind_port = osc_host, osc_port

        # Remove leading and trailing `/` in roots
        stripped_address_roots = (r.strip('/') for r in address_roots)

        self._roots_to_controls: Dict[str, _Controls] = {
            r: _Controls(
                modulator=m,
                interrupter=i,
                center_frequency=i.pwm.frequency,
                duty_cycle=i.pwm.duty_cycle,
                fine_spread=f if f is not None else 0.0,
                immediate_on=immediate_on,
            ) for r, m, i, f in zip(
                 stripped_address_roots,
                 pwm_frequency_modulators,
                 interrupters,
                 fine_spreads,
            )
        }
        controls_len = len(self._roots_to_controls)

        if controls_len != num_address_roots:
            raise ValueError("The address roots must be unique.")

    def run(self) -> None:
        """Start the controller and block thread execution"""
        self.logger.debug("Running")
        dispatcher = self._get_dispatcher()
        self.logger.info("Binding OSC server to %s:%s",
                         self.osc_bind_host, self.osc_bind_port)
        server = osc_server.ThreadingOSCUDPServer(
            (self.osc_bind_host, self.osc_bind_port), dispatcher)
        server.serve_forever()

    def _get_dispatcher(self) -> Dispatcher:
        self.logger.info("Binding dispatcher to OSC address roots %s",
                         self._roots_to_controls.keys())
        dispatcher = Dispatcher()
        for root, control in self._roots_to_controls.items():
            dispatcher.map("/{root}/start".format(root=root), control.set_pwm_on)
            dispatcher.map("/{root}/stop".format(root=root), control.set_pwm_off)
            dispatcher.map("/{root}/toggle".format(root=root),
                           _toggle_callback(control.set_pwm_on,
                                            control.set_pwm_off))
            dispatcher.map("/{root}/center-frequency".format(root=root),
                           control.set_pwm_center_frequency)

            dispatcher.map("/{root}/fine/spread".format(root=root),
                           control.set_pwm_fine_spread)
            dispatcher.map("/{root}/fine/value".format(root=root),
                           control.set_pwm_fine_value)

            dispatcher.map("/{root}/fm/start".format(root=root),
                           control.set_pwm_fm_start)
            dispatcher.map("/{root}/fm/stop".format(root=root),
                           control.set_pwm_fm_stop)
            dispatcher.map("/{root}/fm/toggle",
                           _toggle_callback(control.set_pwm_fm_start,
                                            control.set_pwm_fm_stop))
            dispatcher.map("/{root}/fm/spread".format(root=root),
                           control.set_pwm_fm_spread)
            dispatcher.map("/{root}/fm/frequency".format(root=root),
                           control.set_pwm_fm_frequency)
            dispatcher.map("/{root}/duty-cycle".format(root=root),
                           control.set_pwm_duty_cycle)

            dispatcher.map("/{root}/interrupter/start".format(root=root),
                           control.set_interrupter_start)
            dispatcher.map("/{root}/interrupter/stop".format(root=root),
                           control.set_interrupter_stop)
            dispatcher.map("/{root}/interrupter/toggle".format(root=root),
                           _toggle_callback(control.set_interrupter_start,
                                            control.set_interrupter_stop))
            dispatcher.map("/{root}/interrupter/frequency".format(root=root),
                           control.set_interrupter_frequency)
            dispatcher.map("/{root}/interrupter/duty-cycle".format(root=root),
                           control.set_interrupter_duty_cycle)
        return dispatcher

    def __enter__(self) -> BaseController:
        self.logger.debug("Entering 'with' statement")
        for root, control in self._roots_to_controls.items():
            self.logger.debug("Starting controller for %s", root)
            control.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.logger.debug("%s", locals())
        for root, control in self._roots_to_controls.items():
            self.logger.debug("Shutting down controller for %s", root)
            control.shutdown()
