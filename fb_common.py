#!/usr/bin/env python3
# Copyright 2018 Ian Leonard <antonlacon@gmail.com>
#
# This file is fb_common.py and is part of the Foundational IRC Bot for
# Twitch.tv project.
#
# fb_common.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# fb_common.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with fb_common.py. If not, see <http://www.gnu.org/licneses/>.

# Core Modules
import random   # Random number generator

def generate_number(min_val, max_val):
    """ Return a random integer where min_val <= N <= max_val """
    return random.randint(min_val, max_val)
