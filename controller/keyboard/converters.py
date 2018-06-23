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

from _curses import KEY_LEFT, KEY_UP, KEY_RIGHT, KEY_DOWN


def curses_int_to_unicode(curses_int: int) -> str:
    """Convert a curses int to an interpretable character"""
    return _CURSES_INT_TO_UNICODE.get(curses_int, chr(curses_int))


_CURSES_INT_TO_UNICODE = {
    KEY_LEFT: "←",
    KEY_UP: "↑",
    KEY_RIGHT: "→",
    KEY_DOWN: "↓",
}
_UNICODE_TO_CURSES_INT = {v: k for k, v in _CURSES_INT_TO_UNICODE.items()}


def unicode_to_curses_int(unicode_chr: str) -> int:
    if len(unicode_chr) != 1:
        raise ValueError("Cannot convert {} to curses integer: "
                         "length must equal one".format(unicode_chr))
    return _UNICODE_TO_CURSES_INT.get(unicode_chr, ord(unicode_chr))
