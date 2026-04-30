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
"""Runtime helpers shared between osc_runner.py, plasma_controller.py, and
score_player.py."""

import logging
from typing import Tuple, Union


def cpu_serial() -> Union[str, None]:
    """The serial number of the CPU or None if unknown.

    Returns None on platforms without `/proc/cpuinfo` (e.g. development on
    macOS), so callers can fall back to a MOCK config section.
    """
    result = None
    try:
        fp = open('/proc/cpuinfo', 'r')
    except FileNotFoundError:
        logging.getLogger(__name__).warning(
            "/proc/cpuinfo not available; running off-Pi?")
        return None
    with fp:
        for line in fp:
            if line.startswith('Serial'):
                result = line.split(':')[1].strip()
    if result is None:
        logging.getLogger(__name__).warning("Unable to get serial number")
    return result


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


def set_up_logging(verbosity_level: int=0) -> None:
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
