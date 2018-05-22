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

import time
import unittest
from numbers import Real

from modulator.callback_modulator import CallbackModulator


class TestCallbackModulator(unittest.TestCase):

    def test_callback_modulator(self):
        callback_args_list = []

        def callback(value: Real):
            callback_args_list.append(value)

        update_frequency = 1000
        modulator = CallbackModulator(
            callback,
            center=10,
            frequency=1,
            spread=5,
            update_frequency=update_frequency)
        start_time = time.time()
        modulator.start()
        time.sleep(0.633)
        first_max = max(callback_args_list)
        modulator.set_center(100)
        time.sleep(1-0.633)
        modulator.stop()
        end_time = time.time()
        second_max = max(callback_args_list)

        elapsed_time = end_time - start_time
        self.assertAlmostEqual(len(callback_args_list),
                               update_frequency*elapsed_time,
                               delta=update_frequency*elapsed_time*0.02,
                               msg="Timing loop error should be < 2%")
        self.assertLess(first_max, 20,
                        msg="First calls should have a small value")
        self.assertGreater(second_max, 80,
                           msg="Second set of calls should have larger value")

    def test_zero_frequency(self):
        callback_args_list = []

        def callback(value: Real):
            callback_args_list.append(value)

        update_frequency = 1000
        center_frequency = 10
        modulator = CallbackModulator(
            callback,
            center=center_frequency,
            frequency=0,
            spread=5,
            update_frequency=update_frequency)
        modulator.start()
        time.sleep(0.1)
        modulator.stop()
        self.assertGreater(len(callback_args_list), 0)
        self.assertEqual(
            callback_args_list, [center_frequency]*len(callback_args_list))

    def test_center_is_non_negative(self):
        callback_args_list = []

        def callback(value: Real):
            callback_args_list.append(value)

        update_frequency = 1000
        center_frequency = 0
        modulator = CallbackModulator(
            callback,
            center=center_frequency,
            frequency=100,
            spread=5,
            update_frequency=update_frequency)
        modulator.start()
        time.sleep(0.1)
        modulator.stop()
        self.assertGreater(max(callback_args_list), 0)
        self.assertGreaterEqual(min(callback_args_list), 0.0)


if __name__ == '__main__':
    unittest.main()
