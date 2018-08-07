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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument()
    parser.add_argument(
        "--server",
        metavar="IP:PORT",
        default="127.0.0.1:5005",
        type=str,
        help="The ip:port of the OSC server")


if __name__ == '__main__':
    sys.exit(main())