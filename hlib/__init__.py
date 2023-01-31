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

from . import game


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

MANTANOID_WANDER_SPEED = 1
MANTANOID_WANDER_INTERVAL = FPS * 2
MANTANOID_APPROACH_SPEED = 1.5
MANTANOID_APPROACH_INTERVAL = FPS / 4
MANTANOID_HOP_HEIGHT = 2 * TILE_SIZE
MANTANOID_JUMP_HEIGHT = 4 * TILE_SIZE
MANTANOID_WALK_FRAMES_PER_PIXEL = 1 / 6
MANTANOID_LEVEL_DISTANCE = 48
MANTANOID_SLASH_DISTANCE = 30
MANTANOID_SLASH2_DISTANCE = 44
MANTANOID_BBOX_X = -12
MANTANOID_BBOX_Y = -16
MANTANOID_BBOX_WIDTH = 24
MANTANOID_BBOX_HEIGHT = 48
MANTANOID_SLASH_BBOX_X = -12
MANTANOID_SLASH_BBOX_Y = -27
MANTANOID_SLASH_BBOX_WIDTH = 38
MANTANOID_SLASH_BBOX_HEIGHT = 59
MANTANOID_DOUBLESLASH_OFFSET = 18
MANTANOID_SLASH2_BBOX_X = 0
MANTANOID_SLASH2_BBOX_Y = -20
MANTANOID_SLASH2_BBOX_WIDTH = 24
MANTANOID_SLASH2_BBOX_HEIGHT = 32

SCORPION_WALK_FRAMES_PER_PIXEL = 1 / 6

CEILING_LAX = 2

CAMERA_STOPPED_THRESHOLD = 1
CAMERA_STOPPED_HSPEED_MAX = 2
CAMERA_HSPEED_FACTOR = 1 / 8
CAMERA_VSPEED_FACTOR = 1 / 16
CAMERA_OFFSET_FACTOR = 10
CAMERA_MARGIN_TOP = 6 * TILE_SIZE
CAMERA_MARGIN_BOTTOM = 6 * TILE_SIZE
CAMERA_TARGET_MARGIN_BOTTOM = SCREEN_SIZE[1] / 2

LIFE_FORCE_CHANCE = 0.25
LIFE_FORCE_SPEED = 1
LIFE_FORCE_HEAL = 5

LIGHT_RANGE = 300

SHAKE_FRAME_TIME = FPS / DELTA_MIN
SHAKE_AMOUNT = 3

MAP_CELL_WIDTH = 8
MAP_CELL_HEIGHT = 8

TEXT_SPEED = 1000

SAVE_NSLOTS = 10
MENU_MAX_ITEMS = 14

SOUND_MAX_RADIUS = 200
SOUND_ZERO_RADIUS = 600
SOUND_CENTERED_RADIUS = 75
SOUND_TILTED_RADIUS = 500
SOUND_TILT_LIMIT = 0.75

datadir = "data"
if os.name == "nt":
    basedir = os.getenv("APPDATA", os.path.expanduser("~"))
    configdir = os.path.join(basedir, "Hexoshi", "config")
    localdir = os.path.join(basedir, "Hexoshi", "data")
    del basedir
else:
    configdir = os.path.join(
        os.getenv("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"),
                                                  ".config")), "hexoshi")
    localdir = os.path.join(
        os.getenv("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"),
                                                ".local", "share")), "hexoshi")
scale = 2
fsscale = None
no_hud = False
god = False

fullscreen = False
scale_method = None
sound_volume = 1
music_volume = 1
stereo_enabled = True
fps_enabled = False
metroid_controls = False
joystick_threshold = 0.5
left_key = ["left"]
right_key = ["right"]
up_key = ["up"]
down_key = ["down"]
aim_diag_key = ["a"]
jump_key = ["space"]
shoot_key = ["d"]
secondary_key = ["s"]
aim_up_key = ["e"]
aim_down_key = ["q"]
pause_key = ["enter"]
map_key = ["tab"]
left_js = [(0, "axis-", 0), (0, "hat_left", 0)]
right_js = [(0, "axis+", 0), (0, "hat_right", 0)]
up_js = [(0, "axis-", 1), (0, "hat_up", 0)]
down_js = [(0, "axis+", 1), (0, "hat_down", 0)]
aim_diag_js = [(0, "button", 10), (0, "button", 11)]
jump_js = [(0, "button", 1), (0, "button", 3)]
shoot_js = [(0, "button", 0)]
secondary_js = [(0, "button", 2)]
aim_up_js = [(0, "button", 5), (0, "button", 7)]
aim_down_js = [(0, "button", 4), (0, "button", 6)]
pause_js = [(0, "button", 9)]
map_js = [(0, "button", 8)]
save_slots = [None for i in range(SAVE_NSLOTS)]

abort = False

current_save_slot = None
player_name = "Anneroy"
watched_timelines = []
current_level = None
spawn_point = None
map_revealed = set()
map_explored = set()
map_removed = set()
warp_pads = set()
powerups = set()
rooms_killed = set()
progress_flags = set()
artifacts = 0
etanks = 0
time_taken = 0

spawn_xoffset = 0
spawn_yoffset = 0

player = None

backgrounds = {}
loaded_music = {}

map_rooms = {}
map_objects = {}
num_powerups = 0
num_artifacts = 0
