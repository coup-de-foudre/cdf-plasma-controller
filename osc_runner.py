#!/usr/bin/env python3
import glob
import logging
import os
import sys
from argparse import ArgumentParser
from configparser import ConfigParser

# Hack the dependency management
_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
if _BASE_PATH not in sys.path:
    sys.path += [_BASE_PATH]
for vendor_path in glob.glob(os.path.join(_BASE_PATH, 'vendor', '*')):
    if vendor_path not in sys.path:
        sys.path += [vendor_path]

from plasma.controller.base_controller import BaseController
from plasma.controller.osc_controller import OSCController
from plasma.interrupter.simple_interrupter import SimpleInterrupter
from plasma.modulator.callback_modulator import CallbackModulator
from plasma.pwm.mock_pwm import MockPWM
from plasma.utils.runtime import (
    cpu_serial, parse_bind_host, set_up_logging)
try:
    from plasma.pwm.pi_pwm import PiHardwarePWM
except ImportError as e:
    print("Unable to import PiHardwarePWM; "
          "falling back to MockPWM: {}".format(e),
          file=sys.stderr)
    PiHardwarePWM = MockPWM


_BASE_FILE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CONFIG = os.path.join(_BASE_FILE, 'config', 'irobot.conf')


def _logger():
    return logging.getLogger(__name__)


def configure_controller(config_file: str=_DEFAULT_CONFIG) \
        -> BaseController:

    _logger().info("Reading configuration file %s", config_file)
    config = ConfigParser()
    with open(config_file, "r") as fp:
        config.read_file(fp)

    serial = cpu_serial()
    _logger().debug("Got serial number %s", serial)
    if serial is None:
        section = "MOCK"
        _logger().warning("No serial number; using section %s", section)
    else:
        section = serial

    options = dict(config.items(section))
    _logger().debug("Options: %s", options)

    pin = config.getint(section, "pin")
    host = config.get(section, "host")
    if not host:
        host = None

    if config.getboolean(section, "mock"):
        pwm = MockPWM()
    else:
        pwm = PiHardwarePWM(pin, host)

    pwm.frequency = config.getfloat(section, "center_frequency")
    pwm.duty_cycle = config.getfloat(section, "duty_cycle")

    interrupter_frequency = 100.0
    interrupter_duty_cycle = 1.0
    interrupter = SimpleInterrupter(pwm,
                                    interrupter_frequency,
                                    interrupter_duty_cycle)

    modulator_frequency = 0.0
    modulator_spread = 1.0
    modulator = CallbackModulator(
        lambda f: pwm.set_frequency(f),
        frequency=modulator_frequency,
        spread=modulator_spread,
        center=pwm.frequency,
        update_frequency=40,
    )

    fine_spread = config.getfloat(section, "frequency_spread")
    osc_bind = config.get(section, "osc_bind")
    osc_roots = config.get(section, "osc_roots")
    host, port = parse_bind_host(osc_bind)
    controller = OSCController(
        host,
        port,
        modulator,
        interrupter,
        fine_spread=fine_spread,
        address_roots=osc_roots.split(','),
        immediate_on=True,
    )
    return controller


def main():
    sys.setswitchinterval(5e-4)
    parser = ArgumentParser(
        description="Run OSC controller from configuration file",
        epilog="See the configuration files under the"
               "`config` directory for example options."
    )
    parser.add_argument(
        '-c', '--config',
        default=_DEFAULT_CONFIG,
        help="Location of the config file",
    )
    parser.add_argument(
        '-v', '--verbose',
        action="count",
        help="Enable verbose logging. "
             "Repeat up to three times for more logging"
    )
    args = parser.parse_args()

    set_up_logging(verbosity_level=args.verbose)
    with configure_controller(args.config) as c:
        c.run()


if __name__ == '__main__':
    sys.exit(main())
