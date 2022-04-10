# Hexoshi
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


import os


SCREEN_SIZE = [400, 240]
TILE_SIZE = 16
FPS = 60
DELTA_MIN = FPS / 2
DELTA_MAX = FPS * 4

datadir = "data"
configdir = os.path.join(
    os.getenv("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"),
                                              ".config")), "hexoshi")
localdir = os.path.join(
    os.getenv("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local",
                                            "share")), "hexoshi")
scale = 2
fsscale = None
no_hud = False
