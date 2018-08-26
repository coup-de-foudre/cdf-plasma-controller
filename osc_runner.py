#!/usr/bin/env python3
import sys
import os
from configparser import ConfigParser
from argparse import ArgumentParser
import logging

from typing import Dict, Union, Tuple

from plasma.controller.base_controller import BaseController
from plasma.controller.osc_controller import OSCController
from plasma.interrupter.simple_interrupter import SimpleInterrupter
from plasma.modulator.callback_modulator import CallbackModulator
from plasma.pwm.mock_pwm import MockPWM
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


def cpu_serial() -> Union[str, None]:
    """The serial number of the CPU or None if unknown"""
    result = None
    with open('/proc/cpuinfo', 'r') as fp:
        for line in fp:
            if line.startswith('Serial'):
               result = line.split(':')[1].strip()
    _logger().warn("Unable to get serial number")
    return result


def set_up_logging(verbosity_level: int=0) -> None:
    """Set up custom log formats and levels based on verbosity"""
    # TODO: Refactor this into a single utility

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

    _logger().debug("verbosity_level: %s", verbosity_level)


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


def configure_controller(config_file: str=_DEFAULT_CONFIG) \
        -> BaseController:

    _logger().info("Reading configuration file %s", config_file)
    config=ConfigParser()
    with open(config_file, "r") as fp:
        config.read_file(fp)

    serial = cpu_serial()
    _logger().debug("Got serial number %s", serial)
    if serial is None:
        section = "MOCK"
        _logger().warn("No serial number; using section %s", section)
    else:
        section = serial

    options = dict(config.items(section))
    _logger().debug("Options: %s", options)

    pin = config.getint(section, "pin")
    host = config.get(section, "host")

    if config.getboolean(section, "mock"):
        pwm = MockPWM()
    else:
        pwm = PiHardwarePWM(pin, host)

    pwm.frequency = config.getfloat(section, "center_frequency")
    pwm.duty_cycle = 1.0

    interrupter_frequency = 0.0
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
    host, port = parse_bind_host(config.get(section, "osc_bind"))
    controller = OSCController(host, port, modulator, interrupter,
                               fine_spread=fine_spread,
                               address_roots=osc_roots.split(','))
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
