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
"""Send OSC messages based on sensor input"""

import sys
import argparse
import time

from pythonosc import udp_client

from plasma.utils import parse_bind_host


class OSCSensor:

    def __init__(self,
                 ip: str, port: int,
                 osc_address: str,
                 min_value: float,
                 max_value: float):

        self._client = udp_client.SimpleUDPClient(
            ip, int(port), allow_broadcast=True)
        self._osc_address = osc_address
        self.min_value = min_value
        self.max_value = max_value

    def run(self):
        while True:
            value = min(
                self.max_value, max(self.min_value, self.get_sensor_value()))
            self._client.send_message(self._osc_address, value)
            time.sleep(0.03)

    def get_sensor_value(self):
        # TODO
        raise NotImplementedError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        metavar="IP:PORT",
        default="127.0.0.1:5005",
        type=str,
        help="The ip:port of the OSC server")
    parser.add_argument(
        "--address",
        default="/pwm*/fm/frequency",
        type=str,
        help="The address to send messages to")

    parser.add_argument(
        "--min-value",
        default=0.2,
        type=float,
        help="The minimum value allowed")

    parser.add_argument(
        "--max-value",
        default=12.0,
        type=float,
        help="The maximum value allowed")

    args = parser.parse_args()
    ip, port = parse_bind_host(args.host, 5005)

    OSCSensor(ip, port, args.address, args.min_value, args.max_value).run()


if __name__ == '__main__':
    sys.exit(main())
