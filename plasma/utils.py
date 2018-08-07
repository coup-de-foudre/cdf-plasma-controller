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
import logging
from typing import Tuple


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
