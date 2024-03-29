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


import sge

import hlib


def update_fullscreen():
    if hlib.fullscreen:
        sge.game.scale = hlib.fsscale or None
        sge.game.fullscreen = True
    else:
        sge.game.fullscreen = False
        sge.game.scale = hlib.scale
        sge.game.scale = None


def refresh_screen(time_passed, delta_mult):
    """
    Wrapper for sge.game.refresh() which also calls the paused step
    events, in case they make any changes to the screen by way of
    window projections. Prevents flickering bugs.
    """
    sge.game.event_paused_step(time_passed, delta_mult)
    sge.game.current_room.event_paused_step(time_passed, delta_mult)
    for obj in sge.game.current_room.objects[:]:
        obj.event_paused_step(time_passed, delta_mult)

    sge.game.refresh()
