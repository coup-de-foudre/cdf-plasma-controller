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

from abc import ABC, abstractmethod


class ControllerException(Exception):
    """All exceptions thrown by this module inherit from this"""
    pass


class BaseController(ABC):

    @abstractmethod
    def run(self):
        raise NotImplementedError

    @abstractmethod
    def __enter__(self) -> 'BaseController':
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError
