#!/usr/bin/env python

# Copyright (C) 2018 Julie Marchant <onpon4@riseup.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import json
import os

import six

CONFIG = os.path.join(os.path.expanduser("~"), ".config", "hexoshi")


if __name__ == "__main__":
    try:
        with open(os.path.join(CONFIG, "config.json")) as f:
            cfg = json.load(f)
    except (IOError, ValueError):
        print("No valid config data found in {}.".format(CONFIG))
        six.moves.input("Press Enter to exit.")
    else:
        ai_data = cfg.get("ai_data", [])
        with open("ai_data.json", 'w') as f:
            json.dump(ai_data, f, indent=4)
