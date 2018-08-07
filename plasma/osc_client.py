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
"""Send an OSC message to a specified client"""

import argparse
import sys

from pythonosc import udp_client

from plasma.utils import parse_bind_host


def parse_into_type(parameter: str):
    """Parse a parameter into either a float, int, or string"""
    result = parameter
    try:
        result = float(parameter)
    except ValueError:
        pass
    else:
        try:
            result = int(parameter)
        except ValueError:
            pass
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        metavar="IP:PORT",
        default="127.0.0.1:5005",
        type=str,
        help="The host of the OSC server")
    parser.add_argument("address", help="Address for the message")
    parser.add_argument("value", nargs='*', help="Message values")

    args = parser.parse_args()

    ip, port = parse_bind_host(args.host, 5005)

    client = udp_client.SimpleUDPClient(ip, int(port), allow_broadcast=True)
    client.send_message(args.address, map(parse_into_type, args.value))


if __name__ == "__main__":
    sys.exit(main())
