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


import math
import os


SCREEN_SIZE = [400, 240]
TILE_SIZE = 16
FPS = 60
DELTA_MIN = FPS / 2
DELTA_MAX = FPS * 4

GRAVITY = 0.4

PLAYER_MAX_HP = 50
PLAYER_MAX_SPEED = 3
PLAYER_ROLL_MAX_SPEED = 8
PLAYER_ACCELERATION = 0.5
PLAYER_ROLL_ACCELERATION = 0.25
PLAYER_AIR_ACCELERATION = 0.15
PLAYER_FRICTION = 0.75
PLAYER_ROLL_FRICTION = 0.02
PLAYER_AIR_FRICTION = 0.02
PLAYER_JUMP_HEIGHT = 5 * TILE_SIZE + 2
PLAYER_FALL_SPEED = 7
PLAYER_SLIDE_SPEED = 0.25
PLAYER_ROLL_SLIDE_SPEED = 0
PLAYER_ROLL_SLOPE_ACCELERATION = 0.25
PLAYER_HITSTUN = FPS
PLAYER_AIM_LOCK_TIME = FPS / 2
WARP_TIME = FPS / 10
DEATH_TIME = 3 * FPS
DOUBLETAP_TIME = FPS / 3

ANNEROY_BALL_BOUNCE_HEIGHT = 2
ANNEROY_BALL_FORCE_BOUNCE_SPEED = 4
ANNEROY_WALLJUMP_HEIGHT = 3 * TILE_SIZE
ANNEROY_WALLJUMP_SPEED = PLAYER_MAX_SPEED
ANNEROY_WALLJUMP_FRAME_TIME = FPS / 4
ANNEROY_RUN_FRAMES_PER_PIXEL = 1 / 10
ANNEROY_BALL_FRAMES_PER_PIXEL = 1 / 4
ANNEROY_BBOX_X = -7
ANNEROY_BBOX_WIDTH = 14
ANNEROY_STAND_BBOX_Y = -16
ANNEROY_STAND_BBOX_HEIGHT = 40
ANNEROY_CROUCH_BBOX_Y = -5
ANNEROY_CROUCH_BBOX_HEIGHT = 29
ANNEROY_BALL_BBOX_Y = 10
ANNEROY_BALL_BBOX_HEIGHT = 14
ANNEROY_HEDGEHOG_TIME = 15
ANNEROY_HEDGEHOG_FRAME_TIME = 4
ANNEROY_HEDGEHOG_BBOX_X = -14
ANNEROY_HEDGEHOG_BBOX_Y = 3
ANNEROY_HEDGEHOG_BBOX_WIDTH = 28
ANNEROY_HEDGEHOG_BBOX_HEIGHT = 28
ANNEROY_SLOTH_MAX_SPEED = 0.5
ANNEROY_BULLET_SPEED = 8
ANNEROY_BULLET_DSPEED = ANNEROY_BULLET_SPEED * math.sin(math.radians(45))
ANNEROY_BULLET_LIFE = 45
ANNEROY_XRECOIL = 0.5
ANNEROY_XRECOIL_MAX = 2
ANNEROY_YRECOIL = 1.75
ANNEROY_YRECOIL_MAX = 4
ANNEROY_DECOMPRESS_LAX = 4

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

backgrounds = {}
loaded_music = {}

fullscreen = False
