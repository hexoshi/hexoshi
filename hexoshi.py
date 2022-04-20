#!/usr/bin/env python3

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


__version__ = "0.3a0"


import argparse
import datetime
import gettext
import itertools
import json
import math
import os
import random
import sys
import time
import traceback
import warnings
import weakref

import sge
import xsge_gui
import xsge_lighting
import xsge_particle
import xsge_path
import xsge_physics
import xsge_tiled

import hlib


if getattr(sys, "frozen", False):
    __file__ = sys.executable

hlib.datadir = os.path.join(os.path.dirname(__file__), "data")

gettext.install("hexoshi", os.path.abspath(os.path.join(hlib.datadir, "locale")))

parser = argparse.ArgumentParser()
parser.add_argument(
    "--version", action="version", version=f"Hexoshi {__version__}",
    help=_("Output version information and exit."))
parser.add_argument(
    "-p", "--print-errors",
    help=_("Print errors directly to stdout rather than saving them in a file."),
    action="store_true")
parser.add_argument(
    "-l", "--lang",
    help=_("Manually choose a different language to use."))
parser.add_argument(
    "--nodelta",
    help=_("Disable delta timing. Causes the game to slow down when it can't "
           "run at full speed instead of becoming choppier."),
    action="store_true")
parser.add_argument(
    "-d", "--datadir",
    help=_('Where to load the game data from (Default: "{}")').format(hlib.datadir))
parser.add_argument(
    "--scale",
    help=_('The scale factor to use by default in windowed mode (Default: '
           '"{}")').format(hlib.scale))
parser.add_argument(
    "--fsscale",
    help=_("Specify a scale factor to use in fullscreen mode instead of using "
           "dynamic scaling. This will cause the screen resolution to change, "
           "which may improve performance. For best results, specify this as "
           "the target resolution width divided by {w}, or as the target "
           "resolution height divided by {h} (whichever is smaller). For "
           "example, to target a resolution of 640x480, use {ex}. A scale "
           "factor of 1 will always be fastest, but may result in "
           "windowboxing.").format(
               w=hlib.SCREEN_SIZE[0], h=hlib.SCREEN_SIZE[1],
               ex=min(640 / hlib.SCREEN_SIZE[0], 480 / hlib.SCREEN_SIZE[1])))
parser.add_argument(
    "--no-backgrounds",
    help=_("Only show solid colors for backgrounds (uses less RAM)."),
    action="store_true")
parser.add_argument(
    "--no-hud", help=_("Don't show the player's heads-up display."),
    action="store_true")
parser.add_argument(
    "-m", "--gen-map", help=_("Generate the map even if it already exists."),
    action="store_true")
parser.add_argument(
    "-s", "--save-map", help=_('Save an image of the full map as "map.png".'),
    action="store_true")
parser.add_argument(
    "--dist-ai", help=_("Write the AI data to the game data directory instead "
                        "of the user data directory (for distribution)."),
    action="store_true")
parser.add_argument(
    "-q", "--quit",
    help=_("Quit immediately on startup (useful with -m or -s)."),
    action="store_true")
parser.add_argument("--god")
args = parser.parse_args()

PRINT_ERRORS = args.print_errors
DELTA = not args.nodelta
if args.datadir:
    hlib.datadir = args.datadir
if args.scale:
    hlib.scale = eval(args.scale)
if args.fsscale:
    hlib.fsscale = eval(args.fsscale)
NO_BACKGROUNDS = args.no_backgrounds
hlib.no_hud = args.no_hud
GEN_MAP = args.gen_map
SAVE_MAP = args.save_map
DIST_AI = args.dist_ai
QUIT = args.quit
GOD = (args.god and args.god.lower() == "inbailey")

if args.lang:
    lang = gettext.translation("hexoshi",
                               os.path.abspath(os.path.join(hlib.datadir, "locale")),
                               [args.lang])
    lang.install()

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
PLAYER_JUMP_HEIGHT = 5 * hlib.TILE_SIZE + 2
PLAYER_FALL_SPEED = 7
PLAYER_SLIDE_SPEED = 0.25
PLAYER_ROLL_SLIDE_SPEED = 0
PLAYER_ROLL_SLOPE_ACCELERATION = 0.25
PLAYER_HITSTUN = hlib.FPS
PLAYER_AIM_LOCK_TIME = hlib.FPS / 2
WARP_TIME = hlib.FPS / 10
DEATH_TIME = 3 * hlib.FPS
DOUBLETAP_TIME = hlib.FPS / 3

ANNEROY_BALL_BOUNCE_HEIGHT = 2
ANNEROY_BALL_FORCE_BOUNCE_SPEED = 4
ANNEROY_WALLJUMP_HEIGHT = 3 * hlib.TILE_SIZE
ANNEROY_WALLJUMP_SPEED = PLAYER_MAX_SPEED
ANNEROY_WALLJUMP_FRAME_TIME = hlib.FPS / 4
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
ANNEROY_EXPLODE_TIME = 0.6 * hlib.FPS
ANNEROY_DECOMPRESS_LAX = 4

MANTANOID_WANDER_SPEED = 1
MANTANOID_WANDER_INTERVAL = hlib.FPS * 2
MANTANOID_APPROACH_SPEED = 1.5
MANTANOID_APPROACH_INTERVAL = hlib.FPS / 4
MANTANOID_HOP_HEIGHT = 2 * hlib.TILE_SIZE
MANTANOID_JUMP_HEIGHT = 4 * hlib.TILE_SIZE
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
CAMERA_MARGIN_TOP = 6 * hlib.TILE_SIZE
CAMERA_MARGIN_BOTTOM = 6 * hlib.TILE_SIZE
CAMERA_TARGET_MARGIN_BOTTOM = hlib.SCREEN_SIZE[1] / 2

LIFE_FORCE_CHANCE = 0.25
LIFE_FORCE_SPEED = 1
LIFE_FORCE_HEAL = 5

LIGHT_RANGE = 300

SHAKE_FRAME_TIME = hlib.FPS / hlib.DELTA_MIN
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

ETANK_CHAR = '\x80'

backgrounds = {}
loaded_music = {}

fullscreen = False
scale_method = None
sound_enabled = True
music_enabled = True
stereo_enabled = True
fps_enabled = False
metroid_controls = False
joystick_threshold = 0.1
left_key = [["left", "a"]]
right_key = [["right", "d"]]
up_key = [["up", "w"]]
down_key = [["down", "s"]]
aim_diag_key = [["alt_left", "alt_right"]]
jump_key = [["space"]]
shoot_key = [["ctrl_left", "ctrl_right"]]
aim_up_key = [["x"]]
aim_down_key = [["z"]]
mode_reset_key = [["shift_left", "shift_right"]]
mode_key = [["tab"]]
pause_key = [["enter", "p"]]
map_key = [["m"]]
left_js = [[(0, "axis-", 0), (0, "hat_left", 0)]]
right_js = [[(0, "axis+", 0), (0, "hat_right", 0)]]
up_js = [[(0, "axis-", 1), (0, "hat_up", 0)]]
down_js = [[(0, "axis+", 1), (0, "hat_down", 0)]]
aim_diag_js = [[(0, "button", 10), (0, "button", 11)]]
jump_js = [[(0, "button", 1), (0, "button", 3)]]
shoot_js = [[(0, "button", 0)]]
aim_up_js = [[(0, "button", 5), (0, "button", 7)]]
aim_down_js = [[(0, "button", 4), (0, "button", 6)]]
mode_reset_js = [[(0, "button", 2)]]
mode_js = [[(0, "button", 8)]]
pause_js = [[(0, "button", 9)]]
map_js = [[]]
save_slots = [None for i in range(SAVE_NSLOTS)]

with open(os.path.join(hlib.datadir, "ai_data.json"), 'r') as f:
    ai_data = json.load(f)

abort = False

current_save_slot = None
player_name = "Anneroy"
watched_timelines = []
current_level = None
spawn_point = None
map_revealed = []
map_explored = []
map_removed = []
warp_pads = []
powerups = []
progress_flags = []
artifacts = 0
etanks = 0
time_taken = 0

spawn_xoffset = 0
spawn_yoffset = 0

player = None


class Game(sge.dsp.Game):

    fps_real = hlib.FPS
    fps_time = 0
    fps_frames = 0
    fps_text = ""
    cheatcode = ""

    def event_step(self, time_passed, delta_mult):
        self.fps_time += time_passed
        self.fps_frames += 1
        if self.fps_time >= 250:
            self.fps_real = (1000 * self.fps_frames) / self.fps_time
            self.fps_text = '{:.2f}'.format(self.fps_real)
            self.fps_time = 0
            self.fps_frames = 0

        if fps_enabled:
            self.project_text(font_small, self.fps_text, self.width - 8,
                              self.height - 8, z=1000000,
                              color=sge.gfx.Color("yellow"), halign="right",
                              valign="bottom")

    def event_key_press(self, key, char):
        if key == "f7":
            self.cheatcode = ""
        elif sge.keyboard.get_pressed("f7"):
            if not self.cheatcode:
                print(_("Code entry:"), end=' ')
            self.cheatcode += char
            print(char, end='')
            sys.stdout.flush()

    def event_key_release(self, key):
        global map_revealed
        global map_explored

        if key == "f7":
            if self.cheatcode:
                print()

                if self.cheatcode.lower() == "knowitall":
                    map_revealed = list(map_objects.keys())
                elif self.cheatcode.lower() == "seenitall":
                    map_explored = map_revealed
                elif self.cheatcode.startswith("tele"):
                    warp(self.cheatcode[4:] + ".json")
                else:
                    print(_("Invalid cheat code: {}").format(self.cheatcode))

    def event_close(self):
        self.end()

    def event_paused_close(self):
        self.event_close()


class Level(sge.dsp.Room):

    """Handles levels."""

    def __init__(self, objects=(), *, background=None,
                 object_area_width=hlib.TILE_SIZE * 2,
                 object_area_height = hlib.TILE_SIZE * 2,
                 name=None, bgname=None, music=None, timeline=None,
                 ambient_light=None, disable_lights=False, music_noloop=False,
                 **kwargs):
        self.fname = None
        self.name = name
        self.music = music
        self.music_noloop = music_noloop
        self.timeline_objects = {}
        self.shake_queue = 0
        self.death_time = None
        self.status_text = None
        self.player_z = 0

        if bgname is not None:
            background = backgrounds.get(bgname, background)

        self.load_timeline(timeline)

        if ambient_light:
            self.ambient_light = sge.gfx.Color(ambient_light)
            if (self.ambient_light.red >= 255 and
                    self.ambient_light.green >= 255 and
                    self.ambient_light.blue >= 255):
                self.ambient_light = None
        else:
            self.ambient_light = None

        self.disable_lights = disable_lights or self.ambient_light is None

        super().__init__(objects, background=background,
                         object_area_width=object_area_width,
                         object_area_height=object_area_height, **kwargs)
        self.add(gui_handler)

    def load_timeline(self, timeline):
        self.timeline = {}
        self.timeline_name = ""
        self.timeline_step = 0
        self.timeline_skip_target = None
        if timeline:
            self.timeline_name = timeline
            fname = os.path.join(hlib.datadir, "timelines", timeline)
            with open(fname, 'r') as f:
                jt = json.load(f)

            for i in jt:
                self.timeline[eval(i)] = jt[i]

    def add_timeline_object(self, obj):
        if obj.ID is not None:
            self.timeline_objects[obj.ID] = weakref.ref(obj)

    def timeline_skipto(self, step):
        t_keys = sorted(self.timeline.keys())
        self.timeline_step = step
        while t_keys and t_keys[0] < step:
            i = t_keys.pop(0)
            self.timeline[i] = []

    def show_hud(self):
        # Show darkness
        if self.ambient_light:
            xsge_lighting.project_darkness(ambient_light=self.ambient_light,
                                           buffer=hlib.TILE_SIZE * 2)
        else:
            xsge_lighting.clear_lights()

        if not hlib.no_hud:
            # TODO: Add HUD showing health, ammo, etc.

            if self.status_text:
                sge.game.project_text(font, self.status_text,
                                      sge.game.width / 2, sge.game.height - 16,
                                      color=sge.gfx.Color("white"),
                                      halign="center", valign="middle")
                self.status_text = None

    def shake(self, num=1):
        shaking = (self.shake_queue or "shake_up" in self.alarms or
                   "shake_down" in self.alarms)
        self.shake_queue = max(self.shake_queue, num)
        if not shaking:
            self.event_alarm("shake_down")

        for obj in self.objects:
            if isinstance(obj, SteadyIcicle):
                obj.check_shake(True)

    def pause(self, player_x=None, player_y=None):
        if (self.timeline_skip_target is not None and
              self.timeline_step < self.timeline_skip_target):
            self.timeline_skipto(self.timeline_skip_target)
        else:
            play_sound(pause_sound)
            PauseMenu.create(player_x=player_x, player_y=player_y)

    def die(self):
        sge.game.start_room.start(transition="fade")

    def win_game(self):
        credits_room = CreditsScreen.load(os.path.join("special",
                                                       "credits.json"))
        credits_room.start()

    def event_room_start(self):
        if player is not None:
            self.add(player)
        ##self.add(lava_animation)

        xsge_lighting.clear_lights()

        play_music(self.music, noloop=self.music_noloop)

    def event_room_resume(self):
        play_music(self.music, noloop=self.music_noloop)

    def event_step(self, time_passed, delta_mult):
        global watched_timelines
        global time_taken

        time_taken += time_passed / 1000

        for view in self.views:
            for obj in self.get_objects_at(
                    view.x - LIGHT_RANGE, view.y - LIGHT_RANGE,
                    view.width + LIGHT_RANGE * 2,
                    view.height + LIGHT_RANGE * 2):
                if isinstance(obj, InteractiveObject):
                    if not self.disable_lights:
                        obj.project_light()

                ##if not obj.active:
                    ##if isinstance(obj, (Lava, LavaSurface)):
                    ##    obj.image_index = lava_animation.image_index

        # Show HUD
        self.show_hud()

        # Timeline events
        t_keys = sorted(self.timeline.keys())
        while t_keys:
            i = t_keys.pop(0)
            if i <= self.timeline_step:
                while i in self.timeline and self.timeline[i]:
                    command = self.timeline[i].pop(0)
                    command = command.split(None, 1)
                    if command:
                        if len(command) >= 2:
                            command, arg = command[:2]
                        else:
                            command = command[0]
                            arg = ""

                        if command.startswith("#"):
                            # Comment; do nothing
                            pass
                        elif command == "setattr":
                            args = arg.split(None, 2)
                            if len(args) >= 3:
                                obj, name, value = args[:3]

                                try:
                                    value = eval(value)
                                except Exception as e:
                                    m = _("An error occurred in a timeline "
                                          "'setattr' command:\n\n{}").format(
                                              traceback.format_exc())
                                    show_error(m)
                                else:
                                    if obj in self.timeline_objects:
                                        obj = self.timeline_objects[obj]()
                                        if obj is not None:
                                            setattr(obj, name, value)
                                    elif obj == "__level__":
                                        setattr(self, name, value)
                        elif command == "call":
                            args = arg.split()
                            if len(args) >= 2:
                                obj, method = args[:2]
                                fa = [eval(s) for s in args[2:]]

                                if obj in self.timeline_objects:
                                    obj = self.timeline_objects[obj]()
                                    if obj is not None:
                                        getattr(obj, method, lambda: None)(*fa)
                                elif obj == "__level__":
                                    getattr(self, method, lambda: None)(*fa)
                        elif command == "dialog":
                            DialogBox(gui_handler, _(arg)).show()
                        elif command == "play_music":
                            self.music = arg
                            play_music(arg)
                        elif command == "timeline":
                            if self.timeline_name not in watched_timelines:
                                watched_timelines = watched_timelines[:]
                                watched_timelines.append(self.timeline_name)
                            self.load_timeline(arg)
                            break
                        elif command == "skip_to":
                            try:
                                arg = float(arg)
                            except ValueError:
                                pass
                            else:
                                self.timeline_skipto(arg)
                                break
                        elif command == "exec":
                            try:
                                exec(arg)
                            except Exception as e:
                                m = _("An error occurred in a timeline 'exec' "
                                      "command:\n\n{}").format(
                                          traceback.format_exc())
                                show_error(m)
                        elif command == "if":
                            try:
                                r = eval(arg)
                            except Exception as e:
                                m = _("An error occurred in a timeline 'if' "
                                      "statement:\n\n{}").format(
                                          traceback.format_exc())
                                show_error(m)
                                r = False
                            finally:
                                if not r:
                                    self.timeline[i] = []
                                    break
                        elif command == "if_watched":
                            if self.timeline_name not in watched_timelines:
                                self.timeline[i] = []
                                break
                        elif command == "if_not_watched":
                            if self.timeline_name in watched_timelines:
                                self.timeline[i] = []
                                break
                        elif command == "while":
                            try:
                                r = eval(arg)
                            except Exception as e:
                                m = _("An error occurred in a timeline "
                                      "'while' statement:\n\n{}").format(
                                          traceback.format_exc())
                                show_error(m)
                                r = False
                            finally:
                                if r:
                                    cur_timeline = self.timeline[i][:]
                                    while_command = "while {}".format(arg)
                                    self.timeline[i].insert(0, while_command)
                                    t_keys.insert(0, i)
                                    self.timeline[i - 1] = cur_timeline
                                    self.timeline[i] = loop_timeline
                                    i -= 1
                                    self.timeline_step -= 1
                                else:
                                    self.timeline[i] = []
                                    break
                else:
                    del self.timeline[i]
            else:
                break
        else:
            if (self.timeline_name and
                    self.timeline_name not in watched_timelines):
                watched_timelines = watched_timelines[:]
                watched_timelines.append(self.timeline_name)
                self.timeline_name = ""

        self.timeline_step += delta_mult

    def event_paused_step(self, time_passed, delta_mult):
        # Handle lighting
        for view in self.views:
            for obj in self.get_objects_at(
                    view.x - LIGHT_RANGE, view.y - LIGHT_RANGE,
                    view.width + LIGHT_RANGE*2,
                    view.height + LIGHT_RANGE*2):
                if isinstance(obj, InteractiveObject):
                    if not self.disable_lights:
                        obj.project_light()

        self.show_hud()

    def event_alarm(self, alarm_id):
        if alarm_id == "shake_down":
            self.shake_queue -= 1
            for view in self.views:
                view.yport += SHAKE_AMOUNT
            self.alarms["shake_up"] = SHAKE_FRAME_TIME
        elif alarm_id == "shake_up":
            for view in self.views:
                view.yport -= SHAKE_AMOUNT
            if self.shake_queue:
                self.alarms["shake_down"] = SHAKE_FRAME_TIME
        elif alarm_id == "death":
            self.die()

    @classmethod
    def load(cls, fname, show_prompt=False):
        if show_prompt:
            text = _("Loading data...")
            if sge.game.current_room is not None:
                x = sge.game.width / 2
                y = sge.game.height / 2
                w = font.get_width(text) + 32
                h = font.get_height(text) + 32
                sge.game.project_rectangle(x - w/2, y - h/2, w, h,
                                           fill=sge.gfx.Color("black"))
                sge.game.project_text(font, text, x, y,
                                      color=sge.gfx.Color("white"),
                                      halign="center", valign="middle")
                sge.game.refresh()
            else:
                print(_("Loading \"{}\"...").format(fname))

        try:
            r = xsge_tiled.load(os.path.join(hlib.datadir, "rooms", fname), cls=cls,
                                types=TYPES)
        except Exception as e:
            m = _("An error occurred when trying to load the level:\n\n"
                  "{}").format(traceback.format_exc())
            show_error(m)
            r = None
        else:
            r.fname = fname

        return r


class SpecialScreen(Level):

    def event_room_start(self):
        super().event_room_start()
        if player is not None:
            player.destroy()


class TitleScreen(SpecialScreen):

    def show_hud(self):
        pass

    def event_room_start(self):
        super().event_room_start()
        MainMenu.create()

    def event_room_resume(self):
        super().event_room_resume()
        MainMenu.create()

    def event_key_press(self, key, char):
        pass


class CreditsScreen(SpecialScreen):

    def event_room_start(self):
        super().event_room_start()

        with open(os.path.join(hlib.datadir, "credits.json"), 'r') as f:
            sections = json.load(f)

        logo_section = sge.dsp.Object.create(self.width / 2, self.height,
                                             sprite=logo_sprite,
                                             tangible=False)
        self.sections = [logo_section]
        for section in sections:
            if "title" in section:
                head_sprite = sge.gfx.Sprite.from_text(
                    font_big, section["title"], width=self.width,
                    color=sge.gfx.Color("white"), halign="center")
                x = self.width / 2
                y = self.sections[-1].bbox_bottom + font_big.size*3
                head_section = sge.dsp.Object.create(x, y, sprite=head_sprite,
                                                     tangible=False)
                self.sections.append(head_section)

            if "lines" in section:
                for line in section["lines"]:
                    list_sprite = sge.gfx.Sprite.from_text(
                        font, line, width=self.width - 2*hlib.TILE_SIZE,
                        color=sge.gfx.Color("white"), halign="center")
                    x = self.width / 2
                    y = self.sections[-1].bbox_bottom + font.size
                    list_section = sge.dsp.Object.create(
                        x, y, sprite=list_sprite, tangible=False)
                    self.sections.append(list_section)

        for obj in self.sections:
            obj.yvelocity = -0.2

    def event_step(self, time_passed, delta_mult):
        if self.sections[0].yvelocity > 0 and self.sections[0].y > self.height:
            for obj in self.sections:
                obj.yvelocity = 0

        if self.sections[-1].bbox_bottom < 0 and "end" not in self.alarms:
            sge.snd.Music.stop(fade_time=3000)
            self.alarms["end"] = 3.5 * hlib.FPS

    def event_alarm(self, alarm_id):
        if alarm_id == "end":
            sge.game.start_room.start()

    def event_key_press(self, key, char):
        if key in itertools.chain.from_iterable(down_key):
            if "end" not in self.alarms:
                for obj in self.sections:
                    obj.yvelocity -= 0.1
        elif key in itertools.chain.from_iterable(up_key):
            if "end" not in self.alarms:
                for obj in self.sections:
                    obj.yvelocity += 0.1
        elif (key in itertools.chain.from_iterable(jump_key)
              or key in itertools.chain.from_iterable(shoot_key)
              or key in itertools.chain.from_iterable(pause_key)):
            sge.game.start_room.start()

    def event_joystick(self, js_name, js_id, input_type, input_id, value):
        js = (js_id, input_type, input_id)
        if value >= joystick_threshold:
            if js in itertools.chain.from_iterable(down_js):
                if "end" not in self.alarms:
                    for obj in self.sections:
                        obj.yvelocity -= 0.1
            elif js in itertools.chain.from_iterable(up_js):
                if "end" not in self.alarms:
                    for obj in self.sections:
                        obj.yvelocity += 0.1
            elif (js in itertools.chain.from_iterable(jump_js)
                  or js in itertools.chain.from_iterable(shoot_js)
                  or js in itertools.chain.from_iterable(pause_js)):
                sge.game.start_room.start()


class SolidLeft(xsge_physics.SolidLeft):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class SolidRight(xsge_physics.SolidRight):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class SolidTop(xsge_physics.SolidTop):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class SolidBottom(xsge_physics.SolidBottom):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class Solid(xsge_physics.Solid):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class SlopeTopLeft(xsge_physics.SlopeTopLeft):

    xsticky_top = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)

    def event_create(self):
        self.slope_xacceleration = -self.bbox_height / self.bbox_width


class SlopeTopRight(xsge_physics.SlopeTopRight):

    xsticky_top = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)

    def event_create(self):
        self.slope_xacceleration = self.bbox_height / self.bbox_width


class SlopeBottomLeft(xsge_physics.SlopeBottomLeft):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class SlopeBottomRight(xsge_physics.SlopeBottomRight):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class MovingPlatform(xsge_physics.SolidTop, xsge_physics.MobileWall):

    sticky_top = True

    def __init__(self, x, y, z=0, **kwargs):
        kwargs.setdefault("sprite", platform_sprite)
        super().__init__(x, y, z, **kwargs)
        self.path = None
        self.following = False

    def event_step(self, time_passed, delta_mult):
        super().event_step(time_passed, delta_mult)

        if self.path and not self.following:
            for other in self.collision(Player, y=self.y - 1):
                if self in other.get_bottom_touching_wall():
                    self.path.follow_start(self, self.path.path_speed,
                                           accel=self.path.path_accel,
                                           decel=self.path.path_decel,
                                           loop=self.path.path_loop)
                    break


class HurtLeft(SolidLeft):

    pass


class HurtRight(SolidRight):

    pass


class HurtTop(SolidTop):

    pass


class HurtBottom(SolidBottom):

    pass


class SpikeLeft(HurtLeft, xsge_physics.Solid):

    pass


class SpikeRight(HurtRight, xsge_physics.Solid):

    pass


class SpikeTop(HurtTop, xsge_physics.Solid):

    pass


class SpikeBottom(HurtBottom, xsge_physics.Solid):

    pass


class Death(sge.dsp.Object):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(*args, **kwargs)


class Player(xsge_physics.Collider):

    name = "Ian C."
    max_hp = PLAYER_MAX_HP
    max_speed = PLAYER_MAX_SPEED
    roll_max_speed = PLAYER_ROLL_MAX_SPEED
    acceleration = PLAYER_ACCELERATION
    roll_acceleration = PLAYER_ROLL_ACCELERATION
    air_acceleration = PLAYER_AIR_ACCELERATION
    friction = PLAYER_FRICTION
    roll_friction = PLAYER_ROLL_FRICTION
    air_friction = PLAYER_AIR_FRICTION
    jump_height = PLAYER_JUMP_HEIGHT
    gravity = GRAVITY
    fall_speed = PLAYER_FALL_SPEED
    slide_speed = PLAYER_SLIDE_SPEED
    roll_slide_speed = PLAYER_ROLL_SLIDE_SPEED
    roll_slope_acceleration = PLAYER_ROLL_SLOPE_ACCELERATION
    hitstun_time = PLAYER_HITSTUN
    can_move = True

    @property
    def slope_acceleration(self):
        if self.rolling:
            return self.roll_slope_acceleration
        else:
            return 0

    @slope_acceleration.setter
    def slope_acceleration(self, value):
        pass

    @property
    def hp(self):
        return self.__hp

    @hp.setter
    def hp(self, value):
        self.__hp = value

        while self.__hp > self.max_hp and self.etanks_used > 0:
            self.etanks_used -= 1
            self.__hp -= self.max_hp

        while self.__hp <= 0 and self.etanks_used < etanks:
            self.etanks_used += 1
            self.__hp += self.max_hp

        self.__hp = min(self.__hp, self.max_hp)

        if self.__hp > 0:
            new_w = healthbar_width * self.__hp / self.max_hp
            healthbar_front_sprite.width = new_w
        self.update_hud()

    @property
    def camera_target_x(self):
        guides = sge.collision.rectangle(self.x, self.y, 1, 1, CameraXGuide)
        if guides:
            return guides[0].x
        else:
            return (self.x - self.view.width/2
                    + self.xvelocity*CAMERA_OFFSET_FACTOR)

    @property
    def camera_target_y(self):
        guides = sge.collision.rectangle(self.x, self.y, 1, 1, CameraYGuide)
        if guides:
            self.camera_guided_y = True
            return guides[0].y
        else:
            self.camera_guided_y = False
            return self.y-self.view.height + CAMERA_TARGET_MARGIN_BOTTOM

    @property
    def aim_lock(self):
        return "aim_lock" in self.alarms

    @aim_lock.setter
    def aim_lock(self, value):
        if value:
            self.alarms["aim_lock"] = PLAYER_AIM_LOCK_TIME
        elif "aim_lock" in self.alarms:
            del self.alarms["aim_lock"]

    def __init__(self, x, y, z=0, sprite=None, visible=True, active=True,
                 checks_collisions=True, tangible=True, bbox_x=8, bbox_y=0,
                 bbox_width=16, bbox_height=16, regulate_origin=True,
                 collision_ellipse=False, collision_precise=False, xvelocity=0,
                 yvelocity=0, xacceleration=0, yacceleration=0,
                 xdeceleration=0, ydeceleration=0, image_index=0,
                 image_origin_x=None, image_origin_y=None, image_fps=None,
                 image_xscale=1, image_yscale=1, image_rotation=0,
                 image_alpha=255, image_blend=None, ID="player", player=0,
                 human=True, lose_on_death=True, view_frozen=False):
        self.ID = ID
        self.player = player
        self.human = human
        self.lose_on_death = lose_on_death
        self.view_frozen = view_frozen
        self.input_lock = False
        self.warp_dest = None

        self.hud_sprite = sge.gfx.Sprite(width=hlib.SCREEN_SIZE[0],
                                         height=hlib.SCREEN_SIZE[1])

        self.reset_input()
        self.etanks_used = 0
        self.hitstun = False
        self.invincible = False
        self.facing = 1
        self.has_jumped = False
        self.current_mode = None
        self.rolling = False
        self.aim_direction = None
        self.aim_direction_time = 0
        self.view = None
        self.__hp = self.max_hp
        healthbar_front_sprite.width = healthbar_width
        self.last_xr = None
        self.last_yr = None
        self.camera_guided_y = False

        super().__init__(
            x, y, z=z, sprite=sprite, visible=visible, active=active,
            checks_collisions=checks_collisions, tangible=tangible,
            bbox_x=bbox_x, bbox_y=bbox_y, bbox_width=bbox_width,
            bbox_height=bbox_height, regulate_origin=regulate_origin,
            collision_ellipse=collision_ellipse,
            collision_precise=collision_precise, xvelocity=xvelocity,
            yvelocity=yvelocity, xacceleration=xacceleration,
            yacceleration=yacceleration, xdeceleration=xdeceleration,
            ydeceleration=ydeceleration, image_index=image_index,
            image_origin_x=image_origin_x, image_origin_y=image_origin_y,
            image_fps=image_fps, image_xscale=image_xscale,
            image_yscale=image_yscale, image_rotation=image_rotation,
            image_alpha=image_alpha, image_blend=image_blend)

    def reset_input(self):
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.jump_pressed = False
        self.shoot_pressed = False
        self.aim_diag_pressed = False
        self.aim_up_pressed = False
        self.aim_down_pressed = False
        self.mode_pressed = False
        self.mode_reset_pressed = False

    def refresh_input(self):
        if self.input_lock or not self.human:
            return

        key_controls = [left_key, right_key, up_key, down_key, aim_diag_key,
                        jump_key, shoot_key, aim_up_key, aim_down_key,
                        mode_key, mode_reset_key]
        js_controls = [left_js, right_js, up_js, down_js, aim_diag_js,
                       jump_js, shoot_js, aim_up_js, aim_down_js, mode_js,
                       mode_reset_js]
        states = [0 for i in key_controls]

        for i in range(len(key_controls)):
            for choice in key_controls[i][self.player]:
                value = sge.keyboard.get_pressed(choice)
                states[i] = max(states[i], value)

        for i in range(len(js_controls)):
            for choice in js_controls[i][self.player]:
                j, t, c = choice
                value = min(sge.joystick.get_value(j, t, c), 1)
                if value >= joystick_threshold:
                    states[i] = max(states[i], value)

        (self.left_pressed, self.right_pressed, self.up_pressed,
         self.down_pressed, self.aim_diag_pressed, self.jump_pressed,
         self.shoot_pressed, self.aim_up_pressed, self.aim_down_pressed,
         self.mode_pressed, self.mode_reset_pressed) = states

    def press_up(self):
        if not self.aim_diag_pressed:
            warp_pad_objs = self.collision(WarpPad)
            if warp_pad_objs:
                warp_pad = warp_pad_objs[0]
                warp_pad.teleport(self)

    def press_down(self):
        pass

    def jump(self):
        if self.on_floor or self.was_on_floor:
            self.has_jumped = True
            self.yvelocity = get_jump_speed(self.jump_height, self.gravity)
            self.on_floor = []
            self.was_on_floor = []
            self.event_jump()

    def jump_release(self):
        if self.has_jumped and self.yvelocity < 0:
            self.has_jumped = False
            self.yvelocity /= 2

    def shoot(self):
        pass

    def shoot_release(self):
        pass

    def mode(self):
        all_modes = [None, "compress"]
        if self.current_mode in all_modes:
            i = all_modes.index(self.current_mode)
            while True:
                i += 1

                if i >= len(all_modes):
                    self.current_mode = None
                    break
                elif (all_modes[i] == "compress" and
                        "atomic_compressor" in progress_flags):
                    self.current_mode = all_modes[i]
                    break
        else:
            self.current_mode = None

        self.update_hud()
        play_sound(type_sound)

    def mode_reset(self):
        self.current_mode = None
        self.update_hud()
        play_sound(cancel_sound)

    def hurt(self, damage=1, touching=False):
        if not self.hitstun and not self.invincible:
            play_sound(hurt_sound, self.x, self.y)
            if not GOD:
                self.hp -= damage

            if self.hp <= 0:
                self.kill()
            else:
                self.hitstun = True
                self.image_alpha = 128
                self.alarms["hitstun"] = self.hitstun_time

    def kill(self):
        if self.lose_on_death:
            sge.snd.Music.clear_queue()
            sge.snd.Music.stop()
            sge.game.current_room.alarms["death"] = DEATH_TIME

        play_sound(death_sound, self.x, self.y)
        self.destroy()

    def refresh(self):
        self.hp = self.max_hp
        self.etanks_used = 0
        self.update_hud()

    def warp_in(self):
        self.input_lock = True
        self.alarms["input_lock"] = WARP_TIME
        self.reset_input()
        self.xvelocity = 0
        self.yvelocity = 0

    def warp_out(self):
        self.input_lock = True
        self.alarms["warp_out"] = WARP_TIME
        self.reset_input()
        self.xvelocity = 0
        self.yvelocity = 0

    def update_hud(self):
        self.hud_sprite.draw_clear()
        if not hlib.no_hud:
            start_x = 8
            start_y = 8
            x = start_x
            y = start_y
            self.hud_sprite.draw_sprite(healthbar_back_sprite, 0, x, y)
            if self.hp > 0:
                self.hud_sprite.draw_sprite(healthbar_front_sprite, 0, x, y)

            y += 8
            w = etank_empty_sprite.width
            h = etank_empty_sprite.height
            for i in range(etanks):
                if x + w >= start_x + healthbar_width:
                    x = start_x
                    y += h

                if i < etanks - self.etanks_used:
                    self.hud_sprite.draw_sprite(etank_full_sprite, 0, x, y)
                else:
                    self.hud_sprite.draw_sprite(etank_empty_sprite, 0, x, y)

                x += w

            # Mode image
            x = start_x
            y += 12
            if self.current_mode == "compress":
                self.hud_sprite.draw_sprite(atomic_compressor_sprite, 0, x, y)

            if "map" in progress_flags:
                w = 7
                h = 5

                if sge.game.current_room.fname in map_rooms:
                    rm_x, rm_y = map_rooms[sge.game.current_room.fname]
                    pl_x = rm_x + get_xregion(self.x)
                    pl_y = rm_y + get_yregion(self.y)
                    x = pl_x - w // 2
                    y = pl_y - h // 2
                else:
                    x = 0
                    y = 0
                    pl_x = None
                    pl_y = None

                map_s = draw_map(x, y, w, h, pl_x, pl_y)
                c = sge.gfx.Color((255, 255, 255, 192))
                map_s.draw_rectangle(0, 0, map_s.width, map_s.height, fill=c,
                                     blend_mode=sge.BLEND_RGBA_MULTIPLY)

                x = hlib.SCREEN_SIZE[0] - start_x - w*MAP_CELL_WIDTH
                y = start_y
                self.hud_sprite.draw_sprite(map_s, 0, x, y)
                self.hud_sprite.draw_rectangle(x, y, map_s.width, map_s.height,
                                               outline=sge.gfx.Color("white"))
                

    def show_hud(self):
        if not hlib.no_hud:
            sge.game.project_sprite(self.hud_sprite, 0, 0, 0)

            if not self.human:
                room = sge.game.current_room
                if (room.timeline_skip_target is not None and
                        room.timeline_step < room.timeline_skip_target):
                    room.status_text = _("Press the Menu button to skip...")
                else:
                    room.status_text = _("Cinematic mode enabled")

    def set_image(self):
        pass

    def init_position(self):
        self.last_x = self.x
        self.last_y = self.y
        self.on_slope = self.get_bottom_touching_slope()
        self.on_floor = self.get_bottom_touching_wall() + self.on_slope
        self.was_on_floor = self.on_floor

        self.view.x = self.camera_target_x
        self.view.y = self.camera_target_y

    def event_create(self):
        self.z = sge.game.current_room.player_z
        sge.game.current_room.add_timeline_object(self)
        self.view = sge.game.current_room.views[self.player]
        for obj in sge.game.current_room.objects:
            if isinstance(obj, SpawnPoint) and obj.spawn_id == spawn_point:
                obj.spawn(self)
                break
        self.init_position()
        self.update_hud()

    def event_begin_step(self, time_passed, delta_mult):
        self.refresh_input()

        h_control = bool(self.right_pressed) - bool(self.left_pressed)
        v_control = bool(self.down_pressed) - bool(self.up_pressed)
        current_h_movement = (self.xvelocity > 0) - (self.xvelocity < 0)

        if not self.aim_lock:
            prev_aim_direction = self.aim_direction

            if "shooting" in self.alarms:
                self.aim_direction = 0
            else:
                self.aim_direction = None

            if v_control:
                if self.aim_diag_pressed or (h_control and metroid_controls):
                    self.aim_direction = 1 * -v_control
                else:
                    self.aim_direction = 2 * -v_control
            elif metroid_controls and self.aim_diag_pressed:
                if prev_aim_direction is not None and prev_aim_direction < 0:
                    self.aim_direction = -1
                else:
                    self.aim_direction = 1

            if self.aim_up_pressed and self.aim_down_pressed:
                self.aim_direction = 2
            elif self.aim_up_pressed:
                self.aim_direction = 1
            elif self.aim_down_pressed:
                self.aim_direction = -1

            if self.aim_direction == prev_aim_direction:
                self.aim_direction_time += 1
            else:
                self.aim_direction_time = 0

        self.xacceleration = 0
        self.yacceleration = 0
        self.xdeceleration = 0

        if h_control:
            if not self.can_move:
                target_speed = 0
            else:
                h_factor = abs(self.right_pressed - self.left_pressed)
                target_speed = min(h_factor * self.max_speed, self.max_speed)

            if (abs(self.xvelocity) < target_speed or
                    (self.xvelocity > 0 and h_control < 0) or
                    (self.xvelocity < 0 and h_control > 0)):
                if self.on_floor or self.was_on_floor:
                    if self.rolling:
                        self.xacceleration = self.roll_acceleration * h_control
                    else:
                        self.xacceleration = self.acceleration * h_control
                else:
                    self.xacceleration = self.air_acceleration * h_control
            else:
                if self.on_floor or self.was_on_floor:
                    if self.rolling:
                        dc = self.roll_friction
                    else:
                        dc = self.friction
                else:
                    dc = self.air_friction

                if abs(self.xvelocity) - dc*delta_mult > target_speed:
                    self.xdeceleration = dc
                else:
                    self.xvelocity = target_speed * current_h_movement

        if current_h_movement and h_control != current_h_movement:
            if self.on_floor or self.was_on_floor:
                if self.rolling:
                    self.xdeceleration = self.roll_friction
                else:
                    self.xdeceleration = self.friction
            else:
                self.xdeceleration = self.air_friction

        if not self.on_floor and not self.was_on_floor:
            if self.yvelocity < self.fall_speed:
                self.yacceleration = self.gravity
            else:
                self.yvelocity = self.fall_speed
        elif self.on_slope:
            if self.rolling:
                self.yvelocity = (self.roll_slide_speed
                                  * (self.on_slope[0].bbox_height
                                     / self.on_slope[0].bbox_width))
            elif self.xvelocity:
                self.yvelocity = (self.slide_speed
                                  * (self.on_slope[0].bbox_height
                                     / self.on_slope[0].bbox_width))
            else:
                self.yvelocity = 0

    def event_step(self, time_passed, delta_mult):
        global map_revealed
        global map_explored

        on_floor = self.get_bottom_touching_wall()
        self.on_slope = self.get_bottom_touching_slope() if not on_floor else []
        self.was_on_floor = self.on_floor
        self.on_floor = on_floor + self.on_slope
        h_control = bool(self.right_pressed) - bool(self.left_pressed)
        v_control = bool(self.down_pressed) - bool(self.up_pressed)

        for block in self.on_floor:
            if block in self.was_on_floor and isinstance(block, HurtTop):
                self.hurt()

        # Set image
        self.set_image()

        # Move view
        if self.view is not None and not self.view_frozen:
            view_target_x = self.camera_target_x
            if abs(view_target_x - self.view.x) > 0.5:
                camera_xvel = ((view_target_x-self.view.x)
                               * CAMERA_HSPEED_FACTOR * delta_mult)
                if abs(self.xvelocity) > CAMERA_STOPPED_THRESHOLD:
                    self.view.x += camera_xvel
                else:
                    xvel_max = CAMERA_STOPPED_HSPEED_MAX * delta_mult
                    self.view.x += max(-xvel_max, min(camera_xvel, xvel_max))
                        
            else:
                self.view.x = view_target_x

            view_min_y = self.y - self.view.height + CAMERA_MARGIN_BOTTOM
            view_max_y = self.y - CAMERA_MARGIN_TOP

            view_target_y = self.camera_target_y
            if abs(view_target_y - self.view.y) > 0.5:
                self.view.y += ((view_target_y-self.view.y)
                                * CAMERA_VSPEED_FACTOR * delta_mult)
            else:
                self.view.y = view_target_y

            if not self.camera_guided_y:
                if self.view.y < view_min_y:
                    self.view.y = view_min_y
                elif self.view.y > view_max_y:
                    self.view.y = view_max_y

        self.last_x = self.x
        self.last_y = self.y

        if sge.game.current_room.fname in map_rooms:
            xr, yr = map_rooms[sge.game.current_room.fname]
            xr += get_xregion(self.x)
            yr += get_yregion(self.y)
            if xr != self.last_xr or yr != self.last_yr:
                pos = (xr, yr)
                if pos not in map_explored:
                    map_explored = map_explored[:]
                    map_explored.append(pos)
                if pos not in map_revealed:
                    map_revealed = map_revealed[:]
                    map_revealed.append(pos)
                self.update_hud()
            self.last_xr = xr
            self.last_yr = yr

        self.show_hud()

    def event_paused_step(self, time_passed, delta_mult):
        self.show_hud()

    def event_alarm(self, alarm_id):
        if alarm_id == "hitstun":
            self.hitstun = False
            self.image_alpha = 255
        elif alarm_id == "input_lock":
            self.input_lock = False
            self.refresh_input()
        elif alarm_id == "warp_out":
            if self.warp_dest:
                warp(self.warp_dest)

    def event_key_press(self, key, char):
        if self.human and not self.input_lock:
            if key in up_key[self.player] and not self.up_pressed:
                self.press_up()
            if key in down_key[self.player] and not self.down_pressed:
                self.press_down()
            if key in jump_key[self.player] and not self.jump_pressed:
                self.jump()
            if key in shoot_key[self.player] and not self.shoot_pressed:
                self.shoot()
            if key in mode_key[self.player] and not self.mode_pressed:
                self.mode()
            if (key in mode_reset_key[self.player] and
                    not self.mode_reset_pressed):
                self.mode_reset()
            if key in map_key[self.player]:
                if "map" in progress_flags:
                    play_sound(select_sound)
                    MapDialog(self.last_xr, self.last_yr).show()

        if not isinstance(sge.game.current_room, SpecialScreen):
            if key == "escape" or key in pause_key[self.player]:
                sge.game.current_room.pause(player_x=self.last_xr,
                                            player_y=self.last_yr)

    def event_key_release(self, key):
        if self.human and not self.input_lock:
            if key in jump_key[self.player]:
                self.jump_release()
            if key in shoot_key[self.player]:
                self.shoot_release()
            elif key in up_key[self.player] or key in down_key[self.player]:
                self.aim_lock = False

    def event_joystick(self, js_name, js_id, input_type, input_id, value):
        js = (js_id, input_type, input_id)
        if self.human and not self.input_lock:
            if value >= joystick_threshold:
                if js in up_js[self.player] and not self.up_pressed:
                    self.press_up()
                if js in down_js[self.player] and not self.down_pressed:
                    self.press_down()
                if js in jump_js[self.player] and not self.jump_pressed:
                    self.jump()
                if js in shoot_js[self.player] and not self.shoot_pressed:
                    self.shoot()
                if js in mode_js[self.player] and not self.mode_pressed:
                    self.mode()
                if (js in mode_reset_js[self.player] and
                        not self.mode_reset_pressed):
                    self.mode_reset()
                if js in map_js[self.player]:
                    if "map" in progress_flags:
                        play_sound(select_sound)
                        MapDialog(self.last_xr, self.last_yr).show()
            else:
                if js in jump_js[self.player]:
                    self.jump_release()
                if js in shoot_js[self.player]:
                    self.shoot_release()

        if not isinstance(sge.game.current_room, SpecialScreen):
            if value >= joystick_threshold and js in pause_js[self.player]:
                sge.game.current_room.pause(player_x=self.last_xr,
                                            player_y=self.last_yr)

    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, InteractiveObject):
            other.touch(self)

    def event_physics_collision_left(self, other, move_loss):
        for block in self.get_left_touching_wall():
            if isinstance(block, HurtRight):
                self.hurt()

        if isinstance(other, xsge_physics.SolidRight):
            self.xvelocity = max(self.xvelocity, 0)

    def event_physics_collision_right(self, other, move_loss):
        for block in self.get_right_touching_wall():
            if isinstance(block, HurtLeft):
                self.hurt()

        if isinstance(other, xsge_physics.SolidLeft):
            self.xvelocity = min(self.xvelocity, 0)

    def event_physics_collision_top(self, other, move_loss):
        top_touching = self.get_top_touching_wall()

        tmv = 0
        for i in range(CEILING_LAX):
            if (not self.get_left_touching_wall()
                    and not self.get_left_touching_slope()):
                self.x -= 1
                tmv -= 1
                if (not self.get_top_touching_wall()
                        and not self.get_top_touching_slope()):
                    self.move_y(-move_loss)
                    break
        else:
            self.x -= tmv
            tmv = 0
            for i in range(CEILING_LAX):
                if (not self.get_left_touching_wall()
                        and not self.get_left_touching_slope()):
                    self.x += 1
                    tmv += 1
                    if (not self.get_top_touching_wall()
                            and not self.get_top_touching_slope()):
                        self.move_y(-move_loss)
                        break
            else:
                self.x -= tmv
                tmv = 0
                self.yvelocity = max(self.yvelocity, 0)

        for block in top_touching:
            if isinstance(block, HurtBottom):
                self.hurt()

    def event_physics_collision_bottom(self, other, move_loss):
        self.has_jumped = False

        for block in self.get_bottom_touching_wall():
            if isinstance(block, HurtTop):
                self.hurt()

        if isinstance(other, xsge_physics.SolidTop):
            self.yvelocity = min(self.yvelocity, 0)
        elif isinstance(other, (xsge_physics.SlopeTopLeft,
                                xsge_physics.SlopeTopRight)):
            ss = self.roll_slide_speed if self.rolling else self.slide_speed
            self.yvelocity = min(ss * (other.bbox_height / other.bbox_width),
                                 self.yvelocity)

    def event_jump(self):
        pass


class Anneroy(Player):

    name = "Anneroy"

    @property
    def can_move(self):
        if self.crouching:
            h_control = bool(self.right_pressed) - bool(self.left_pressed)
            if h_control != self.facing:
                self.alarms["autostand_lock"] = 10

            if "autostand_lock" not in self.alarms:
                self.press_up()

        return not self.crouching

    def __init__(self, *args, **kwargs):
        kwargs["bbox_x"] = ANNEROY_BBOX_X
        kwargs["bbox_width"] = ANNEROY_BBOX_WIDTH
        kwargs["bbox_y"] = ANNEROY_STAND_BBOX_Y
        kwargs["bbox_height"] = ANNEROY_STAND_BBOX_HEIGHT
        super().__init__(*args, **kwargs)

        self.torso = None
        self.hedgehog_spikes = None
        self.fixed_sprite = False
        self.crouching = False
        self.ball = False
        self.walljumping = False
        self.wall_direction = 0
        self.bouncing = False
        self.hedgehog = False
        self.hedgehog_autocancel = False
        self.last_aim_direction = 0

    def get_up_obstructed(self, x, y, w, h, lax=0):
        def _get_up_obstructed(self=self, x=x, y=y, w=w, h=h):
            for other in sge.collision.rectangle(self.x + x, self.y + y, w, h):
                if isinstance(other, xsge_physics.SolidBottom):
                    if not self.collision(other):
                        return True
                elif isinstance(other, xsge_physics.SlopeBottomLeft):
                    if self.bbox_top >= other.get_slope_y(self.bbox_right):
                        return True
                elif isinstance(other, xsge_physics.SlopeBottomRight):
                    if self.bbox_top >= other.get_slope_y(self.bbox_left):
                        return True

            return False

        rv = _get_up_obstructed()

        if rv:
            xstart = self.x

            for i in range(lax):
                self.move_x(-1)
                rv = _get_up_obstructed()
                if not rv:
                    break
            else:
                self.move_x(xstart - self.x)

                for i in range(lax):
                    self.move_x(1)
                    rv = _get_up_obstructed()
                    if not rv:
                        break
                else:
                    self.move_x(xstart - self.x)

        return rv

    def press_up(self):
        if self.ball:
            if self.get_up_obstructed(
                    ANNEROY_BBOX_X, ANNEROY_CROUCH_BBOX_Y,
                    ANNEROY_BBOX_WIDTH, ANNEROY_CROUCH_BBOX_HEIGHT,
                    ANNEROY_DECOMPRESS_LAX):
                self.reset_image()
                self.sprite = anneroy_decompress_fail_sprite
                self.image_index = 0
                self.image_speed = None
                self.torso.visible = False
                self.fixed_sprite = "decompress_fail"
            else:
                if self.fixed_sprite != "compress":
                    self.reset_image()
                    self.sprite = anneroy_compress_sprite
                    self.image_index = anneroy_compress_sprite.frames - 1
                self.image_speed = -anneroy_compress_sprite.speed
                self.torso.visible = False
                self.fixed_sprite = "compress"

                self.ball = False
                self.hedgehog = False
                self.rolling = False
                self.aim_lock = True

                if "fixed_sprite" in self.alarms:
                    del self.alarms["fixed_sprite"]
                if "hedgehog_retract" in self.alarms:
                    del self.alarms["hedgehog_retract"]
                if "hedgehog_extend" in self.alarms:
                    del self.alarms["hedgehog_extend"]
                if "hedgehog_extend2" in self.alarms:
                    del self.alarms["hedgehog_extend2"]

                self.max_speed = self.__class__.max_speed
                if self.on_floor:
                    self.crouching = True
                    self.bbox_y = ANNEROY_CROUCH_BBOX_Y
                    self.bbox_height = ANNEROY_CROUCH_BBOX_HEIGHT
                else:
                    self.bbox_y = ANNEROY_STAND_BBOX_Y
                    self.bbox_height = ANNEROY_STAND_BBOX_HEIGHT
        elif self.crouching:
            if not self.aim_diag_pressed:
                for other in sge.collision.rectangle(
                        self.x + ANNEROY_BBOX_X, self.y + ANNEROY_STAND_BBOX_Y,
                        ANNEROY_BBOX_WIDTH, ANNEROY_STAND_BBOX_HEIGHT):
                    if isinstance(other, (xsge_physics.SolidBottom,
                                          xsge_physics.SlopeBottomLeft,
                                          xsge_physics.SlopeBottomRight)):
                        if not self.collision(other):
                            break
                else:
                    if self.on_floor:
                        if self.fixed_sprite != "crouch":
                            self.reset_image()
                            self.sprite = anneroy_legs_crouch_sprite
                            self.image_index = anneroy_legs_crouch_sprite.frames - 1
                        self.image_speed = -anneroy_legs_crouch_sprite.speed
                        self.fixed_sprite = "crouch"

                    self.crouching = False
                    self.bbox_y = ANNEROY_STAND_BBOX_Y
                    self.bbox_height = ANNEROY_STAND_BBOX_HEIGHT
                    self.aim_lock = True
        else:
            super().press_up()

    def press_down(self):
        if not self.aim_diag_pressed:
            h_control = bool(self.right_pressed) - bool(self.left_pressed)
            if self.on_floor and self.was_on_floor:
                if self.ball:
                    # Do nothing
                    pass
                elif self.crouching:
                    self.compress()
                else:
                    if not h_control:
                        if self.fixed_sprite != "crouch":
                            self.reset_image()
                            self.sprite = anneroy_legs_crouch_sprite
                            self.image_index = 0
                        self.image_speed = anneroy_legs_crouch_sprite.speed
                        self.fixed_sprite = "crouch"
                        self.crouching = True
                        self.bbox_y = ANNEROY_CROUCH_BBOX_Y
                        self.bbox_height = ANNEROY_CROUCH_BBOX_HEIGHT
                        self.aim_lock = True
                    else:
                        if "compress_pressed" in self.alarms:
                            self.compress()
                            del self.alarms["compress_pressed"]
                        else:
                            self.alarms["compress_pressed"] = DOUBLETAP_TIME
            else:
                if not self.ball:
                    if "compress_pressed" in self.alarms:
                        self.compress()
                        del self.alarms["compress_pressed"]
                    else:
                        self.alarms["compress_pressed"] = DOUBLETAP_TIME

    def jump(self):
        if self.crouching:
            self.press_up()

        if not self.crouching and not self.ball and not self.walljumping:
            if (not self.on_floor and not self.was_on_floor and
                    "monkey_boots" in progress_flags):
                if self.facing > 0 and self.get_right_touching_wall():
                    self.reset_image()
                    self.sprite = anneroy_wall_right_sprite
                    self.image_index = 0
                    self.image_speed = anneroy_wall_right_sprite.speed
                    self.image_xscale = abs(self.image_xscale)
                    self.fixed_sprite = "wall"
                    self.walljumping = True
                    self.wall_direction = 1
                    self.has_jumped = False
                    if "fixed_sprite" in self.alarms:
                        del self.alarms["fixed_sprite"]
                    self.torso.visible = False
                    self.input_lock = True
                    self.xvelocity = 0
                    self.yvelocity = 0
                    self.gravity = 0
                elif self.facing < 0 and self.get_left_touching_wall():
                    self.reset_image()
                    self.sprite = anneroy_wall_left_sprite
                    self.image_index = 0
                    self.image_speed = anneroy_wall_left_sprite.speed
                    self.image_xscale = abs(self.image_xscale)
                    self.fixed_sprite = "wall"
                    self.walljumping = True
                    self.wall_direction = -1
                    self.has_jumped = False
                    if "fixed_sprite" in self.alarms:
                        del self.alarms["fixed_sprite"]
                    self.torso.visible = False
                    self.input_lock = True
                    self.xvelocity = 0
                    self.yvelocity = 0
                    self.gravity = 0
            else:
                super().jump()

    def retract_spikes(self):
        self.hedgehog = False
        self.sprite = anneroy_hedgehog_start_sprite
        self.fixed_sprite = "hedgehog"
        self.alarms["fixed_sprite"] = ANNEROY_HEDGEHOG_FRAME_TIME
        self.alarms["hedgehog_lock"] = ANNEROY_HEDGEHOG_FRAME_TIME
        self.rolling = True
        self.max_speed = self.__class__.max_speed

    def recoil(self, direction):
        direction = math.radians((direction+180) % 360)

        diff = ANNEROY_XRECOIL * math.cos(direction)
        if diff > 0 and self.xvelocity < ANNEROY_XRECOIL_MAX:
            self.xvelocity += diff
            if self.xvelocity > ANNEROY_XRECOIL_MAX:
                self.xvelocity = ANNEROY_XRECOIL_MAX
        elif diff < 0 and self.xvelocity > -ANNEROY_XRECOIL_MAX:
            self.xvelocity += diff
            if self.xvelocity < -ANNEROY_XRECOIL_MAX:
                self.xvelocity = -ANNEROY_XRECOIL_MAX

        diff = ANNEROY_YRECOIL * math.sin(direction)
        if diff > 0 and self.yvelocity < ANNEROY_YRECOIL_MAX:
            self.yvelocity += diff
            if self.yvelocity > ANNEROY_YRECOIL_MAX:
                self.yvelocity = ANNEROY_YRECOIL_MAX
        elif diff < 0 and self.yvelocity > -ANNEROY_YRECOIL_MAX:
            self.yvelocity += diff
            if self.yvelocity < -ANNEROY_YRECOIL_MAX:
                self.yvelocity = -ANNEROY_YRECOIL_MAX

    def shoot_default(self):
        if "shoot_lock" in self.alarms:
            return

        if "life_orb" not in progress_flags:
            if self.aim_direction is None:
                self.aim_direction = 0
            self.alarms["shooting"] = 30
            self.alarms["shoot_lock"] = 60
            self.last_aim_direction = self.aim_direction

            play_sound(cancel_sound, self.image_xcenter, self.image_ycenter)

            return

        if self.ball:
            if ("hedgehog_hormone" in progress_flags and not self.hedgehog
                    and "hedgehog_lock" not in self.alarms):
                self.hedgehog = True
                self.sprite = anneroy_hedgehog_start_sprite

                if self.fixed_sprite:
                    self.image_speed = (abs(self.xvelocity) *
                                        ANNEROY_BALL_FRAMES_PER_PIXEL)

                self.fixed_sprite = "hedgehog"
                self.alarms["hedgehog_extend"] = ANNEROY_HEDGEHOG_FRAME_TIME
                play_sound(hedgehog_spikes_sound, self.image_xcenter,
                           self.image_ycenter)
                self.rolling = False

                if "sloth_ball" in progress_flags:
                    self.hedgehog_autocancel = False
                    self.max_speed = ANNEROY_SLOTH_MAX_SPEED
                else:
                    self.hedgehog_autocancel = True
                    self.max_speed = 0
        else:
            if self.aim_direction is None:
                self.aim_direction = 0
            self.alarms["shooting"] = 30
            apct = min(1, artifacts / max(1, num_artifacts))
            self.alarms["shoot_lock"] = 30 - 26*apct
            self.last_aim_direction = self.aim_direction

            x = 0
            y = 0
            xv = 0
            yv = 0
            image_rotation = 0

            if self.facing > 0:
                if self.aim_direction == 0:
                    x = 25
                    y = -4
                    xv = ANNEROY_BULLET_SPEED
                    image_rotation = 0
                elif self.aim_direction == 1:
                    x = 22
                    y = -27
                    xv = ANNEROY_BULLET_DSPEED
                    yv = -ANNEROY_BULLET_DSPEED
                    image_rotation = 315
                elif self.aim_direction == 2:
                    x = 6
                    y = -31
                    yv = -ANNEROY_BULLET_SPEED
                    image_rotation = 270
                elif self.aim_direction == -1:
                    x = 20
                    y = 9
                    xv = ANNEROY_BULLET_DSPEED
                    yv = ANNEROY_BULLET_DSPEED
                    image_rotation = 45
                elif self.aim_direction == -2:
                    x = 10
                    y = 21
                    yv = ANNEROY_BULLET_SPEED
                    image_rotation = 90
            else:
                if self.aim_direction == 0:
                    x = -25
                    y = -4
                    xv = -ANNEROY_BULLET_SPEED
                    image_rotation = 180
                elif self.aim_direction == 1:
                    x = -22
                    y = -28
                    xv = -ANNEROY_BULLET_DSPEED
                    yv = -ANNEROY_BULLET_DSPEED
                    image_rotation = 225
                elif self.aim_direction == 2:
                    x = -5
                    y = -31
                    yv = -ANNEROY_BULLET_SPEED
                    image_rotation = 270
                elif self.aim_direction == -1:
                    x = -19
                    y = 9
                    xv = -ANNEROY_BULLET_DSPEED
                    yv = ANNEROY_BULLET_DSPEED
                    image_rotation = 135
                elif self.aim_direction == -2:
                    x = -8
                    y = 21
                    yv = ANNEROY_BULLET_SPEED
                    image_rotation = 90

            self.recoil(image_rotation)

            if x:
                m = y / x
            else:
                m = None

            xdest = self.torso.x + x
            ydest = self.torso.y + y
            guide = xsge_physics.Collider.create(
                self.torso.x, self.torso.y, sprite=anneroy_bullet_sprite)
            if self.facing > 0:
                guide.bbox_right = self.bbox_right
            else:
                guide.bbox_left = self.bbox_left
            if self.aim_direction < 0:
                guide.bbox_bottom = self.bbox_bottom
            else:
                guide.bbox_top = self.bbox_top
            x += self.torso.x - guide.x
            y += self.torso.y - guide.y
            xsteps = int(abs(x) / guide.bbox_width)
            ysteps = int(abs(y) / guide.bbox_height)
            xfinal = math.copysign(abs(x) - xsteps * guide.bbox_width, x)
            yfinal = math.copysign(abs(y) - ysteps * guide.bbox_height, y)
            for i in range(xsteps):
                guide.move_x(math.copysign(guide.bbox_width, x))
            for i in range(ysteps):
                guide.move_y(math.copysign(guide.bbox_height, y))
            guide.move_x(xfinal)
            guide.move_y(yfinal)

            if abs(self.aim_direction) == 1 and m:
                target_x = self.torso.x + x
                target_y = self.torso.y + y
                xdiff = guide.x - self.torso.x
                ydiff = guide.y - self.torso.y
                if abs(guide.x - target_x) >= 1:
                    guide.y = self.torso.y + m*xdiff
                elif abs(guide.y - target_y) >= 1:
                    guide.x = self.torso.x + ydiff/m

            bs = AnneroyBullet.create(
                guide.x, guide.y, self.z - 0.2, sprite=anneroy_bullet_sprite,
                xvelocity=xv, yvelocity=yv, regulate_origin=True,
                image_xscale=abs(self.image_xscale),
                image_yscale=self.image_yscale, image_rotation=image_rotation,
                image_blend=self.image_blend)

            guide.destroy()

            Smoke.create(
                xdest, ydest, self.torso.z, sprite=anneroy_bullet_dust_sprite,
                #xvelocity=self.xvelocity, yvelocity=self.yvelocity,
                regulate_origin=True, image_xscale=abs(self.image_xscale),
                image_yscale=self.image_yscale, image_rotation=image_rotation,
                image_blend=self.image_blend)
            play_sound(shoot_sound, xdest, ydest)

    def shoot(self):
        if self.current_mode == "compress":
            if not self.shoot_pressed:
                if self.ball:
                    self.shoot_default()
                else:
                    self.compress()
        else:
            self.shoot_default()

    def shoot_release(self):
        if self.hedgehog and not self.hedgehog_autocancel:
            if self.fixed_sprite == "hedgehog":
                self.hedgehog_autocancel = True
            elif "hedgehog_lock" not in self.alarms:
                self.retract_spikes()

    def compress(self):
        if "atomic_compressor" in progress_flags and not self.shoot_pressed:
            if self.fixed_sprite != "compress":
                self.reset_image()
                self.sprite = anneroy_compress_sprite
                self.image_index = 0
            self.image_speed = anneroy_compress_sprite.speed
            self.fixed_sprite = "compress"
            self.torso.visible = False
            self.crouching = False
            self.ball = True
            self.rolling = True
            self.bouncing = False
            self.hedgehog = False
            self.max_speed = self.__class__.max_speed
            self.bbox_y = ANNEROY_BALL_BBOX_Y
            self.bbox_height = ANNEROY_BALL_BBOX_HEIGHT

    def hurt(self, damage=1, touching=False):
        if (not touching) or (not self.hedgehog):
            super().hurt(damage, touching)

    def kill(self):
        if self.lose_on_death:
            sge.snd.Music.clear_queue()
            sge.snd.Music.stop()
            sge.game.current_room.alarms["death"] = DEATH_TIME

        play_sound(death_sound, self.x, self.y)
        self.ball = False
        self.hedgehog = False
        self.rolling = False
        self.input_lock = True
        self.tangible = False
        self.view_frozen = True
        self.reset_input()
        self.xvelocity = 0
        self.yvelocity = 0
        self.gravity = 0
        self.reset_image()
        if self.facing > 0:
            self.sprite = anneroy_death_right_sprite
        else:
            self.sprite = anneroy_death_left_sprite
        self.image_index = 0
        self.image_fps = None
        self.image_xscale = abs(self.image_xscale)
        self.torso.visible = False
        self.fixed_sprite = "death"
        
        # Delete all alarms to prevent any problems
        self.alarms = []

    def warp_in(self):
        self.input_lock = True
        self.reset_input()
        self.xvelocity = 0
        self.yvelocity = 0
        self.reset_image()
        self.sprite = anneroy_teleport_sprite
        self.image_index = 0
        self.image_fps = anneroy_teleport_sprite.fps
        self.torso.visible = False
        self.fixed_sprite = "warp_in"

    def warp_out(self):
        self.input_lock = True
        self.reset_input()
        self.xvelocity = 0
        self.yvelocity = 0
        self.reset_image()
        self.sprite = anneroy_teleport_sprite
        self.image_index = anneroy_teleport_sprite.frames - 1
        self.image_fps = -anneroy_teleport_sprite.fps
        self.torso.visible = False
        self.fixed_sprite = "warp_out"

    def reset_image(self):
        self.visible = True
        self.torso.visible = True
        self.image_xscale = self.facing * abs(self.image_xscale)
        self.image_speed = 0

    def set_image(self):
        assert self.torso is not None
        h_control = bool(self.right_pressed) - bool(self.left_pressed)

        aim_direction = self.aim_direction
        idle_torso_right = anneroy_torso_right_idle_sprite
        idle_torso_left = anneroy_torso_left_idle_sprite

        # Turn Anneroy around.
        if not self.fixed_sprite or self.fixed_sprite == "turn":
            if not self.crouching and not self.ball:
                if self.facing < 0 and h_control > 0:
                    self.facing = 1
                    if self.fixed_sprite != "turn":
                        self.reset_image()
                        self.sprite = anneroy_turn_sprite
                        self.image_index = 0
                    self.image_speed = anneroy_turn_sprite.speed
                    self.image_xscale = abs(self.image_xscale)
                    self.torso.visible = False
                    self.fixed_sprite = "turn"
                elif self.facing > 0 and h_control < 0:
                    self.facing = -1
                    if self.fixed_sprite != "turn":
                        self.reset_image()
                        self.sprite = anneroy_turn_sprite
                        self.image_index = anneroy_turn_sprite.frames - 1
                    self.image_speed = -anneroy_turn_sprite.speed
                    self.image_xscale = abs(self.image_xscale)
                    self.torso.visible = False
                    self.fixed_sprite = "turn"
            elif h_control:
                self.facing = h_control

        if not self.fixed_sprite:
            old_is = self.image_speed
            self.reset_image()

            if self.xvelocity:
                xm = (self.xvelocity > 0) - (self.xvelocity < 0)
            else:
                real_xv = self.x - self.xprevious
                xm = (real_xv > 0) - (real_xv < 0)

            if self.ball:
                if self.hedgehog:
                    self.sprite = anneroy_hedgehog_sprite
                else:
                    self.sprite = anneroy_ball_sprite

                self.torso.visible = False
                if self.on_floor:
                    if xm:
                        self.image_speed = (self.speed
                                            * ANNEROY_BALL_FRAMES_PER_PIXEL)
                        if xm != self.facing:
                            self.image_speed *= -1
                    else:
                        self.image_speed = 0
                else:
                    self.image_speed = old_is
            else:
                # Set legs
                if self.on_floor and self.was_on_floor:
                    if self.crouching:
                        self.sprite = anneroy_legs_crouched_sprite
                    else:
                        if xm == self.facing:
                            self.sprite = anneroy_legs_run_sprite
                            self.image_speed = (self.speed
                                                * ANNEROY_RUN_FRAMES_PER_PIXEL)
                            if xm != self.facing:
                                self.image_speed *= -1

                            idle_torso_right = anneroy_torso_right_aim_right_sprite
                            idle_torso_left = anneroy_torso_left_aim_left_sprite
                        else:
                            self.sprite = anneroy_legs_stand_sprite
                else:
                    self.sprite = anneroy_legs_jump_sprite
                    self.image_index = -1
        elif self.fixed_sprite == "hedgehog":
            if self.on_floor:
                if self.xvelocity:
                    xm = (self.xvelocity > 0) - (self.xvelocity < 0)
                else:
                    real_xv = self.x - self.xprevious
                    xm = (real_xv > 0) - (real_xv < 0)

                if xm:
                    self.image_speed = (self.speed
                                        * ANNEROY_BALL_FRAMES_PER_PIXEL)
                    if xm != self.facing:
                        self.image_speed *= -1
                else:
                    self.image_speed = 0

        if "shooting" in self.alarms:
            aim_direction = self.last_aim_direction
        elif not self.fixed_sprite:
            if self.aim_direction_time < 4 and self.aim_direction is not None:
                aim_direction = max(-1, min(self.aim_direction, 1))
        else:
            if self.aim_direction_time < 16:
                aim_direction = None
            elif (self.aim_direction_time < 20 and
                  self.aim_direction is not None):
                aim_direction = max(-1, min(self.aim_direction, 1))

        # Set torso
        if self.facing > 0:
            self.torso.sprite = {
                0: anneroy_torso_right_aim_right_sprite,
                1: anneroy_torso_right_aim_upright_sprite,
                2: anneroy_torso_right_aim_up_sprite,
                -1: anneroy_torso_right_aim_downright_sprite,
                -2: anneroy_torso_right_aim_down_sprite}.get(
                    aim_direction, idle_torso_right)
        else:
            self.torso.sprite = {
                0: anneroy_torso_left_aim_left_sprite,
                1: anneroy_torso_left_aim_upleft_sprite,
                2: anneroy_torso_left_aim_up_sprite,
                -1: anneroy_torso_left_aim_downleft_sprite,
                -2: anneroy_torso_left_aim_down_sprite}.get(
                    aim_direction, idle_torso_left)

        # Position torso
        x, y = anneroy_torso_offset.setdefault(
            (id(self.sprite), self.image_index % self.sprite.frames), (0, 0))
        self.torso.x = self.x + x*self.image_xscale
        self.torso.y = self.y + y*self.image_yscale
        self.torso.z = self.z + 0.1
        self.torso.image_xscale = abs(self.image_xscale)
        self.torso.image_yscale = self.image_yscale
        self.torso.image_alpha = self.image_alpha
        self.torso.image_blend = self.image_blend

        # Position hedgehog spikes
        if self.hedgehog:
            if self.hedgehog_spikes is None:
                self.hedgehog_spikes = HedgehogSpikes.create(
                    self.x, self.y, visible=False,
                    bbox_x=ANNEROY_HEDGEHOG_BBOX_X,
                    bbox_y=ANNEROY_HEDGEHOG_BBOX_Y,
                    bbox_width=ANNEROY_HEDGEHOG_BBOX_WIDTH,
                    bbox_height=ANNEROY_HEDGEHOG_BBOX_HEIGHT,
                    regulate_origin=True)
            else:
                self.hedgehog_spikes.x = self.x
                self.hedgehog_spikes.y = self.y
                self.hedgehog_spikes.tangible = True
        else:
            if self.hedgehog_spikes is not None:
                self.hedgehog_spikes.tangible = False

    def event_create(self):
        self.torso = sge.dsp.Object.create(self.x, self.y, self.z + 0.1,
                                           regulate_origin=True)
        self.hedgehog_spikes = HedgehogSpikes.create(
            self.x, self.y, visible=False, bbox_x=ANNEROY_HEDGEHOG_BBOX_X,
            bbox_y=ANNEROY_HEDGEHOG_BBOX_Y,
            bbox_width=ANNEROY_HEDGEHOG_BBOX_WIDTH,
            bbox_height=ANNEROY_HEDGEHOG_BBOX_HEIGHT, regulate_origin=True)
        super().event_create()

    def event_begin_step(self, time_passed, delta_mult):
        super().event_begin_step(time_passed, delta_mult)

        if not self.on_floor and self.crouching:
            self.press_up()

    def event_alarm(self, alarm_id):
        super().event_alarm(alarm_id)

        if alarm_id == "fixed_sprite":
            self.fixed_sprite = False
        elif alarm_id == "hedgehog_extend":
            self.sprite = anneroy_hedgehog_extend_sprite
            self.alarms["hedgehog_extend2"] = ANNEROY_HEDGEHOG_FRAME_TIME
        elif alarm_id == "hedgehog_extend2":
            self.fixed_sprite = False
            if self.hedgehog_autocancel:
                self.alarms["hedgehog_retract"] = ANNEROY_HEDGEHOG_TIME
                self.alarms["hedgehog_lock"] = ANNEROY_HEDGEHOG_TIME
        elif alarm_id == "hedgehog_retract":
            self.retract_spikes()
        elif alarm_id == "shoot_lock":
            if self.shoot_pressed:
                self.shoot()

    def event_animation_end(self):
        if self.fixed_sprite in {"turn", "crouch", "anim"}:
            self.fixed_sprite = False
        elif self.fixed_sprite == "warp_in":
            self.image_index = self.sprite.frames - 1
            self.image_speed = 0
            self.alarms["fixed_sprite"] = WARP_TIME
            self.alarms["input_lock"] = WARP_TIME
        elif self.fixed_sprite == "warp_out":
            self.visible = False
            self.image_speed = 0
            self.alarms["warp_out"] = WARP_TIME
        elif self.fixed_sprite in {"compress", "decompress_fail"}:
            self.fixed_sprite = False
            self.image_speed = (abs(self.xvelocity)
                                * ANNEROY_BALL_FRAMES_PER_PIXEL)
        elif self.fixed_sprite == "wall":
            self.reset_image()
            if self.wall_direction < 0:
                self.sprite = anneroy_walljump_right_sprite
            else:
                self.sprite = anneroy_walljump_left_sprite
            self.image_xscale = abs(self.image_xscale)
            self.torso.visible = False
            self.fixed_sprite = "walljump"
            self.alarms["fixed_sprite"] = ANNEROY_WALLJUMP_FRAME_TIME
            self.walljumping = False
            self.input_lock = False
            self.facing = -self.wall_direction
            self.gravity = self.__class__.gravity
            self.xvelocity = ANNEROY_WALLJUMP_SPEED * self.facing
            self.yvelocity = get_jump_speed(ANNEROY_WALLJUMP_HEIGHT,
                                            self.gravity)
        elif self.fixed_sprite == "death":
            Smoke.create(self.x, self.y, z=(self.z + 0.1),
                         sprite=anneroy_explode_sprite, tangible=False)
            for i in range(12):
                shard = Shard.create(
                    self.x, self.y, self.z, sprite=anneroy_explode_fragments,
                    image_index=random.randrange(
                        anneroy_explode_fragments.frames),
                    image_fps=0)
                shard.speed = 5
                shard.move_direction = random.randrange(360)
            self.destroy()

    def event_physics_collision_top(self, other, move_loss):
        super().event_physics_collision_top(other, move_loss)
        self.event_animation_end()

    def event_physics_collision_bottom(self, other, move_loss):
        yv = self.yvelocity
        super().event_physics_collision_bottom(other, move_loss)

        if not self.was_on_floor:
            if self.hedgehog:
                play_sound(ball_land_sound, self.x, self.y)
            elif self.ball:
                if not self.bouncing or yv >= ANNEROY_BALL_FORCE_BOUNCE_SPEED:
                    self.bouncing = True
                    self.yvelocity = get_jump_speed(ANNEROY_BALL_BOUNCE_HEIGHT,
                                                    self.gravity)
                else:
                    self.bouncing = False
                play_sound(ball_land_sound, self.x, self.y)
            else:
                self.reset_image()
                self.sprite = anneroy_legs_land_sprite
                self.image_speed = None
                self.image_index = 0
                self.fixed_sprite = "anim"
                play_sound(land_sound, self.x, self.y)

    def event_jump(self):
        if not self.ball:
            self.reset_image()
            self.sprite = anneroy_legs_jump_sprite
            self.image_speed = None
            self.image_index = 0
            self.fixed_sprite = "anim"

    def event_destroy(self):
        if self.torso is not None:
            self.torso.destroy()


class DeadMan(sge.dsp.Object):

    """Object which falls off the screen, then gets destroyed."""

    gravity = GRAVITY
    fall_speed = PLAYER_FALL_SPEED

    def event_begin_step(self, time_passed, delta_mult):
        if self.yvelocity < self.fall_speed:
            self.yacceleration = self.gravity
        else:
            self.yvelocity = self.fall_speed
            self.yacceleration = 0

    def event_step(self, time_passed, delta_mult):
        if self.y - self.image_origin_y > sge.game.current_room.height:
            self.destroy()


class Corpse(xsge_physics.Collider):

    """Like DeadMan, but just falls to the floor, not off-screen."""

    gravity = GRAVITY
    fall_speed = PLAYER_FALL_SPEED

    def event_create(self):
        self.alarms["die"] = 90

    def event_begin_step(self, time_passed, delta_mult):
        if self.get_bottom_touching_wall() or self.get_bottom_touching_slope():
            self.yvelocity = 0
        else:
            if self.yvelocity < self.fall_speed:
                self.yacceleration = self.gravity
            else:
                self.yvelocity = min(self.yvelocity, self.fall_speed)
                self.yacceleration = 0

    def event_alarm(self, alarm_id):
        if alarm_id == "die":
            self.destroy()


class Smoke(sge.dsp.Object):

    def event_animation_end(self):
        self.destroy()


class InteractiveObject(sge.dsp.Object):

    shootable = False
    spikeable = False
    freezable = False

    def get_nearest_player(self):
        player = None
        dist = 0
        for obj in sge.game.current_room.objects:
            if isinstance(obj, Player):
                ndist = math.hypot(self.x - obj.x, self.y - obj.y)
                if player is None or ndist < dist:
                    player = obj
                    dist = ndist
        return player

    def set_direction(self, direction):
        self.image_xscale = abs(self.image_xscale) * direction
        self.xvelocity = math.copysign(self.xvelocity, self.image_xscale)

    def move(self):
        pass

    def touch(self, other):
        pass

    def shoot(self, other):
        pass

    def spike(self, other):
        self.shoot(other)

    def freeze(self):
        pass

    def project_light(self):
        pass

    def event_begin_step(self, time_passed, delta_mult):
        self.move()


class InteractiveCollider(InteractiveObject, xsge_physics.Collider):

    def stop_left(self):
        self.xvelocity = 0

    def stop_right(self):
        self.xvelocity = 0

    def stop_up(self):
        self.yvelocity = 0

    def stop_down(self):
        self.yvelocity = 0

    def touch_hurt(self):
        pass

    def event_physics_collision_left(self, other, move_loss):
        if isinstance(other, HurtRight):
            self.touch_hurt()

        if isinstance(other, xsge_physics.SolidRight):
            self.stop_left()
        elif isinstance(other, xsge_physics.SlopeTopRight):
            if self.yvelocity > 0:
                self.stop_down()
        elif isinstance(other, xsge_physics.SlopeBottomRight):
            if self.yvelocity < 0:
                self.stop_up()

    def event_physics_collision_right(self, other, move_loss):
        if isinstance(other, HurtLeft):
            self.touch_hurt()

        if isinstance(other, xsge_physics.SolidLeft):
            self.stop_right()
        elif isinstance(other, xsge_physics.SlopeTopLeft):
            if self.yvelocity > 0:
                self.stop_down()
        elif isinstance(other, xsge_physics.SlopeBottomLeft):
            if self.yvelocity < 0:
                self.stop_up()

    def event_physics_collision_top(self, other, move_loss):
        if isinstance(other, HurtBottom):
            self.touch_hurt()
        if isinstance(other, (xsge_physics.SolidBottom,
                              xsge_physics.SlopeBottomLeft,
                              xsge_physics.SlopeBottomRight)):
            self.stop_up()

    def event_physics_collision_bottom(self, other, move_loss):
        if isinstance(other, HurtTop):
            self.touch_hurt()
        if isinstance(other, (xsge_physics.SolidTop, xsge_physics.SlopeTopLeft,
                              xsge_physics.SlopeTopRight)):
            self.stop_down()


class FallingObject(InteractiveCollider):

    """
    Falls based on gravity. If on a slope, falls at a constant speed
    based on the steepness of the slope.
    """

    gravity = GRAVITY
    fall_speed = PLAYER_FALL_SPEED
    slide_speed = PLAYER_SLIDE_SPEED

    was_on_floor = False

    def move(self):
        on_floor = self.get_bottom_touching_wall()
        on_slope = self.get_bottom_touching_slope()
        if self.was_on_floor and (on_floor or on_slope) and self.yvelocity >= 0:
            self.yacceleration = 0
            if on_floor:
                if self.yvelocity > 0:
                    self.yvelocity = 0
            elif on_slope:
                self.yvelocity = self.slide_speed * (on_slope[0].bbox_height
                                                     / on_slope[0].bbox_width)
        else:
            if self.yvelocity < self.fall_speed:
                self.yacceleration = self.gravity
            else:
                self.yvelocity = self.fall_speed
                self.yacceleration = 0

        self.was_on_floor = on_floor or on_slope


class WalkingObject(FallingObject):

    """
    Walks in the direction it faces.  Turns around at walls, and can
    also be set to turn around at ledges with the stayonplatform
    attribute.  If slopeisplatform is False, slopes are regarded as
    ledges.
    """

    walk_speed = PLAYER_MAX_SPEED
    stayonplatform = False
    slopeisplatform = True

    def set_direction(self, direction):
        self.xvelocity = self.walk_speed * direction
        self.image_xscale = abs(self.image_xscale) * direction

    def move(self):
        super().move()

        if not self.xvelocity:
            self.set_direction(math.copysign(1, self.image_xscale))

        on_floor = self.get_bottom_touching_wall()
        on_slope = self.slopeisplatform and self.get_bottom_touching_slope()
        if (on_floor or on_slope) and self.stayonplatform:
            if self.xvelocity < 0:
                my_left = self.bbox_left + (self.x-self.bbox_left)/2
                for tile in on_floor:
                    if tile.bbox_left < my_left:
                        break
                else:
                    if not on_slope:
                        self.set_direction(1)
            else:
                my_right = self.bbox_right - (self.bbox_right-self.x)/2
                for tile in on_floor:
                    if tile.bbox_right > my_right:
                        break
                else:
                    if not on_slope:
                        self.set_direction(-1)

    def stop_left(self):
        self.set_direction(1)

    def stop_right(self):
        self.set_direction(-1)


class CrowdBlockingObject(InteractiveObject):

    """Blocks CrowdObject instances, causing them to turn around."""

    pass


class CrowdObject(CrowdBlockingObject):

    """
    Turns around when colliding with a CrowdBlockingObject.  (Note: this
    class is itself derived from CrowdBlockingObject.)
    """

    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, CrowdBlockingObject):
            if xdirection:
                self.set_direction(-xdirection)
            else:
                if self.x > other.x:
                    self.set_direction(1)
                elif self.x < other.x:
                    self.set_direction(-1)
                elif id(self) > id(other):
                    self.set_direction(1)
                else:
                    self.set_direction(-1)
        else:
            super().event_collision(other, xdirection, ydirection)


class Shard(FallingObject):

    """Like Corpse, but bounces around a bit before disappearing."""

    fall_speed = 99
    bounce = 0.5
    friction = 0.99
    life = 45

    def stop_left(self):
        self.xvelocity *= -self.bounce

    def stop_right(self):
        self.xvelocity *= -self.bounce

    def stop_up(self):
        self.yvelocity *= -self.bounce

    def stop_down(self):
        self.yvelocity *= -self.bounce

    def event_create(self):
        self.alarms["die"] = self.life

    def move(self):
        super().move()
        self.speed *= self.friction

    def event_alarm(self, alarm_id):
        if alarm_id == "die":
            blend = sge.gfx.Color((255, 255, 255, 0))
            base_sprite = sge.gfx.Sprite(width=self.sprite.width,
                                         height=self.sprite.height,
                                         origin_x=self.sprite.origin_x,
                                         origin_y=self.sprite.origin_y)
            base_sprite.draw_sprite(self.sprite, self.image_index,
                                    self.sprite.origin_x, self.sprite.origin_y)
            spr = sge.gfx.Sprite.from_tween(
                base_sprite, int(hlib.FPS / 4), fps=hlib.FPS, blend=blend,
                blend_mode=sge.BLEND_RGBA_MULTIPLY)
            Smoke.create(self.x, self.y, z=self.z, sprite=spr, tangible=False,
                         xvelocity=self.xvelocity, yvelocity=self.yvelocity,
                         image_origin_x=self.image_origin_x,
                         image_origin_y=self.image_origin_y,
                         image_xscale=self.image_xscale,
                         image_yscale=self.image_yscale,
                         image_rotation=self.image_rotation,
                         image_alpha=self.image_alpha,
                         image_blend=self.image_blend,
                         image_blend_mode=self.image_blend_mode)

            self.destroy()


class Enemy(InteractiveObject):

    classname = None
    shootable = True
    spikeable = True
    touch_damage = 5
    hp = 1
    shard_num_min = 4
    shard_num_max = 8
    shard_speed_min = 1
    shard_speed_max = 3

    def touch(self, other):
        other.hurt(self.touch_damage, True)

    def shoot(self, other):
        # TODO: Handle different kinds of bullets
        self.hurt(1)

    def spike(self, other):
        self.hurt(3)

    def hurt(self, damage=1):
        self.hp -= damage
        if self.hp <= 0:
            self.kill()
        else:
            self.image_blend = sge.gfx.Color("white")
            self.image_blend_mode = sge.BLEND_RGB_SCREEN
            self.alarms["hurt_flash"] = hlib.FPS / 10
            play_sound(enemy_hurt_sound, self.image_xcenter, self.image_ycenter)

    def kill(self):
        if sge.game.fps_real >= hlib.FPS:
            shard_num = random.randint(self.shard_num_min, self.shard_num_max)
        else:
            shard_num = self.shard_num_min

        for i in range(shard_num):
            shard = Shard.create(self.x, self.y, self.z,
                                 sprite=enemy_fragment_sprite)
            shard.speed = random.randint(self.shard_speed_min,
                                         self.shard_speed_max)
            shard.move_direction = random.randrange(360)

        if random.random() < LIFE_FORCE_CHANCE:
            LifeForce.create(self.image_xcenter, self.image_ycenter,
                             z=self.z - 0.1)

        play_sound(enemy_death_sound, self.image_xcenter, self.image_ycenter)
        self.destroy()

    def event_alarm(self, alarm_id):
        if alarm_id == "hurt_flash":
            self.image_blend = None
            self.image_blend_mode = None


class FreezableObject(InteractiveObject):

    """Provides basic freeze behavior."""

    freezable = True
    frozen_sprite = None
    frozen_time = 120
    frozen = False

    def permafreeze(self):
        prev_frozen_time = self.frozen_time
        self.frozen_time = None
        self.freeze()
        self.frozen_time = prev_frozen_time

    def freeze(self):
        if self.frozen_sprite is None:
            self.frozen_sprite = sge.gfx.Sprite(
                width=self.sprite.width, height=self.sprite.height,
                origin_x=self.sprite.origin_x, origin_y=self.sprite.origin_y,
                fps=THAW_FPS, bbox_x=self.sprite.bbox_x,
                bbox_y=self.sprite.bbox_y, bbox_width=self.sprite.bbox_width,
                bbox_height=self.sprite.bbox_height)
            self.frozen_sprite.append_frame()
            self.frozen_sprite.draw_sprite(self.sprite, self.image_index,
                                           self.sprite.origin_x,
                                           self.sprite.origin_y)
            colorizer = sge.gfx.Sprite(width=self.frozen_sprite.width,
                                       height=self.frozen_sprite.height)
            colorizer.draw_rectangle(0, 0, colorizer.width, colorizer.height,
                                     fill=sge.gfx.Color((128, 128, 255)))
            self.frozen_sprite.draw_sprite(colorizer, 0, 0, 0, frame=0,
                                           blend_mode=sge.BLEND_RGB_MULTIPLY)

        frozen_self = FrozenObject.create(self.x, self.y, self.z,
                                          sprite=self.frozen_sprite,
                                          image_fps=0,
                                          image_xscale=self.image_xscale,
                                          image_yscale=self.image_yscale)
        frozen_self.unfrozen = self
        self.frozen = True
        self.tangible = False
        self.active = False
        self.visible = False
        if self.frozen_time is not None:
            frozen_self.alarms["thaw_warn"] = self.frozen_time


class FrozenObject(InteractiveObject, xsge_physics.Solid):

    freezable = True
    unfrozen = None

    def thaw(self):
        if self.unfrozen is not None:
            self.unfrozen.frozen = False
            self.unfrozen.tangible = True
            self.unfrozen.visible = True
            self.unfrozen.activate()
        self.destroy()

    def burn(self):
        self.thaw()
        play_sound(sizzle_sound, self.x, self.y)

    def freeze(self):
        if self.unfrozen is not None:
            self.thaw()
            self.unfrozen.freeze()

    def event_alarm(self, alarm_id):
        if self.unfrozen is not None:
            if alarm_id == "thaw_warn":
                self.image_fps = None
                self.alarms["thaw"] = THAW_WARN_TIME
            elif alarm_id == "thaw":
                self.thaw()


class Frog(Enemy, FallingObject, CrowdObject):

    slide_speed = 0
    jump_distance = 200
    jump_height = 2*hlib.TILE_SIZE + 1
    jump_speed = 3
    jump_interval = hlib.FPS / 2

    def stop_left(self):
        if self.yvelocity >= 0:
            self.xvelocity = 0

    def stop_right(self):
        if self.yvelocity >= 0:
            self.xvelocity = 0

    def stop_down(self):
        self.xvelocity = 0
        self.yvelocity = 0

    def event_create(self):
        self.bbox_x = 2
        self.bbox_y = 5
        self.bbox_width = 12
        self.bbox_height = 11

    def event_step(self, time_passed, delta_mult):
        super().event_step(time_passed, delta_mult)

        if ("jump" not in self.alarms and self.was_on_floor and
                not self.yvelocity):
            self.alarms["jump"] = self.jump_interval
            target = self.get_nearest_player()
            if target is not None:
                xvec = target.x - self.image_xcenter
                self.image_xscale = math.copysign(self.image_xscale, xvec)

        if self.was_on_floor:
            self.sprite = frog_stand_sprite
            if self.yvelocity == 0:
                # Set xvelocity to 0 in case the frog happened to have
                # yvelocity == 0 as it started touching the floor (which
                # prevents stop_down from being called).
                self.xvelocity = 0
        elif self.yvelocity < 0:
            self.sprite = frog_jump_sprite
        else:
            self.sprite = frog_fall_sprite

    def event_alarm(self, alarm_id):
        if alarm_id == "jump":
            target = self.get_nearest_player()
            if target is not None:
                xvec = target.x - self.image_xcenter
                yvec = target.y - self.image_ycenter
                self.image_xscale = math.copysign(self.image_xscale, xvec)
                dist = math.hypot(xvec, yvec)
                if dist <= self.jump_distance:
                    self.xvelocity = math.copysign(self.jump_speed, xvec)
                    self.yvelocity = get_jump_speed(self.jump_height,
                                                    self.gravity)
                    play_sound(frog_jump_sound, self.image_xcenter,
                               self.image_ycenter)


class Hedgehog(Enemy, FallingObject, CrowdBlockingObject):

    hp = 3
    touch_damage = 7
    charge_distance = 300
    acceleration = 0.25
    walk_speed = 1
    max_speed = 4
    roll_slope_acceleration = 0.2
    roll_max_speed = 8
    friction = PLAYER_FRICTION
    roll_friction = 0.05
    walk_frames_per_pixel = 1 / 4
    roll_frames_per_pixel = 1 / 5

    @property
    def slope_acceleration(self):
        if self.rolling:
            return self.roll_slope_acceleration
        else:
            return 0

    def stop_left(self):
        self.xvelocity = 0

    def stop_right(self):
        self.xvelocity = 0

    def event_create(self):
        self.bbox_x = 4
        self.bbox_y = 6
        self.bbox_width = 12
        self.bbox_height = 14
        self.rolling = False
        self.anim_lock = False
        self.sprite = hedgehog_stand_sprite

    def event_step(self, time_passed, delta_mult):
        self.xacceleration = 0
        if self.rolling:
            if self.was_on_floor:
                self.xdeceleration = self.roll_friction
                target = self.get_nearest_player()
                if target is not None:
                    xvec = target.x - self.image_xcenter
                    tdir = (xvec > 0) - (xvec < 0)
                    vdir = (self.xvelocity > 0) - (self.xvelocity < 0)
                    yvec = target.y - self.image_ycenter
                    dist = math.hypot(xvec, yvec)
                    if dist <= self.charge_distance and tdir == vdir:
                        if abs(self.xvelocity) < self.max_speed:
                            self.xacceleration = math.copysign(
                                self.acceleration, xvec)
                            self.xdeceleration = 0
                            
            else:
                self.xdeceleration = 0

            if abs(self.xvelocity) < self.walk_speed:
                self.rolling = False
                self.anim_lock = True
                self.sprite = hedgehog_uncompress_sprite
                self.image_index = 0
                self.image_speed = None

            if not self.anim_lock:
                self.sprite = hedgehog_ball_sprite
                self.image_speed = (abs(self.xvelocity)
                                    * self.roll_frames_per_pixel)

            if abs(self.xvelocity) >= self.roll_max_speed:
                self.xvelocity = math.copysign(self.roll_max_speed,
                                               self.xvelocity)
        else:
            if self.was_on_floor:
                self.xdeceleration = self.friction
                target = self.get_nearest_player()
                if target is not None:
                    xvec = target.x - self.image_xcenter
                    yvec = target.y - self.image_ycenter
                    dist = math.hypot(xvec, yvec)
                    if dist <= self.charge_distance:
                        self.xacceleration = math.copysign(self.acceleration,
                                                           xvec)
                        self.xdeceleration = 0
                        if abs(self.xvelocity) >= self.max_speed:
                            self.xvelocity = math.copysign(self.max_speed,
                                                           self.xvelocity)
                            self.rolling = True
                            self.anim_lock = True
                            self.sprite = hedgehog_compress_sprite
                            self.image_index = 0
                            self.image_speed = None
            else:
                self.xdeceleration = 0

            if not self.anim_lock:
                if self.xvelocity:
                    self.sprite = hedgehog_walk_sprite
                    self.image_speed = (abs(self.xvelocity)
                                        * self.walk_frames_per_pixel)
                else:
                    self.sprite = hedgehog_stand_sprite

        self.image_xscale = math.copysign(self.image_xscale, self.xvelocity)

    def event_animation_end(self):
        self.anim_lock = False


class Worm(Enemy, InteractiveCollider, CrowdBlockingObject):

    hp = 3
    touch_damage = 10
    extend_distance = 96
    repeat_delay = 90

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = worm_sprite
        kwargs["collision_precise"] = True
        kwargs["tangible"] = False
        kwargs["image_fps"] = 0
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def event_create(self):
        sge.dsp.Object.create(
            self.x, self.y, self.z + 0.1, sprite=worm_base_sprite,
            tangible=False)

    def event_step(self, time_passed, delta_mult):
        super().event_step(time_passed, delta_mult)

        if self.tangible or "extend_wait" in self.alarms:
            return

        target = self.get_nearest_player()
        if target is None:
            return

        xvec = target.x - self.image_xcenter
        yvec = target.y - self.image_ycenter
        dist = math.hypot(xvec, yvec)
        if dist <= self.extend_distance:
            self.tangible = True
            self.image_fps = None
            self.image_index = 0

    def event_animation_end(self):
        self.tangible = False
        self.image_fps = 0
        self.image_index = 0
        self.alarms["extend_wait"] = self.repeat_delay


class Bat(Enemy, InteractiveCollider, CrowdBlockingObject):

    max_distance = 50
    move_time_min = hlib.FPS // 2
    move_time_max = hlib.FPS * 2
    scatter_time = hlib.FPS * 3 // 4

    def __init__(self, x, y, **kwargs):
        self.scattering = False
        kwargs["sprite"] = bat_sprite
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def touch(self, other):
        if self.scattering:
            return

        self.alarms["move"] = self.scatter_time
        self.image_speed = self.sprite.speed * 2
        self.speed = 2
        self.move_direction = random.uniform(0, 360)
        self.scattering = True

    def stop_left(self):
        self.xvelocity *= -1

    def stop_right(self):
        self.xvelocity *= -1

    def stop_up(self):
        self.yvelocity *= -1

    def stop_down(self):
        self.yvelocity *= -1

    def event_create(self):
        self.image_xscale *= random.choice([1, -1])
        self.event_alarm("move")

    def event_step(self, time_passed, delta_mult):
        super().event_step(time_passed, delta_mult)

        if self.xvelocity:
            self.image_xscale = math.copysign(self.image_xscale, self.xvelocity)

    def event_alarm(self, alarm_id):
        if alarm_id == "move":
            self.scattering = False
            self.image_speed = None
            self.speed = random.uniform(0, 1)
            if self.speed < 0.25:
                self.speed = 0
            xdiff = self.xstart - self.x
            ydiff = self.ystart - self.y
            if math.hypot(xdiff, ydiff) < self.max_distance:
                self.move_direction = random.uniform(0, 360)
            else:
                self.move_direction = math.degrees(math.atan2(ydiff, xdiff))
            self.alarms["move"] = random.randrange(self.move_time_min,
                                                   self.move_time_max)


class Jellyfish(Enemy, CrowdBlockingObject):

    hp = 3
    touch_damage = 7
    swim_speed = 2
    friction = 0.025
    swim_interval = hlib.FPS

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = jellyfish_idle_sprite
        kwargs["regulate_origin"] = True
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def stop_left(self):
        self.xvelocity = 0
        self.yvelocity = 0

    def stop_right(self):
        self.xvelocity = 0
        self.yvelocity = 0

    def stop_up(self):
        self.xvelocity = 0
        self.yvelocity = 0

    def stop_down(self):
        self.xvelocity = 0
        self.yvelocity = 0

    def event_create(self):
        self.x += self.image_origin_x
        self.y += self.image_origin_y
        self.bbox_x = -9
        self.bbox_y = -9
        self.bbox_width = 17
        self.bbox_height = 17
        self.xdeceleration = self.friction
        self.ydeceleration = self.friction
        self.alarms["swim"] = self.swim_interval

    def event_alarm(self, alarm_id):
        super().event_alarm(alarm_id)

        if alarm_id == "swim":
            choices = 3*[1] + [-1]
            xv = random.choice(choices)
            if self.x > self.xstart:
                xv *= -1
            yv = random.choice(choices)
            if self.y > self.ystart:
                yv *= -1

            self.image_xscale = math.copysign(self.image_xscale, xv)
            self.image_yscale = math.copysign(self.image_yscale, yv)
            self.sprite = jellyfish_swim_start_sprite
            self.image_index = 0

    def event_animation_end(self):
        if self.sprite == jellyfish_swim_start_sprite:
            self.sprite = jellyfish_swim_sprite
            self.image_index = 0
            self.xvelocity = math.copysign(self.swim_speed, self.image_xscale)
            self.yvelocity = math.copysign(self.swim_speed, self.image_yscale)
            self.alarms["swim"] = self.swim_interval
        elif self.sprite != jellyfish_idle_sprite:
            self.sprite = jellyfish_idle_sprite
            self.image_index = 0


class Scorpion(Enemy, WalkingObject, CrowdObject):

    walk_speed = 1
    hp = 10
    touch_damage = 10
    stayonplatform = True
    slopeisplatform = False
    sight_distance = 1000
    sight_threshold = 64
    shoot_interval = hlib.FPS
    shoot_recheck_interval = hlib.FPS / 10
    bullet_speed = 3

    def __init__(self, x, y, **kwargs):
        x += scorpion_stand_sprite.origin_x
        y += scorpion_stand_sprite.origin_y
        kwargs["sprite"] = scorpion_stand_sprite
        kwargs["bbox_x"] = -28
        kwargs["bbox_y"] = -1
        kwargs["bbox_width"] = 56
        kwargs["bbox_height"] = 28
        super().__init__(x, y, **kwargs)

    def move(self):
        if not self.action:
            super().move()
            if self.xvelocity:
                self.sprite = scorpion_walk_sprite
                self.image_speed = (abs(self.xvelocity)
                                    * SCORPION_WALK_FRAMES_PER_PIXEL)
            else:
                self.sprite = scorpion_stand_sprite

    def attack(self):
        target = self.get_nearest_player()
        if target is not None:
            xvec = target.x - self.image_xcenter
            yvec = target.y - self.image_ycenter
            if (abs(xvec) <= self.sight_distance
                    and abs(yvec) < self.sight_threshold):
                self.xvelocity = 0
                self.action = "shoot_start"
                self.sprite = scorpion_shoot_start_sprite
                self.image_index = 0
                self.image_fps = None
                self.image_xscale = math.copysign(self.image_xscale, xvec)
                return

        self.alarms["shoot"] = self.shoot_recheck_interval

    def event_create(self):
        super().event_create()
        self.alarms["shoot"] = self.shoot_interval
        self.action = None

    def event_alarm(self, alarm_id):
        super().event_alarm(alarm_id)

        if alarm_id == "shoot":
            self.attack()

    def event_animation_end(self):
        if self.action == "shoot_start":
            self.action = "shoot_end"
            self.sprite = scorpion_shoot_end_sprite
            self.image_index = 0
            self.image_fps = None
            xv = math.copysign(self.bullet_speed, self.image_xscale)
            x = self.x
            if self.image_xscale < 0:
                x -= scorpion_projectile_sprite.width
            ScorpionBullet.create(
                x, self.y, self.z + 0.1,
                sprite=scorpion_projectile_sprite, xvelocity=xv,
                image_xscale=self.image_xscale, image_yscale=self.image_yscale)
            play_sound(scorpion_shoot_sound, self.x, self.y)
        elif self.action == "shoot_end":
            self.action = None
            self.sprite = scorpion_stand_sprite
            self.alarms["shoot"] = self.shoot_interval


class Mantanoid(Enemy, FallingObject, CrowdBlockingObject):

    classname = "Mantanoid"
    hp = 10
    touch_damage = 10
    slash_damage = 20
    sight_distance = 300
    shard_num_min = 8
    shard_num_max = 16

    def __init__(self, x, y, hiding=False, wander_x=None, **kwargs):
        x += mantanoid_stand_sprite.origin_x
        y += mantanoid_stand_sprite.origin_y
        kwargs["sprite"] = mantanoid_stand_sprite
        kwargs["bbox_x"] = MANTANOID_BBOX_X
        kwargs["bbox_y"] = MANTANOID_BBOX_Y
        kwargs["bbox_width"] = MANTANOID_BBOX_WIDTH
        kwargs["bbox_height"] = MANTANOID_BBOX_HEIGHT
        kwargs["regulate_origin"] = True
        super().__init__(x, y, **kwargs)
        self.hiding = hiding
        self.wander_x = wander_x if wander_x else x
        self.has_approached = False
        self.action = None
        self.target = None
        self.movement_speed = 0
        self.can_act = False
        self.action_check = None
        self.action_check_id = None
        self.action_check_x = None
        self.action_check_y = None
        self.action_check_dest_x = None
        self.action_check_dest_y = None
        self.action_check_verify = None
        self.spitball_checks = []
        self.spitball_check_ids = []

    def set_direction(self, direction):
        if not self.action and self.can_act:
            if direction > 0:
                self.perform_action(self.action_turn_right)
            elif direction < 0:
                self.perform_action(self.action_turn_left)

    def stop_left(self):
        if self.yvelocity > 0 and not self.was_on_floor:
            self.xvelocity = 0

        if not self.action and self.can_act:
            if self.target is not None:
                if (not self.check_action(self.action_hop, self.target.x,
                                          self.target.y, "stop_down")
                        and not self.check_action(self.action_jump,
                                                  self.target.x, self.target.y,
                                                  "stop_down")):
                    self.target = None
            else:
                self.perform_action(self.action_turn_right)

    def stop_right(self):
        if self.yvelocity > 0 and not self.was_on_floor:
            self.xvelocity = 0

        if not self.action and self.can_act:
            if self.target is not None:
                if (not self.check_action(self.action_hop, self.target.x,
                                          self.target.y, "stop_down")
                        and not self.check_action(self.action_jump,
                                                  self.target.x, self.target.y,
                                                  "stop_down")):
                    self.target = None
            else:
                self.perform_action(self.action_turn_left)

    def stop_up(self):
        self.yvelocity = 0
        if (self.action_check_verify == "stop_down"
                and self.get_bottom_touching_wall()):
            self.verify_action()

    def stop_down(self):
        self.xvelocity = 0
        self.yvelocity = 0

        if not self.was_on_floor:
            if not self.action or self.action == "animation":
                self.sprite = mantanoid_land_sprite
                self.fps = None
                self.image_index = 0
                self.action = "animation"

        if self.action_check_verify == "stop_down":
            self.verify_action()

    def update_wander(self):
        if (not self.hiding and self.was_on_floor
                and "move_lock" not in self.alarms):
            choices = 3 * [1] + 7 * [0] + [-1]
            xv = random.choice(choices)
            if self.x > self.wander_x:
                xv *= -1

            self.set_direction(xv)
            self.movement_speed = MANTANOID_WANDER_SPEED * abs(xv)
            self.alarms["move_lock"] = MANTANOID_WANDER_INTERVAL

    def log_action_result(self, action, success):
        ai_data.setdefault(action, [0, 0])
        i = 0 if success else 1
        ai_data[action][i] += 1

        # Record the spitballs as a success. Note: we do NOT log
        # failures here since the same spitballs might actually lead to
        # other solutions and we don't want to impede the AI's trust in
        # later successful spitballs just because it didn't work this
        # time.
        if success:
            for spitball in self.spitball_check_ids:
                ai_data.setdefault(spitball, [0, 0])
                ai_data[spitball][0] += 1

    def perform_action(self, action):
        if not self.action and self.can_act:
            self.can_act = False
            self.reset_action_check()
            self.xvelocity = 0
            action()

    def check_action(self, action, target_x, target_y, verify_event,
                     check_x=None, check_y=None):
        if not self.can_act:
            return False

        if target_x is None and target_y is None:
            self.perform_action(action)
            return True

        if target_x is not None and target_y is not None:
            if sge.collision.rectangle(target_x, target_y, 1, 1, MantanoidNoGo):
                # No-go zone, which means we can't go there no matter what.
                return False

        def rough(x):
            return int(math.floor(x / 8)) * 8 if x is not None else None

        if check_x is None:
            check_x = target_x
        if check_y is None:
            check_y = target_y

        action_id = "{}; {}: ({},{};{}+{})->({},{})|({},{})!{}".format(
            self.__class__.__name__, sge.game.current_room.fname,
            rough(self.x), rough(self.y), self.image_xscale,
            self.movement_speed, rough(target_x), rough(target_y),
            rough(check_x), rough(check_y), action.__name__)

        ai_data.setdefault(action_id, [0, 0])
        successes = ai_data[action_id][0]
        fails = ai_data[action_id][1]

        if successes >= 3 and successes > fails:
            if target_x is not None:
                if target_x < self.x and self.image_xscale > 0:
                    self.perform_action(self.action_turn_left)
                    return True
                elif target_x > self.x and self.image_xscale < 0:
                    self.perform_action(self.action_turn_right)
                    return True

            self.perform_action(action)
            return True
        elif fails < 3:
            if target_x is not None:
                if target_x < self.x and self.image_xscale > 0:
                    self.perform_action(self.action_turn_left)
                    return True
                elif target_x > self.x and self.image_xscale < 0:
                    self.perform_action(self.action_turn_right)
                    return True

            self.perform_action(action)
            self.action_check = action
            self.action_check_id = action_id
            self.action_check_x = self.x
            self.action_check_y = self.y
            self.action_check_dest_x = check_x
            self.action_check_dest_y = check_y
            self.action_check_verify = verify_event

            self.spitball_check_ids = []
            for s_action, s_x, s_y, s_ixs, s_spd in self.spitball_checks:
                sid = "{}; {}: ({},{};{}+{})->({},{})|({},{})!{}".format(
                    self.__class__.__name__, sge.game.current_room.fname,
                    rough(s_x), rough(s_y), s_ixs, s_spd, rough(target_x),
                    rough(target_y), rough(check_x), rough(check_y),
                    s_action.__name__)
                self.spitball_check_ids.append(sid)
            self.spitball_checks = []

            return True

        return False

    def verify_action(self):
        if self.action_check is not None:
            if (self.action_check_dest_x is None and
                    self.action_check_dest_y is None):
                self.log_action_result(self.action_check_id, True)
            elif self.action_check_dest_x is None:
                orig_dist = abs(self.action_check_dest_y - self.action_check_y)
                new_dist = abs(self.action_check_dest_y - self.y)
            elif self.action_check_dest_y is None:
                orig_dist = abs(self.action_check_dest_x - self.action_check_x)
                new_dist = abs(self.action_check_dest_x - self.x)
            else:
                orig_dist = abs(math.hypot(
                    self.action_check_dest_x - self.action_check_x,
                    self.action_check_dest_y - self.action_check_y))
                new_dist = abs(math.hypot(
                    self.action_check_dest_x - self.x,
                    self.action_check_dest_y - self.y))

            if new_dist < orig_dist:
                self.log_action_result(self.action_check_id, True)
            else:
                self.log_action_result(self.action_check_id, False)

            self.reset_action_check()

    def reset_action_check(self):
        self.action_check = None
        self.action_check_id = None
        self.action_check_x = None
        self.action_check_y = None
        self.action_check_dest_x = None
        self.action_check_dest_y = None
        self.action_check_verify = None

    def action_turn_left(self):
        if (self.image_xscale > 0 and not self.action and
                self.was_on_floor and self.get_bottom_touching_wall()):
            self.image_xscale = -abs(self.image_xscale)
            self.sprite = mantanoid_turn_sprite
            self.image_fps = None
            self.image_index = 0
            self.action = "animation"

    def action_turn_right(self):
        if (self.image_xscale < 0 and not self.action and
                self.was_on_floor and self.get_bottom_touching_wall()):
            self.image_xscale = abs(self.image_xscale)
            self.sprite = mantanoid_turn_sprite
            self.image_fps = None
            self.image_index = 0
            self.action = "animation"

    def action_hop(self):
        if (self.was_on_floor and self.yvelocity >= 0 and
                (self.get_bottom_touching_wall() or
                 self.get_bottom_touching_slope())):
            self.sprite = mantanoid_hop_start_sprite
            self.image_fps = None
            self.image_index = 0
            self.action = "hop"

    def action_jump(self):
        if (self.was_on_floor and self.yvelocity >= 0 and
                (self.get_bottom_touching_wall() or
                 self.get_bottom_touching_slope())):
            self.sprite = mantanoid_jump_start_sprite
            self.image_fps = None
            self.image_index = 0
            self.action = "jump"

    def action_approach(self):
        self.hiding = False
        if self.target is not None:
            if self.movement_speed != MANTANOID_APPROACH_SPEED:
                self.movement_speed = MANTANOID_APPROACH_SPEED
                if not self.has_approached:
                    self.has_approached = True
                    play_sound(mantanoid_approach_sound, self.x, self.y)

            self.alarms["action_lock"] = MANTANOID_APPROACH_INTERVAL

    def action_slash(self):
        self.hiding = False
        if self.target is not None:
            self.action = "slash"
            self.sprite = mantanoid_slash_start_sprite
            self.image_fps = None
            self.image_index = 0

    def get_spitball_action(self):
        choices = 6*[self.action_approach] + [self.action_jump, self.action_hop]
        if not self.spitball_checks:
            if self.image_xscale < 0:
                choices.append(self.action_turn_right)
            else:
                choices.append(self.action_turn_left)

        action = random.choice(choices)
        self.spitball_checks.append((action, self.x, self.y, self.image_xscale,
                                     self.movement_speed))
        return action

    def check_hazards(self):
        return None

    def update_action(self):
        action = self.check_hazards()
        if not action:
            if (self.target is not None
                    and not self.target.collision(MantanoidNoGo)):
                xdist = abs(self.target.x - self.x)
                ydist = abs(self.target.y - self.y)
                if (xdist <= MANTANOID_SLASH_DISTANCE
                        and ydist <= MANTANOID_LEVEL_DISTANCE):
                    action = self.action_slash
                elif "action_lock" not in self.alarms:
                    if not self.hiding:
                        if random.random() < 0.1:
                            # Randomly decide to spitball (curiosity)
                            action = self.get_spitball_action()
                        elif self.target.on_floor and self.check_action(
                                self.action_approach, self.target.x,
                                self.target.y, "action_lock"):
                            return
                        elif self.target.on_floor and self.check_action(
                                self.action_jump, self.target.x, self.target.y,
                                "stop_down"):
                            return
                        elif self.target.on_floor and self.check_action(
                                self.action_hop, self.target.x, self.target.y,
                                "stop_down"):
                            return
                        elif self.check_action(
                                self.action_approach, self.target.x,
                                self.target.y, "action_lock"):
                            return
                        else:
                            # Try a random action
                            action = self.get_spitball_action()
                    elif ydist <= MANTANOID_LEVEL_DISTANCE:
                        action = self.action_approach

        if action:
            self.perform_action(action)
        else:
            self.update_wander()

    def set_image(self):
        if not self.action:
            if self.was_on_floor:
                if self.xvelocity:
                    self.sprite = mantanoid_walk_sprite
                    self.image_speed = abs(self.xvelocity
                                           * MANTANOID_WALK_FRAMES_PER_PIXEL)
                else:
                    self.sprite = mantanoid_stand_sprite
                    if random.random() < 1 / (2*hlib.FPS):
                        self.sprite = mantanoid_idle_sprite
                        self.image_fps = None
                        self.image_index = 0
                        self.action = "animation"
            else:
                if self.yvelocity < 0:
                    self.sprite = mantanoid_jump_sprite
                else:
                    if self.sprite == mantanoid_jump_sprite:
                        self.sprite = mantanoid_fall_start_sprite
                        self.image_fps = None
                        self.image_index = 0
                        self.action = "animation"
                        if self.action_check_verify == "peak":
                            self.verify_action()
                    else:
                        self.sprite = mantanoid_fall_sprite

    def event_step(self, time_passed, delta_mult):
        on_floor = (self.get_bottom_touching_wall()
                    + self.get_bottom_touching_slope())
        self.can_act = (self.was_on_floor and on_floor and self.yvelocity >= 0)

        if not self.action and self.can_act:
            self.target = self.get_nearest_player()
            dist = 0
            if self.target is not None:
                xvec = self.target.x - self.x
                yvec = self.target.y - self.y
                dist = math.hypot(xvec, yvec)
                if dist > self.sight_distance:
                    self.target = None
                    self.has_approached = False

            self.update_action()

        if not self.action:
            self.xvelocity = self.movement_speed * self.image_xscale

            on_slope = self.get_bottom_touching_slope()
            if (on_floor or on_slope):
                if self.xvelocity < 0:
                    for tile in on_floor:
                        if tile.bbox_left < self.bbox_left:
                            break
                    else:
                        if not on_slope:
                            if self.can_act:
                                if self.target is not None:
                                    if (not self.check_action(
                                                self.action_hop, self.target.x,
                                                self.target.y, "stop_down")
                                            and not self.check_action(
                                                self.action_jump,
                                                self.target.x, self.target.y,
                                                "stop_down")
                                            and not self.check_action(
                                                self.action_approach,
                                                self.target.x, self.target.y,
                                                "stop_down")):
                                        self.target = None
                                else:
                                    self.perform_action(self.action_turn_right)
                            else:
                                self.xvelocity = 0
                else:
                    for tile in on_floor:
                        if tile.bbox_right > self.bbox_right:
                            break
                    else:
                        if not on_slope:
                            if self.can_act:
                                if self.target is not None:
                                    if (not self.check_action(
                                                self.action_hop, self.target.x,
                                                self.target.y, "stop_down") and
                                            not self.check_action(
                                                self.action_jump,
                                                self.target.x, self.target.y,
                                                "stop_down") and
                                            not self.check_action(
                                                self.action_approach,
                                                self.target.x, self.target.y,
                                                "stop_down")):
                                        self.target = None
                                else:
                                    self.perform_action(self.action_turn_left)
                            else:
                                self.xvelocity = 0

            self.set_image()

    def event_alarm(self, alarm_id):
        super().event_alarm(alarm_id)

        if alarm_id == "action_lock":
            if self.action_check_verify == "action_lock":
                self.verify_action()

    def event_animation_end(self):
        if self.action == "hop":
            self.action = None
            self.can_act = False
            self.set_image()
            if self.was_on_floor and (self.get_bottom_touching_wall()
                                      or self.get_bottom_touching_slope()):
                self.xvelocity = math.copysign(MANTANOID_APPROACH_SPEED,
                                               self.image_xscale)
                self.yvelocity = get_jump_speed(MANTANOID_HOP_HEIGHT,
                                                self.gravity)
        if self.action == "jump":
            self.action = None
            self.can_act = False
            self.set_image()
            if self.was_on_floor and (self.get_bottom_touching_wall()
                                      or self.get_bottom_touching_slope()):
                self.xvelocity = math.copysign(MANTANOID_APPROACH_SPEED,
                                               self.image_xscale)
                self.yvelocity = get_jump_speed(MANTANOID_JUMP_HEIGHT,
                                                self.gravity)
        elif self.action == "slash":
            hit_target = False

            w = MANTANOID_SLASH_BBOX_WIDTH
            h = MANTANOID_SLASH_BBOX_HEIGHT
            if self.image_xscale > 0:
                x = self.x + MANTANOID_SLASH_BBOX_X
                y = self.y + MANTANOID_SLASH_BBOX_Y
            else:
                x = self.x - MANTANOID_SLASH_BBOX_X - w
                y = self.y - MANTANOID_SLASH_BBOX_Y - h

            for other in sge.collision.rectangle(x, y, w, h):
                if isinstance(other, Player):
                    other.hurt(self.slash_damage)
                    if other is self.target:
                        hit_target = True
                elif isinstance(other, AnneroyBullet):
                    other.dissipate(other.xvelocity, other.yvelocity)

            double = False
            if self.target is not None and not hit_target:
                xdist = abs(self.target.x - self.x)
                ydist = abs(self.target.y - self.y)
                if (ydist <= MANTANOID_LEVEL_DISTANCE
                        and xdist <= MANTANOID_SLASH2_DISTANCE):
                    double = True

            play_sound(mantanoid_slash_sound, self.x, self.y)
            self.image_fps = None
            self.image_index = 0
            if double:
                self.sprite = mantanoid_slash_double_first_sprite
                self.action = "doubleslash"
            else:
                self.sprite = mantanoid_slash_single_sprite
                self.action = "animation"
        elif self.action == "doubleslash":
            self.move_x(MANTANOID_DOUBLESLASH_OFFSET * self.image_xscale)

            w = MANTANOID_SLASH2_BBOX_WIDTH
            h = MANTANOID_SLASH2_BBOX_HEIGHT
            if self.image_xscale > 0:
                x = self.x + MANTANOID_SLASH2_BBOX_X
                y = self.y + MANTANOID_SLASH2_BBOX_Y
            else:
                x = self.x - MANTANOID_SLASH2_BBOX_X - w
                y = self.y - MANTANOID_SLASH2_BBOX_Y - h

            for other in sge.collision.rectangle(x, y, w, h):
                if isinstance(other, Player):
                    other.hurt(self.slash_damage)
                elif isinstance(other, AnneroyBullet):
                    other.dissipate(other.xvelocity, other.yvelocity)

            play_sound(mantanoid_slash_sound, self.x, self.y)
            self.sprite = mantanoid_slash_double_second_sprite
            self.image_fps = None
            self.image_index = 0
            self.action = "animation"
        elif self.action == "animation":
            self.action = None
            self.set_image()


class MantanoidNoGo(sge.dsp.Object):

    def __init__(self, x, y, **kwargs):
        kwargs["visible"] = False
        kwargs["checks_collisions"] = False
        super().__init__(x, y, **kwargs)


class Boss(InteractiveObject):

    def __init__(self, x, y, ID="boss", death_timeline=None, stage=0,
                 **kwargs):
        self.ID = ID
        self.death_timeline = death_timeline
        self.stage = stage
        super().__init__(x, y, **kwargs)

    def event_create(self):
        super().event_create()
        sge.game.current_room.add_timeline_object(self)

    def event_destroy(self):
        for obj in sge.game.current_room.objects:
            if obj is not self and isinstance(obj, Boss) and obj.stage > 0:
                break
        else:
            if self.death_timeline:
                sge.game.current_room.load_timeline(self.death_timeline)


class LifeForce(InteractiveObject):

    def __init__(self, *args, **kwargs):
        kwargs["sprite"] = life_force_sprite
        super().__init__(*args, **kwargs)

    def move(self):
        if "set_direction" not in self.alarms:
            self.alarms["set_direction"] = hlib.FPS / 4
            target = self.get_nearest_player()
            if target is not None:
                xvec = target.x - self.image_xcenter
                yvec = max(target.y, target.bbox_top) - self.image_ycenter
                self.speed = LIFE_FORCE_SPEED
                self.move_direction = math.degrees(math.atan2(yvec, xvec))
            else:
                self.speed = 0

    def touch(self, other):
        other.hp += LIFE_FORCE_HEAL
        play_sound(heal_sound, other.x, other.y)
        self.destroy()


class Bullet(InteractiveObject):

    attacks_player = False
    attacks_enemy = False
    attacks_bullet = True
    attacks_wall = True
    breaks_stone = False
    player_damage = 5
    life = None

    def dissipate(self, xdirection=0, ydirection=0):
        """
        Show the appropriate dissipation animation for the bullet, based
        on what direction the bullet hit something in, and destroy the
        bullet.  Default behavior just calls "self.destroy()".
        """
        self.destroy()

    def shoot_player(self, other):
        other.hurt(self.player_damage)

    def shoot_enemy(self, other):
        other.shoot(self)

    def event_create(self):
        if self.life is not None:
            self.alarms["die"] = self.life

    def event_step(self, time_passed, delta_mult):
        room = sge.game.current_room
        if (self.bbox_right < 0 or self.bbox_left > room.width
                or self.bbox_bottom < 0 or self.bbox_top > room.height):
            self.destroy()

    def event_collision(self, other, xdirection, ydirection):
        super().event_collision(other, xdirection, ydirection)

        if isinstance(other, Player):
            if self.attacks_player:
                self.shoot_player(other)
                self.dissipate(xdirection, ydirection)
        elif isinstance(other, Bullet):
            if (self.attacks_bullet and
                    ((self.attacks_player and other.attacks_enemy)
                     or (self.attacks_enemy and other.attacks_player))):
                xd = math.copysign(1, other.xvelocity)
                yd = math.copysign(1, other.yvelocity)
                other.dissipate(xd, yd)
        elif isinstance(other, InteractiveObject) and other.shootable:
            if self.attacks_enemy:
                self.shoot_enemy(other)
                self.dissipate(xdirection, ydirection)
        elif isinstance(other, xsge_physics.Wall) and self.attacks_wall:
            point_x = self.x
            point_y = self.y
            if ((self.xvelocity > 0 and self.yvelocity > 0)
                    or (self.xvelocity < 0 and self.yvelocity < 0)):
                collisions = sge.collision.line(
                    self.bbox_left, self.bbox_top, self.bbox_right,
                    self.bbox_bottom)
            elif ((self.xvelocity > 0 and self.yvelocity < 0)
                  or (self.xvelocity < 0 and self.yvelocity > 0)):
                collisions = sge.collision.line(
                    self.bbox_left, self.bbox_bottom, self.bbox_right,
                    self.bbox_top)
            elif self.xvelocity:
                collisions = sge.collision.rectangle(
                    self.bbox_left, self.y, self.bbox_width, 1)
            elif self.yvelocity:
                collisions = sge.collision.rectangle(
                    self.x, self.bbox_top, 1, self.bbox_height)
            else:
                warnings.warn("Bullet is not moving!")
                collisions = []

            if self.xvelocity:
                if self.xvelocity > 0:
                    slope_cls = (xsge_physics.SlopeTopLeft,
                                 xsge_physics.SlopeBottomLeft)
                    cls = (xsge_physics.SolidLeft,) + slope_cls
                else:
                    slope_cls = (xsge_physics.SlopeTopRight,
                                 xsge_physics.SlopeBottomRight)
                    cls = (xsge_physics.SolidRight,) + slope_cls

                touching = False
                if collisions:
                    for obj in collisions:
                        if isinstance(obj, cls):
                            if isinstance(obj, slope_cls):
                                if self.xvelocity > 0:
                                    collision_real = (
                                        point_x > obj.get_slope_x(point_y))
                                else:
                                    collision_real = (
                                        point_x < obj.get_slope_x(point_y))
                            else:
                                collision_real = True

                            if collision_real:
                                touching = True
                                if (self.breaks_stone and
                                        isinstance(obj, Stone) and
                                        obj.shootable):
                                    obj.destroy()

                if touching:
                    self.dissipate(xdirection, ydirection)

            if self.yvelocity:
                if self.yvelocity > 0:
                    slope_cls = (xsge_physics.SlopeTopLeft,
                                 xsge_physics.SlopeTopRight)
                    cls = (xsge_physics.SolidTop,) + slope_cls
                else:
                    slope_cls = (xsge_physics.SlopeBottomLeft,
                                 xsge_physics.SlopeBottomRight)
                    cls = (xsge_physics.SolidBottom,) + slope_cls

                touching = False
                if collisions:
                    for obj in collisions:
                        if isinstance(obj, cls):
                            if isinstance(obj, slope_cls):
                                if self.yvelocity > 0:
                                    collision_real = (
                                        point_y > obj.get_slope_y(point_x))
                                else:
                                    collision_real = (
                                        point_y < obj.get_slope_y(point_x))
                            else:
                                collision_real = True

                            if collision_real:
                                touching = True
                                if (self.breaks_stone
                                        and isinstance(obj, Stone)
                                        and obj.shootable):
                                    obj.destroy()

                if touching:
                    self.dissipate(xdirection, ydirection)

    def event_alarm(self, alarm_id):
        if alarm_id == "die":
            self.destroy()


class AnneroyBullet(Bullet):

    attacks_enemy = True
    attacks_bullet = False
    breaks_stone = True
    life = ANNEROY_BULLET_LIFE

    def dissipate(self, xdirection=0, ydirection=0):
        if self not in sge.game.current_room.objects:
            return

        image_rotation = 0
        if abs(xdirection) > abs(ydirection):
            if xdirection < 0:
                image_rotation = 180
            else:
                image_rotation = 0
        elif abs(ydirection) > abs(xdirection):
            if ydirection < 0:
                image_rotation = 270
            else:
                image_rotation = 90
        elif abs(self.xvelocity) > abs(self.yvelocity):
            if self.xvelocity < 0:
                image_rotation = 180
            else:
                image_rotation = 0
        else:
            if self.yvelocity < 0:
                image_rotation = 270
            else:
                image_rotation = 90

        play_sound(bullet_death_sound, self.x, self.y)
        Smoke.create(
            self.x, self.y, self.z, sprite=anneroy_bullet_dissipate_sprite,
            regulate_origin=True, image_xscale=self.image_xscale,
            image_yscale=self.image_yscale, image_rotation=image_rotation,
            image_blend=self.image_blend)
        self.destroy()


class ScorpionBullet(Bullet):

    attacks_player = True
    player_damage = 15
    shard_num = 50
    shard_speed_min = 1
    shard_speed_max = 3

    def dissipate(self, xdirection=0, ydirection=0):
        self.destroy()
        play_sound(scorpion_projectile_break_sound, self.image_xcenter,
                   self.image_ycenter)

        for i in range(self.shard_num):
            life = random.uniform(hlib.FPS / 8, hlib.FPS / 2)
            image_index = random.randrange(
                0, scorpion_projectile_shard_sprite.frames)
            shard = xsge_particle.TimedParticle.create(
                self.x, self.y, self.z, life=life,
                sprite=scorpion_projectile_shard_sprite,
                image_index=image_index)
            shard.speed = random.randint(self.shard_speed_min,
                                         self.shard_speed_max)
            shard.move_direction = random.randrange(360)


class HedgehogSpikes(InteractiveObject):

    spike_hitstun = hlib.FPS / 4

    def event_collision(self, other, xdirection, ydirection):
        super().event_collision(other, xdirection, ydirection)

        if isinstance(other, InteractiveObject) and other.spikeable:
            if "spike_hitstun" not in other.alarms:
                other.spike(self)
                other.alarms["spike_hitstun"] = self.spike_hitstun
                
        elif isinstance(other, Stone) and other.spikeable:
            other.destroy()


class FakeTile(sge.dsp.Object):

    def event_create(self):
        self.tangible = False


class Stone(xsge_physics.Solid):

    shard_num_min = 1
    shard_num_max = 4
    shard_speed_min = 1
    shard_speed_max = 3
    shootable = False
    spikeable = False

    fakes = ()

    def event_create(self):
        self.checks_collisions = False
        self.fakes = []
        for other in sge.game.current_room.get_objects_at(
                self.image_left, self.image_top, self.image_width,
                self.image_height):
            if (isinstance(other, FakeTile)
                    and self.image_left < other.image_right
                    and self.image_right > other.image_left
                    and self.image_top < other.image_bottom
                    and self.image_bottom > other.image_top):
                self.fakes.append(other)

    def event_destroy(self):
        play_sound(stone_break_sound, self.image_xcenter, self.image_ycenter)

        for other in self.fakes:
            other.destroy()

        if sge.game.fps_real >= hlib.FPS:
            shard_num = random.randint(self.shard_num_min, self.shard_num_max)
        else:
            shard_num = self.shard_num_min

        for i in range(shard_num):
            shard = Shard.create(self.x, self.y, self.z,
                                 sprite=stone_fragment_sprite)
            shard.speed = random.randint(self.shard_speed_min,
                                         self.shard_speed_max)
            shard.move_direction = random.randrange(360)


class WeakStone(Stone):

    shootable = True
    spikeable = True


class SpikeStone(Stone):

    spikeable = True


class Macguffin(InteractiveObject):

    def touch(self, other):
        sge.snd.Music.clear_queue()
        sge.snd.Music.stop()
        play_sound(powerup_sound, self.image_xcenter, self.image_ycenter)

        msg1 = _("MACGUFFIN\n\n"
                 "This is the end of the demo! Thank you for playing Hexoshi "
                 "version {}.").format(__version__)
        msg2 = _("Don't worry; the full game will not end this way. This is "
                 "just a placeholder until the game is completed. We hope you "
                 "enjoyed what you have seen so far, and we hope you enjoy "
                 "the final game when it is finished!")
        DialogBox(gui_handler, msg1, self.sprite).show()
        DialogBox(gui_handler, msg2, self.sprite).show()

        sge.game.current_room.win_game()


class Powerup(InteractiveObject):

    @property
    def message(self):
        return _("USELESS OBJECT\n\nIt doesn't seem to do anything")

    def collect(self, other):
        pass

    def touch(self, other):
        global powerups
        global map_removed

        play_sound(powerup_sound, self.image_xcenter, self.image_ycenter)
        i = (self.__class__.__name__, sge.game.current_room.fname,
             int(self.x), int(self.y))
        powerups = powerups[:]
        powerups.append(i)

        # Remove the powerup from the map
        px = get_xregion(self.image_xcenter)
        py = get_yregion(self.image_ycenter)
        map_removed.append(("powerup", sge.game.current_room.fname, px, py))

        self.collect(other)

        for obj in sge.game.current_room.objects:
            if isinstance(obj, Player):
                obj.update_hud()

        DialogBox(gui_handler, self.message, self.sprite).show()
        self.destroy()

    def event_create(self):
        i = (self.__class__.__name__, sge.game.current_room.fname,
             int(self.x), int(self.y))
        if i in powerups:
            self.destroy()


class Artifact(Powerup):

    message = ""

    @property
    def message(self):
        return _("HEXOSHI ARTIFACT\n\n"
                 "{amt}/{total} ({pct}%)\n\n"
                 "Fire rate increased").format(
                     amt=artifacts, total=num_artifacts,
                     pct=int(100 * artifacts / max(num_artifacts, 1)))

    def collect(self, other):
        global artifacts
        artifacts += 1
        # TODO: Check to see if this is the last artifact, and set up a
        # victory condition if so.


class Etank(Powerup):

    @property
    def message(self):
        return _("E-TANK\n\nExtra energy capacity acquired")

    def collect(self, other):
        global etanks
        etanks += 1
        other.refresh()


class LifeOrb(Powerup):

    @property
    def message(self):
        return _('HEX ORB\n\n'
                 'Shoot bullets by pressing "shoot"\n\n'
                 'Collect Hexoshi Artifacts for faster fire rate')

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = life_orb_sprite
        super().__init__(x, y, **kwargs)

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("life_orb")


class Map(Powerup):

    @property
    def message(self):
        return _('HANDHELD MAP\n\n'
                 'See mini-map in HUD\n\n'
                 'See full map by pressing "map" or via pause menu')

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = powerup_map_sprite
        super().__init__(x, y, **kwargs)

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("map")


class MapDisk(Powerup):

    @property
    def message(self):
        return _("MAP DISK\n\nArea map data loaded")

    def __init__(self, x, y, rooms=None, **kwargs):
        if rooms:
            self.rooms = rooms.split(',')
        else:
            self.rooms = []
        super().__init__(x, y, **kwargs)

    def collect(self, other):
        global map_revealed

        for fname in self.rooms:
            sge.game.pump_input()
            if fname in map_rooms:
                room = Level.load(fname, True)
                rm_x, rm_y = map_rooms[fname]
                rm_w = int(math.ceil(room.width / hlib.SCREEN_SIZE[0]))
                rm_h = int(math.ceil(room.height / hlib.SCREEN_SIZE[1]))

                ignore_regions = set()
                for obj in room.objects:
                    sge.game.pump_input()
                    if isinstance(obj, IgnoreRegion):
                        rx1 = rm_x + get_xregion(obj.bbox_left)
                        rx2 = rm_x + get_xregion(obj.bbox_right - 1)
                        ry1 = rm_y + get_yregion(obj.bbox_top)
                        ry2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                        for ry in range(ry1, ry2 + 1):
                            for rx in range(rx1, rx2 + 1):
                                ignore_regions.add((rx, ry))

                for y in range(rm_y, rm_y + rm_h):
                    for x in range(rm_x, rm_x + rm_w):
                        sge.game.pump_input()
                        if ((x, y) not in ignore_regions
                                and (x, y) not in map_revealed):
                            map_revealed = map_revealed[:]
                            map_revealed.append((x, y))

        sge.game.regulate_speed()
        sge.game.pump_input()
        sge.game.input_events = []


class AtomicCompressor(Powerup):

    message = _('ATOMIC COMPRESSOR\n\n'
                'To compress: press "down" while crouching, or select with '
                '"mode" and then press "shoot"\n\n'
                'To uncompress: press "up"')

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = atomic_compressor_sprite
        super().__init__(x, y, **kwargs)

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("atomic_compressor")


class MonkeyBoots(Powerup):

    message = _('MONKEY BOOTS\n\n'
                'Press "jump" while touching a wall to wall-jump')

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = monkey_boots_sprite
        super().__init__(x, y, **kwargs)
        self.emitter = None

    def event_create(self):
        self.emitter = xsge_particle.Emitter.create(
            self.bbox_left, self.bbox_top, self.z + 0.5, interval=(hlib.FPS * 2),
            particle_cls=xsge_particle.AnimationParticle,
            particle_args=[self.x, self.y, self.z + 0.5],
            particle_kwargs={"sprite": monkey_boots_gleam_sprite},
            particle_lambda_args=[
                lambda e: random.uniform(e.x, e.x + 13),
                lambda e: random.uniform(e.y, e.y + 4)])

        super().event_create()

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("monkey_boots")

    def event_destroy(self):
        if self.emitter is not None:
            self.emitter.destroy()
            self.emitter = None


class HedgehogHormone(Powerup):

    message = _('HEDGEHOG HORMONE\n\n'
                'Press "shoot" while in the form of a ball to grow spikes')

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = hedgehog_hormone_sprite
        super().__init__(x, y, **kwargs)
        self.emitter = None

    def event_create(self):
        self.emitter = xsge_particle.Emitter.create(
            self.image_xcenter, self.bbox_top + 1, self.z - 0.5, interval=8,
            chance=0.5, particle_cls=xsge_particle.AnimationBubbleParticle,
            particle_args=[self.image_xcenter, self.bbox_top + 1, self.z - 0.5],
            particle_kwargs={"sprite": hedgehog_hormone_bubble_sprite,
                             "yvelocity": -0.25, "turn_factor": 20,
                             "min_angle": 225, "max_angle": 315})

        super().event_create()

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("hedgehog_hormone")

    def event_destroy(self):
        if self.emitter is not None:
            self.emitter.destroy()
            self.emitter = None


class Tunnel(InteractiveObject):

    def __init__(self, x, y, dest=None, **kwargs):
        self.dest = dest
        kwargs["visible"] = False
        kwargs["checks_collisions"] = False
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def touch(self, other):
        global spawn_xoffset
        global spawn_yoffset
        spawn_xoffset = other.x - self.x
        spawn_yoffset = other.y - self.y

        if self.dest:
            warp(self.dest)


class SpawnPoint(sge.dsp.Object):

    def __init__(self, x, y, spawn_id=None, spawn_direction=None, barrier=None,
                 **kwargs):
        self.spawn_id = spawn_id
        self.spawn_direction = spawn_direction
        self.barrier = barrier
        kwargs["visible"] = False
        kwargs["tangible"] = False
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def spawn(self, other):
        other.x = self.x + spawn_xoffset
        other.y = self.y + spawn_yoffset
        if self.spawn_direction == 0:
            other.bbox_left = self.bbox_right
        elif self.spawn_direction == 90:
            other.bbox_top = self.bbox_bottom
        elif self.spawn_direction == 180:
            other.bbox_right = self.bbox_left
        elif self.spawn_direction == 270:
            other.bbox_bottom = self.bbox_top
            other.yvelocity = get_jump_speed(hlib.TILE_SIZE / 2, other.gravity)

        other.init_position()

    def event_create(self):
        if spawn_point == self.spawn_id:
            for obj in sge.game.current_room.objects:
                if isinstance(obj, Player):
                    self.spawn(obj)

            if self.barrier is not None:
                self.barrier.image_index = self.barrier.sprite.frames - 1
                self.barrier.image_speed = -self.barrier.sprite.speed
                play_sound(door_close_sound, self.barrier.image_xcenter,
                           self.barrier.image_ycenter)


class WarpPad(SpawnPoint):

    message = _('WARP PAD\n\nProgress saved. Press "up" to teleport.')

    def __init__(self, x, y, spawn_id="save", **kwargs):
        self.spawn_id = spawn_id
        self.spawn_direction = None
        self.barrier = None
        self.created = False
        self.activated = False
        kwargs["sprite"] = warp_pad_inactive_sprite
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def activate(self):
        global current_level
        global spawn_point
        global warp_pads

        self.activated = True
        self.sprite = warp_pad_active_sprite
        current_level = sge.game.current_room.fname
        spawn_point = self.spawn_id
        x = get_xregion(self.image_xcenter)
        y = get_yregion(self.image_ycenter)
        i = (sge.game.current_room.fname, self.spawn_id, x, y)
        if i not in warp_pads:
            warp_pads = warp_pads[:]
            warp_pads.append(i)

    def spawn(self, other):
        if not self.created:
            self.create_children()
        other.x = self.image_xcenter
        other.bbox_bottom = self.image_top
        other.z = self.z - 0.5
        other.init_position()
        other.warp_in()
        other.refresh()
        self.activate()
        save_game()
        play_sound(teleport_sound, self.image_xcenter, self.image_ycenter)

    def teleport(self, other):
        x = get_xregion(self.image_xcenter)
        y = get_yregion(self.image_ycenter)
        i = (sge.game.current_room.fname, self.spawn_id, x, y)
        dlg = TeleportDialog(i)
        dlg.show()
        if dlg.selection and dlg.selection != i:
            other.x = self.image_xcenter
            other.bbox_bottom = self.image_top
            other.warp_dest = "{}:{}".format(*dlg.selection[:2])
            other.warp_out()
            play_sound(teleport_sound, self.image_xcenter, self.image_ycenter)

    def create_children(self):
        self.created = True
        self.bbox_x = 8
        self.bbox_y = -4
        self.bbox_width = 32
        self.bbox_height = 4
        Solid.create(self.x + 8, self.y, bbox_width=32, bbox_height=8)
        SlopeTopLeft.create(self.x, self.y, bbox_width=8, bbox_height=8)
        SlopeTopRight.create(self.x + 40, self.y, bbox_width=8, bbox_height=8)

    def event_create(self):
        super().event_create()
        if not self.created:
            self.create_children()

    def event_collision(self, other, xdirection, ydirection):
        global progress_flags

        if isinstance(other, Player):
            if xdirection or ydirection:
                if not self.activated:
                    self.activate()
                    other.refresh()
                    play_sound(warp_pad_sound, self.image_xcenter,
                               self.image_ycenter)

                    if "warp" not in progress_flags:
                        progress_flags.append("warp")
                        DialogBox(gui_handler, self.message).show()

                save_game()


class DoorBarrier(InteractiveObject, xsge_physics.Solid):

    shootable = True
    spikeable = True

    parent = None

    def shoot(self, other):
        if self.parent is not None:
            self.parent.shoot(other)

    def event_animation_end(self):
        self.image_speed = 0
        if self.tangible:
            self.image_index = 0
        else:
            self.image_index = self.sprite.frames - 1


class DoorFrame(InteractiveObject):

    shootable = True
    spikeable = True

    closed_sprite = None
    open_sprite = None
    barrier_sprite = None
    edge1_area = (0, 0, 8, 8)
    edge2_area = (0, 56, 8, 8)

    def __init__(self, x, y, **kwargs):
        self.edge1 = None
        self.edge2 = None
        self.barrier = None
        kwargs["tangible"] = False
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def shoot(self, other):
        if self.barrier is not None:
            self.sprite = self.open_sprite
            self.barrier.tangible = False
            self.barrier.image_speed = self.barrier.sprite.speed
            play_sound(door_open_sound, self.barrier.image_xcenter,
                       self.barrier.image_ycenter)

    def event_create(self):
        self.sprite = self.closed_sprite
        x, y, w, h = self.edge1_area
        self.edge1 = Solid.create(self.x + x, self.y + y, bbox_width=w,
                                  bbox_height=h)
        x, y, w, h = self.edge2_area
        self.edge2 = Solid.create(self.x + x, self.y + y, bbox_width=w,
                                  bbox_height=h)

        self.barrier = DoorBarrier.create(self.x, self.y, self.z,
                                          sprite=self.barrier_sprite,
                                          image_index=0, image_fps=0)
        self.barrier.parent = self


class DoorFrameX(DoorFrame):

    def event_create(self):
        self.closed_sprite = doorframe_regular_x_closed_sprite
        self.open_sprite = doorframe_regular_x_open_sprite
        self.barrier_sprite = door_barrier_x_sprite
        super().event_create()


class DoorFrameY(DoorFrame):

    edge2_area = (56, 0, 8, 8)

    def event_create(self):
        self.closed_sprite = doorframe_regular_y_closed_sprite
        self.open_sprite = doorframe_regular_y_open_sprite
        self.barrier_sprite = door_barrier_y_sprite
        super().event_create()


class Door(sge.dsp.Object):

    def __init__(self, x, y, dest=None, spawn_id=None, **kwargs):
        self.dest = dest
        self.spawn_id = spawn_id
        if not spawn_id and dest:
            if ':' in dest:
                level_f, spawn = dest.split(':', 1)
                if level_f:
                    self.spawn_id = level_f
            else:
                self.spawn_id = dest
        kwargs["visible"] = False
        kwargs["tangible"] = False
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def event_create(self):
        self.destroy()


class LeftDoor(Door):

    def event_create(self):
        frame = DoorFrameX.create(self.x, self.y, z=self.z)
        Tunnel.create(frame.barrier.bbox_left - hlib.TILE_SIZE,
                      frame.barrier.bbox_top, dest=self.dest,
                      bbox_width=hlib.TILE_SIZE,
                      bbox_height=frame.barrier.bbox_height)
        SpawnPoint.create(frame.barrier.bbox_left, frame.barrier.bbox_top,
                          spawn_id=self.spawn_id, spawn_direction=0,
                          barrier=frame.barrier,
                          bbox_width=frame.barrier.bbox_width,
                          bbox_height=frame.barrier.bbox_height)
        self.destroy()


class RightDoor(Door):

    def event_create(self):
        frame = DoorFrameX.create(self.x, self.y, z=self.z)
        Tunnel.create(frame.barrier.bbox_right, frame.barrier.bbox_top,
                      dest=self.dest, bbox_width=hlib.TILE_SIZE,
                      bbox_height=frame.barrier.bbox_height)
        SpawnPoint.create(frame.barrier.bbox_left, frame.barrier.bbox_top,
                          spawn_id=self.spawn_id, spawn_direction=180,
                          barrier=frame.barrier,
                          bbox_width=frame.barrier.bbox_width,
                          bbox_height=frame.barrier.bbox_height)
        self.destroy()


class UpDoor(Door):

    def event_create(self):
        frame = DoorFrameY.create(self.x, self.y, z=self.z)
        Tunnel.create(frame.barrier.bbox_left,
                      frame.barrier.bbox_top - hlib.TILE_SIZE, dest=self.dest,
                      bbox_width=frame.barrier.bbox_width,
                      bbox_height=hlib.TILE_SIZE)
        SpawnPoint.create(frame.barrier.bbox_left, frame.barrier.bbox_top,
                          spawn_id=self.spawn_id, spawn_direction=90,
                          barrier=frame.barrier,
                          bbox_width=frame.barrier.bbox_width,
                          bbox_height=frame.barrier.bbox_height)
        self.destroy()


class DownDoor(Door):

    def event_create(self):
        frame = DoorFrameY.create(self.x, self.y, z=self.z)
        Tunnel.create(frame.barrier.bbox_left, frame.barrier.bbox_bottom,
                      dest=self.dest, bbox_width=frame.barrier.bbox_width,
                      bbox_height=hlib.TILE_SIZE)
        SpawnPoint.create(frame.barrier.bbox_left, frame.barrier.bbox_top,
                          spawn_id=self.spawn_id, spawn_direction=270,
                          barrier=frame.barrier,
                          bbox_width=frame.barrier.bbox_width,
                          bbox_height=frame.barrier.bbox_height)
        self.destroy()


class TimelineSwitcher(InteractiveObject):

    def __init__(self, x, y, timeline=None, **kwargs):
        self.timeline = timeline
        kwargs["visible"] = False
        kwargs["checks_collisions"] = False
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def touch(self, other):
        sge.game.current_room.load_timeline(self.timeline)
        self.destroy()


class MovingObjectPath(xsge_path.PathLink):

    cls = None
    default_speed = PLAYER_MAX_SPEED
    default_accel = None
    default_decel = None
    default_loop = None
    auto_follow = True

    def __init__(self, x, y, path_speed=None, path_accel=None, path_decel=None,
                 path_loop=None, path_id=None, prime=False, parent=None,
                 **kwargs):
        if path_speed is None:
            path_speed = self.default_speed
        if path_accel is None:
            path_accel = self.default_accel
        if path_decel is None:
            path_decel = self.default_decel
        if path_loop is None:
            path_loop = self.default_loop

        self.path_speed = path_speed
        self.path_accel = path_accel if path_accel != -1 else None
        self.path_decel = path_decel if path_decel != -1 else None
        self.path_loop = path_loop if path_loop != -1 else None
        self.path_id = path_id
        self.prime = prime
        self.parent = parent
        self.obj = lambda: None
        super().__init__(x, y, **kwargs)

    def event_create(self):
        if self.parent is not None:
            for obj in sge.game.current_room.objects:
                if (isinstance(obj, self.__class__)
                        and obj.path_id == self.parent):
                    obj.next_path = self
                    obj.next_speed = self.path_speed
                    obj.next_accel = self.path_accel
                    obj.next_decel = self.path_decel
                    obj.next_loop = self.path_loop
                    break
        else:
            self.prime = True

        if self.prime and self.cls in TYPES:
            obj = TYPES[self.cls].create(self.x, self.y, z=self.z)
            self.obj = weakref.ref(obj)
            if self.auto_follow:
                self.follow_start(obj, self.path_speed, accel=self.path_accel,
                                  decel=self.path_decel, loop=self.path_loop)


class MovingPlatformPath(MovingObjectPath):

    cls = "moving_platform"
    default_speed = 3
    default_accel = 0.02
    default_decel = 0.02

    def event_create(self):
        super().event_create()
        obj = self.obj()
        if obj:
            obj.path = self

    def follow_start(self, obj, *args, **kwargs):
        super().follow_start(obj, *args, **kwargs)
        obj.following = True

    def event_follow_end(self, obj):
        obj.following = False
        obj.speed = 0
        obj.x = self.x + self.points[-1][0]
        obj.y = self.y + self.points[-1][1]


class TriggeredMovingPlatformPath(MovingPlatformPath):

    default_speed = 2
    default_accel = None
    default_decel = None
    auto_follow = False
    followed = False


class CircoflamePath(xsge_path.Path):

    def __init__(self, x, y, z=0, points=(), rvelocity=2):
        self.rvelocity = rvelocity
        x += hlib.TILE_SIZE / 2
        y += hlib.TILE_SIZE / 2
        super().__init__(x, y, z=z, points=points)

    def event_create(self):
        if self.points:
            fx, fy = self.points[0]
            radius = math.hypot(fx, fy)
            pos = math.degrees(math.atan2(fy, fx))
            CircoflameCenter.create(self.x, self.y, z=self.z, radius=radius,
                                    pos=pos, rvelocity=self.rvelocity)
        self.destroy()


class PlayerLayer(sge.dsp.Object):

    def event_create(self):
        sge.game.current_room.player_z = self.z
        for obj in sge.game.current_room.objects:
            if isinstance(obj, Player):
                obj.z = self.z
        self.destroy()


class CameraGuide(sge.dsp.Object):

    def __init__(self, x, y, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super().__init__(x, y, **kwargs)


class CameraXGuide(CameraGuide):

    pass


class CameraYGuide(CameraGuide):

    pass


class MapHint(sge.dsp.Object):

    def event_create(self):
        self.alarms["destroy"] = 1

    def event_alarm(self, alarm_id):
        if alarm_id == "destroy":
            self.destroy()


class MapLeftWall(MapHint):

    pass


class MapRightWall(MapHint):

    pass


class MapTopWall(MapHint):

    pass


class MapBottomWall(MapHint):

    pass


class MapLeftDoor(MapHint):

    pass


class MapRightDoor(MapHint):

    pass


class MapTopDoor(MapHint):

    pass


class MapBottomDoor(MapHint):

    pass


class IgnoreRegion(MapHint):

    pass


class Menu(xsge_gui.MenuWindow):

    items = []

    @classmethod
    def create(cls, default=0):
        if cls.items:
            self = cls.from_text(
                gui_handler, sge.game.width / 2, sge.game.height * 2 / 3,
                cls.items, font_normal=font,
                color_normal=menu_text_color,
                color_selected=menu_text_selected_color,
                background_color=menu_color, margin=4, halign="center",
                valign="middle")
            default %= len(self.widgets)
            self.keyboard_focused_widget = self.widgets[default]
            self.show()
            return self

    def event_change_keyboard_focus(self):
        play_sound(select_sound)


class MainMenu(Menu):

    items = [_("New Game"), _("Load Game"), _("Options"), _("Credits"),
             _("Quit")]

    def event_choose(self):
        if self.choice == 0:
            play_sound(confirm_sound)
            NewGameMenu.create_page()
        elif self.choice == 1:
            play_sound(confirm_sound)
            LoadGameMenu.create_page()
        elif self.choice == 2:
            play_sound(confirm_sound)
            OptionsMenu.create_page()
        elif self.choice == 3:
            credits_room = CreditsScreen.load(os.path.join("special",
                                                           "credits.json"))
            credits_room.start()
        else:
            sge.game.end()


class NewGameMenu(Menu):

    @classmethod
    def create_page(cls, default=0):
        cls.items = []
        for slot in save_slots:
            if slot is None:
                cls.items.append(_("-Empty-"))
            else:
                name = slot.get("player_name", "Anneroy")
                etanks = slot.get("etanks", 0)
                if etanks:
                    text = "{} {}".format(name, ETANK_CHAR * etanks)
                else:
                    text = name
                cls.items.append(text)

        cls.items.append(_("Back"))

        return cls.create(default)

    def event_choose(self):
        global abort
        global current_save_slot

        abort = False

        if self.choice in range(len(save_slots)):
            play_sound(confirm_sound)
            current_save_slot = self.choice
            if save_slots[current_save_slot] is None:
                set_new_game()
                if not abort:
                    start_game()
                else:
                    NewGameMenu.create(default=self.choice)
            else:
                OverwriteConfirmMenu.create(default=1)
        else:
            play_sound(cancel_sound)
            MainMenu.create(default=0)


class OverwriteConfirmMenu(Menu):

    items = [_("Overwrite this save file"), _("Cancel")]

    def event_choose(self):
        global abort

        abort = False

        if self.choice == 0:
            play_sound(confirm_sound)
            set_new_game()
            if not abort:
                start_game()
            else:
                play_sound(cancel_sound)
                NewGameMenu.create(default=current_save_slot)
        else:
            play_sound(cancel_sound)
            NewGameMenu.create(default=current_save_slot)


class LoadGameMenu(NewGameMenu):

    def event_choose(self):
        global abort
        global current_save_slot

        abort = False

        if self.choice in range(len(save_slots)):
            play_sound(confirm_sound)
            current_save_slot = self.choice
            load_game()
            if abort:
                MainMenu.create(default=1)
            elif not start_game():
                play_sound(error_sound)
                show_error(_("An error occurred when trying to load the game."))
                MainMenu.create(default=1)
        else:
            play_sound(cancel_sound)
            MainMenu.create(default=1)


class OptionsMenu(Menu):

    @classmethod
    def create_page(cls, default=0):
        smt = scale_method if scale_method else "fastest"
        cls.items = [
            _("Fullscreen: {}").format(_("On") if fullscreen else _("Off")),
            _("Scale Method: {}").format(smt),
            _("Sound: {}").format(_("On") if sound_enabled else _("Off")),
            _("Music: {}").format(_("On") if music_enabled else _("Off")),
            _("Stereo: {}").format(_("On") if stereo_enabled else _("Off")),
            _("Show FPS: {}").format(_("On") if fps_enabled else _("Off")),
            _("Metroid-Style Aiming: {}").format(_("On") if metroid_controls else _("Off")),
            _("Joystick Threshold: {}%").format(int(joystick_threshold * 100)),
            _("Configure keyboard"), _("Configure joysticks"),
            _("Detect joysticks"), _("Back")]
        return cls.create(default)

    def event_choose(self):
        global fullscreen
        global scale_method
        global sound_enabled
        global music_enabled
        global stereo_enabled
        global fps_enabled
        global metroid_controls
        global joystick_threshold

        if self.choice == 0:
            play_sound(select_sound)
            fullscreen = not fullscreen
            update_fullscreen()
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 1:
            choices = [None, "noblur", "smooth"] + sge.SCALE_METHODS
            if scale_method in choices:
                i = choices.index(scale_method)
            else:
                i = 0

            play_sound(select_sound)
            i += 1
            i %= len(choices)
            scale_method = choices[i]
            sge.game.scale_method = scale_method
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 2:
            sound_enabled = not sound_enabled
            play_sound(teleport_sound)
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 3:
            music_enabled = not music_enabled
            play_music(sge.game.current_room.music,
                       noloop=sge.game.current_room.music_noloop)
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 4:
            stereo_enabled = not stereo_enabled
            play_sound(confirm_sound)
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 5:
            play_sound(select_sound)
            fps_enabled = not fps_enabled
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 6:
            play_sound(select_sound)
            metroid_controls = not metroid_controls
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 7:
            play_sound(select_sound)
            # This somewhat complicated method is to prevent rounding
            # irregularities.
            threshold = ((int(joystick_threshold*100) + 5) % 100) / 100
            if not threshold:
                threshold = 0.0001
            joystick_threshold = threshold
            xsge_gui.joystick_threshold = threshold
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 8:
            play_sound(confirm_sound)
            KeyboardMenu.create_page()
        elif self.choice == 9:
            play_sound(confirm_sound)
            JoystickMenu.create_page()
        elif self.choice == 10:
            sge.joystick.refresh()
            play_sound(heal_sound)
            OptionsMenu.create_page(default=self.choice)
        else:
            play_sound(cancel_sound)
            write_to_disk()
            MainMenu.create(default=2)


class KeyboardMenu(Menu):

    page = 0

    @classmethod
    def create_page(cls, default=0, page=0):
        page %= min(len(left_key), len(right_key), len(up_key), len(down_key),
                    len(jump_key), len(shoot_key), len(aim_diag_key),
                    len(aim_up_key), len(aim_down_key), len(mode_reset_key),
                    len(mode_key), len(pause_key), len(map_key))

        def format_key(key):
            if key:
                return " ".join(key)
            else:
                return None

        cls.items = [_("Player {}").format(page + 1),
                     _("Left: {}").format(format_key(left_key[page])),
                     _("Right: {}").format(format_key(right_key[page])),
                     _("Up: {}").format(format_key(up_key[page])),
                     _("Down: {}").format(format_key(down_key[page])),
                     _("Jump: {}").format(format_key(jump_key[page])),
                     _("Shoot: {}").format(format_key(shoot_key[page])),
                     _("Aim Diagonal: {}").format(format_key(aim_diag_key[page])),
                     _("Aim Up: {}").format(format_key(aim_up_key[page])),
                     _("Aim Down: {}").format(format_key(aim_down_key[page])),
                     _("Reset Mode: {}").format(format_key(mode_reset_key[page])),
                     _("Mode: {}").format(format_key(mode_key[page])),
                     _("Pause: {}").format(format_key(pause_key[page])),
                     _("Map: {}").format(format_key(map_key[page])),
                     _("Back")]
        self = cls.create(default)
        self.page = page
        return self

    def event_choose(self):
        def bind_key(key, new_key, self=self):
            for other_key in [
                    left_key[self.page], right_key[self.page],
                    up_key[self.page], down_key[self.page],
                    jump_key[self.page], shoot_key[self.page],
                    aim_diag_key[self.page], aim_up_key[self.page],
                    aim_down_key[self.page], mode_reset_key[self.page],
                    mode_key[self.page], pause_key[self.page],
                    map_key[self.page]]:
                if new_key in other_key:
                    other_key.remove(new_key)

            key.append(new_key)
            while len(key) > 2:
                key.pop(0)

        text = _("Press the key you wish to bind to this function, or the "
                 "Escape key to cancel.")

        if self.choice == 0:
            play_sound(select_sound)
            self.__class__.create_page(default=self.choice, page=(self.page + 1))
        elif self.choice == 1:
            k = wait_key(text)
            if k is not None:
                bind_key(left_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 2:
            k = wait_key(text)
            if k is not None:
                bind_key(right_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 3:
            k = wait_key(text)
            if k is not None:
                bind_key(up_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 4:
            k = wait_key(text)
            if k is not None:
                bind_key(down_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 5:
            k = wait_key(text)
            if k is not None:
                bind_key(jump_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 6:
            k = wait_key(text)
            if k is not None:
                bind_key(shoot_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 7:
            k = wait_key(text)
            if k is not None:
                bind_key(aim_diag_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 8:
            k = wait_key(text)
            if k is not None:
                bind_key(aim_up_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 9:
            k = wait_key(text)
            if k is not None:
                bind_key(aim_down_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 10:
            k = wait_key(text)
            if k is not None:
                bind_key(mode_reset_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 11:
            k = wait_key(text)
            if k is not None:
                bind_key(mode_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 12:
            k = wait_key(text)
            if k is not None:
                bind_key(pause_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 13:
            k = wait_key(text)
            if k is not None:
                bind_key(map_key[self.page], k)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        else:
            play_sound(cancel_sound)
            OptionsMenu.create_page(default=5)


class JoystickMenu(Menu):

    page = 0

    @classmethod
    def create_page(cls, default=0, page=0):
        page %= min(len(left_js), len(right_js), len(up_js), len(down_js),
                    len(jump_js), len(shoot_js), len(aim_diag_js),
                    len(aim_up_js), len(aim_down_js), len(mode_reset_js),
                    len(mode_js), len(pause_js), len(map_js))

        def format_js(js):
            js_template = "{},{},{}"
            sL = []
            for j in js:
                sL.append(js_template.format(*j))
            if sL:
                return " ".join(sL)
            else:
                return _("None")

        cls.items = [_("Player {}").format(page + 1),
                     _("Left: {}").format(format_js(left_js[page])),
                     _("Right: {}").format(format_js(right_js[page])),
                     _("Up: {}").format(format_js(up_js[page])),
                     _("Down: {}").format(format_js(down_js[page])),
                     _("Jump: {}").format(format_js(jump_js[page])),
                     _("Shoot: {}").format(format_js(shoot_js[page])),
                     _("Aim Diagonal: {}").format(format_js(aim_diag_js[page])),
                     _("Aim Up: {}").format(format_js(aim_up_js[page])),
                     _("Aim Down: {}").format(format_js(aim_down_js[page])),
                     _("Reset Mode: {}").format(format_js(mode_reset_js[page])),
                     _("Mode: {}").format(format_js(mode_js[page])),
                     _("Pause: {}").format(format_js(pause_js[page])),
                     _("Map: {}").format(format_js(map_js[page])),
                     _("Back")]
        self = cls.create(default)
        self.page = page
        return self

    def event_choose(self):
        def bind_js(js, new_js, self=self):
            for other_js in [
                    left_js[self.page], right_js[self.page],
                    up_js[self.page], down_js[self.page],
                    jump_js[self.page], shoot_js[self.page],
                    aim_diag_js[self.page], aim_up_js[self.page],
                    aim_down_js[self.page], mode_reset_js[self.page],
                    mode_js[self.page], pause_js[self.page],
                    map_js[self.page]]:
                if new_js in other_js:
                    other_js.remove(new_js)

            js.append(new_js)
            while len(js) > 2:
                js.pop(0)

        text = _("Press the joystick button, axis, or hat direction you wish "
                 "to bind to this function, or the Escape key to cancel.")

        if self.choice == 0:
            play_sound(select_sound)
            self.__class__.create_page(default=self.choice, page=self.page + 1)
        elif self.choice == 1:
            js = wait_js(text)
            if js is not None:
                bind_js(left_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 2:
            js = wait_js(text)
            if js is not None:
                bind_js(right_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 3:
            js = wait_js(text)
            if js is not None:
                bind_js(up_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 4:
            js = wait_js(text)
            if js is not None:
                bind_js(down_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 5:
            js = wait_js(text)
            if js is not None:
                bind_js(jump_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 6:
            js = wait_js(text)
            if js is not None:
                bind_js(shoot_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 7:
            js = wait_js(text)
            if js is not None:
                bind_js(aim_diag_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 8:
            js = wait_js(text)
            if js is not None:
                bind_js(aim_up_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 9:
            js = wait_js(text)
            if js is not None:
                bind_js(aim_down_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 10:
            js = wait_js(text)
            if js is not None:
                bind_js(mode_reset_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 11:
            js = wait_js(text)
            if js is not None:
                bind_js(mode_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 12:
            js = wait_js(text)
            if js is not None:
                bind_js(pause_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        elif self.choice == 13:
            js = wait_js(text)
            if js is not None:
                bind_js(map_js[self.page], js)
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            self.__class__.create_page(default=self.choice, page=self.page)
        else:
            play_sound(cancel_sound)
            OptionsMenu.create_page(default=6)


class ModalMenu(xsge_gui.MenuDialog):

    items = []

    @classmethod
    def create(cls, default=0):
        if cls.items:
            self = cls.from_text(
                gui_handler, sge.game.width / 2, sge.game.height / 2,
                cls.items, font_normal=font,
                color_normal=menu_text_color,
                color_selected=menu_text_selected_color,
                background_color=menu_color, margin=9, halign="center",
                valign="middle")
            default %= len(self.widgets)
            self.keyboard_focused_widget = self.widgets[default]
            sge.game.refresh()
            self.show()
            return self

    def event_change_keyboard_focus(self):
        play_sound(select_sound)


class PauseMenu(ModalMenu):

    @classmethod
    def create(cls, default=0, player_x=None, player_y=None):
        if "map" in progress_flags:
            items = [_("Continue"), _("View Stats"), _("Configure keyboard"),
                     _("Configure joysticks"), _("View Map"),
                     _("Return to Title Screen")]
        else:
            items = [_("Continue"), _("View Stats"), _("Configure keyboard"),
                     _("Configure joysticks"), _("Return to Title Screen")]

        self = cls.from_text(
            gui_handler, sge.game.width / 2, sge.game.height / 2,
            items, font_normal=font, color_normal=menu_text_color,
            color_selected=menu_text_selected_color,
            background_color=menu_color, margin=9, halign="center",
            valign="middle")
        default %= len(self.widgets)
        self.keyboard_focused_widget = self.widgets[default]
        self.player_x = player_x
        self.player_y = player_y
        sge.game.refresh()
        self.show()
        return self

    def event_choose(self):
        self.hide()
        sge.game.refresh()

        def check_quit():
            if current_save_slot is not None:
                slot = save_slots[current_save_slot]
            else:
                slot = {}

            if (slot.get("map_revealed") == map_revealed and
                    slot.get("map_explored") == map_explored and
                    slot.get("map_removed") == map_removed and
                    slot.get("warp_pads") == warp_pads and
                    slot.get("powerups") == powerups and
                    slot.get("progress_flags") == progress_flags and
                    slot.get("artifacts") == artifacts and
                    slot.get("etanks") == etanks):
                sge.game.start_room.start()
            else:
                text = _("Some progress has not been saved. If you leave the "
                         "game now, this unsaved progress will be lost. You "
                         "can save the game by touching any warp pad.")
                DialogBox(gui_handler, text).show()
                play_sound(type_sound)
                LoseProgressMenu.create(1)

        if self.choice == 1:
            seconds = int(time_taken % 60)
            minutes = int((time_taken/60) % 60)
            hours = int(time_taken / 3600)
            powerups_col = len(powerups) - artifacts
            text = _("PLAYER STATISTICS\n\n"
                     "Time spent: {hours}:{minutes:02}:{seconds:02}\n"
                     "Powerups collected: {powerups} ({powerups_percent}%)\n"
                     "Artifacts collected: {artifacts} "
                     "({artifacts_percent}%)").format(
                         hours=hours, minutes=minutes, seconds=seconds,
                         powerups=powerups_col,
                         powerups_percent=int(100 * powerups_col
                                              / max(num_powerups, 1)),
                         artifacts=artifacts,
                         artifacts_percent=int(100 * artifacts
                                               / max(num_artifacts, 1)))

            DialogBox(gui_handler, text).show()
            PauseMenu.create(default=self.choice, player_x=self.player_x,
                             player_y=self.player_y)
        elif self.choice == 2:
            play_sound(confirm_sound)
            ModalKeyboardMenu.create_page()
            PauseMenu.create(default=self.choice, player_x=self.player_x,
                             player_y=self.player_y)
        elif self.choice == 3:
            play_sound(confirm_sound)
            ModalJoystickMenu.create_page()
            PauseMenu.create(default=self.choice, player_x=self.player_x,
                             player_y=self.player_y)
        elif self.choice == 4:
            if "map" in progress_flags:
                play_sound(select_sound)
                MapDialog(self.player_x, self.player_y).show()
            else:
                check_quit()
        elif self.choice == 5:
            check_quit()
        else:
            play_sound(select_sound)


class ModalKeyboardMenu(ModalMenu, KeyboardMenu):

    def event_choose(self):
        self.hide()
        sge.game.refresh()
        if self.choice is not None and self.choice < len(self.items) - 1:
            super().event_choose()
        else:
            play_sound(cancel_sound)


class ModalJoystickMenu(ModalMenu, JoystickMenu):

    def event_choose(self):
        self.hide()
        sge.game.refresh()
        if self.choice is not None and self.choice < len(self.items) - 1:
            super().event_choose()
        else:
            play_sound(cancel_sound)


class LoseProgressMenu(ModalMenu):

    items = [_("Abandon unsaved progress"), _("Return to game")]

    def event_choose(self):
        if self.choice == 0:
            sge.game.start_room.start()
        else:
            play_sound(select_sound)


class MapDialog(xsge_gui.Dialog):

    def __init__(self, player_x, player_y):
        if player_x is None:
            player_x = 0
        if player_y is None:
            player_y = 0

        xcells = int(sge.game.width / MAP_CELL_WIDTH)
        ycells = int(sge.game.height / MAP_CELL_HEIGHT)
        w = sge.game.width
        h = sge.game.height
        super().__init__(
            gui_handler, 0, 0, w, h, background_color=sge.gfx.Color("black"),
            border=False)
        self.map = xsge_gui.Widget(self, 0, 0, 0)
        self.map.sprite = draw_map(player_x=player_x, player_y=player_y)
        self.map.tab_focus = False
        self.left = 0
        self.top = 0
        for rx, ry in set(map_revealed + map_explored):
            self.left = min(self.left, rx)
            self.top = min(self.top, ry)
        player_x -= self.left
        player_y -= self.top
        self.map.x = (xcells // 2 - player_x) * MAP_CELL_WIDTH
        self.map.y = (ycells // 2 - player_y) * MAP_CELL_HEIGHT

    def event_press_left(self):
        play_sound(select_sound)
        self.map.x += MAP_CELL_WIDTH

    def event_press_right(self):
        play_sound(select_sound)
        self.map.x -= MAP_CELL_WIDTH

    def event_press_up(self):
        play_sound(select_sound)
        self.map.y += MAP_CELL_HEIGHT

    def event_press_down(self):
        play_sound(select_sound)
        self.map.y -= MAP_CELL_HEIGHT

    def event_press_enter(self):
        play_sound(select_sound)
        self.destroy()

    def event_press_escape(self):
        play_sound(select_sound)
        self.destroy()


class TeleportDialog(MapDialog):

    def __init__(self, selection):
        self.selection = selection
        w = sge.game.width
        h = sge.game.height
        xsge_gui.Dialog.__init__(
            self, gui_handler, 0, 0, w, h,
            background_color=sge.gfx.Color("black"), border=False)
        self.map = xsge_gui.Widget(self, 0, 0, 0)
        self.map.sprite = draw_map()
        self.map.tab_focus = False
        self.location_indicator = xsge_gui.Widget(self, 0, 0, 1)
        self.location_indicator.sprite = map_player_sprite
        self.location_indicator.tab_focus = False

        self.left = 0
        self.top = 0
        for rx, ry in set(map_revealed + map_explored):
            self.left = min(self.left, rx)
            self.top = min(self.top, ry)

        xcells = int(sge.game.width / MAP_CELL_WIDTH)
        ycells = int(sge.game.height / MAP_CELL_HEIGHT)
        self.location_indicator.x = (xcells//2) * MAP_CELL_WIDTH
        self.location_indicator.y = (ycells//2) * MAP_CELL_HEIGHT

        self.update_selection()

    def update_selection(self):
        if self.selection[0] in map_rooms:
            xcells = int(sge.game.width / MAP_CELL_WIDTH)
            ycells = int(sge.game.height / MAP_CELL_HEIGHT)
            x, y = map_rooms[self.selection[0]]
            x += self.selection[2] - self.left
            y += self.selection[3] - self.top
            self.map.x = (xcells//2 - x) * MAP_CELL_WIDTH
            self.map.y = (ycells//2 - y) * MAP_CELL_HEIGHT

    def event_press_left(self):
        play_sound(select_sound)

        if self.selection in warp_pads:
            i = warp_pads.index(self.selection)
        else:
            i = 0

        self.selection = warp_pads[(i-1) % len(warp_pads)]
        self.update_selection()

    def event_press_right(self):
        play_sound(select_sound)

        if self.selection in warp_pads:
            i = warp_pads.index(self.selection)
        else:
            i = -1

        self.selection = warp_pads[(i+1) % len(warp_pads)]
        self.update_selection()

    def event_press_up(self):
        pass

    def event_press_down(self):
        pass

    def event_press_enter(self):
        self.destroy()

    def event_press_escape(self):
        self.selection = None
        self.destroy()


class DialogLabel(xsge_gui.ProgressiveLabel):

    def event_add_character(self):
        if not self.text[-1].isspace():
            play_sound(type_sound)


class DialogBox(xsge_gui.Dialog):

    def __init__(self, parent, text, portrait=None, rate=TEXT_SPEED):
        width = sge.game.width / 2
        x_padding = 16
        y_padding = 16
        label_x = 8
        label_y = 8
        if portrait is not None:
            x_padding += 8
            label_x += 8
            portrait_w = portrait.width
            portrait_h = portrait.height
            label_x += portrait_w
        else:
            portrait_w = 0
            portrait_h = 0
        label_w = max(1, width - portrait_w - x_padding)
        height = max(1, portrait_h + y_padding,
                     font.get_height(text, width=label_w) + y_padding)
        x = sge.game.width/2 - width/2
        y = sge.game.height/2 - height/2
        super().__init__(parent, x, y, width, height,
                         background_color=menu_color, border=False)
        label_h = max(1, height - y_padding)

        self.label = DialogLabel(self, label_x, label_y, 0, text, font=font,
                                 width=label_w, height=label_h,
                                 color=sge.gfx.Color("white"), rate=rate)

        if portrait is not None:
            xsge_gui.Widget(self, 8, 8, 0, sprite=portrait)

    def event_press_enter(self):
        if len(self.label.text) < len(self.label.full_text):
            self.label.text = self.label.full_text
        else:
            self.destroy()

    def event_press_escape(self):
        self.destroy()
        room = sge.game.current_room
        if (isinstance(room, Level)
                and room.timeline_skip_target is not None
                and room.timeline_step < room.timeline_skip_target):
            room.timeline_skipto(room.timeline_skip_target)


def get_object(x, y, cls=None, **kwargs):
    cls = TYPES.get(cls, xsge_tiled.Decoration)
    return cls(x, y, **kwargs)


def get_scaled_copy(obj):
    s = obj.sprite.copy()
    if obj.image_xscale < 0:
        s.mirror()
    if obj.image_yscale < 0:
        s.flip()
    s.width *= abs(obj.image_xscale)
    s.height *= abs(obj.image_yscale)
    s.rotate(obj.image_rotation)
    s.origin_x = obj.image_origin_x
    s.origin_y = obj.image_origin_y
    return s


def get_jump_speed(height, gravity=GRAVITY):
    # Get the speed to achieve a given height using a kinematic
    # equation: v[f]^2 = v[i]^2 + 2ad
    return -math.sqrt(2 * gravity * height)


def get_xregion(x):
    return int(x / hlib.SCREEN_SIZE[0])


def get_yregion(y):
    return int(y / hlib.SCREEN_SIZE[1])


def warp(dest):
    global spawn_point

    if ":" in dest:
        level_f, spawn_point = dest.split(':', 1)
    else:
        level_f = dest
        spawn_point = sge.game.current_room.fname

    if level_f:
        level = sge.game.current_room.__class__.load(level_f)
    else:
        level = sge.game.current_room

    if level is not None:
        level.start()
    else:
        sge.game.start_room.start()


def set_gui_controls():
    # Set the controls for xsge_gui.
    xsge_gui.next_widget_keys = ["down", "tab", "s", "kp_2"]
    xsge_gui.previous_widget_keys = ["up", "w", "kp_8"]
    xsge_gui.left_keys = ["left", "a", "kp_4"]
    xsge_gui.right_keys = ["right", "d", "kp_6"]
    xsge_gui.up_keys = []
    xsge_gui.down_keys = []
    xsge_gui.enter_keys = ["enter", "kp_enter", "space", "end"]
    xsge_gui.escape_keys = ["escape"]
    xsge_gui.next_widget_joystick_events = [
        (0, "axis+", 1), (0, "hat_down", 0)]
    xsge_gui.previous_widget_joystick_events = [
        (0, "axis-", 1), (0, "hat_up", 0)]
    xsge_gui.left_joystick_events = [(0, "axis-", 0), (0, "hat_left", 0)]
    xsge_gui.right_joystick_events = [(0, "axis+", 0), (0, "hat_right", 0)]
    xsge_gui.up_joystick_events = []
    xsge_gui.down_joystick_events = []
    xsge_gui.enter_joystick_events = [
        (0, "button", 0), (0, "button", 1), (0, "button", 2), (0, "button", 3),
        (0, "button", 9)]
    xsge_gui.escape_joystick_events = [(0, "button", 8)]


def wait_key(text):
    # Wait for a key press and return it.
    while True:
        # Input events
        sge.game.pump_input()
        while sge.game.input_events:
            event = sge.game.input_events.pop(0)
            if isinstance(event, sge.input.KeyPress):
                sge.game.pump_input()
                sge.game.input_events = []
                if event.key == "escape":
                    return None
                else:
                    return event.key

        # Regulate speed
        sge.game.regulate_speed(fps=10)

        # Project text
        sge.game.project_text(font, text, sge.game.width / 2,
                              sge.game.height / 2, width=sge.game.width,
                              height=sge.game.height,
                              color=sge.gfx.Color("white"),
                              halign="center", valign="middle")

        # Refresh
        sge.game.refresh()


def wait_js(text):
    # Wait for a joystick press and return it.
    sge.game.pump_input()
    sge.game.input_events = []

    while True:
        # Input events
        sge.game.pump_input()
        while sge.game.input_events:
            event = sge.game.input_events.pop(0)
            if isinstance(event, sge.input.KeyPress):
                if event.key == "escape":
                    sge.game.pump_input()
                    sge.game.input_events = []
                    return None
            elif isinstance(event, sge.input.JoystickEvent):
                if (event.input_type not in {"axis0", "hat_center_x",
                                             "hat_center_y"}
                        and event.value >= joystick_threshold):
                    sge.game.pump_input()
                    sge.game.input_events = []
                    return (event.js_id, event.input_type, event.input_id)

        # Regulate speed
        sge.game.regulate_speed(fps=10)

        # Project text
        sge.game.project_text(font, text, sge.game.width / 2,
                              sge.game.height / 2, width=sge.game.width,
                              height=sge.game.height,
                              color=sge.gfx.Color("white"),
                              halign="center", valign="middle")

        # Refresh
        sge.game.refresh()


def show_error(message):
    print(message)
    raise


def play_sound(sound, x=None, y=None, force=True):
    if sound_enabled and sound:
        if x is None or y is None:
            sound.play(force=force)
        else:
            current_view = None
            view_x = 0
            view_y = 0
            dist = 0
            for view in sge.game.current_room.views:
                vx = view.x + view.width/2
                vy = view.y + view.height/2
                new_dist = math.hypot(vx - x, vy - y)
                if current_view is None or new_dist < dist:
                    current_view = view
                    view_x = vx
                    view_y = vy
                    dist = new_dist

            bl = min(x, view_x)
            bw = abs(x - view_x)
            bt = min(y, view_y)
            bh = abs(y - view_y)
            for obj in sge.game.current_room.get_objects_at(bl, bt, bw, bh):
                if isinstance(obj, Player):
                    new_dist = math.hypot(obj.x - x, obj.y - y)
                    if new_dist < dist:
                        view_x = obj.x
                        view_y = obj.y
                        dist = new_dist

            if dist <= SOUND_MAX_RADIUS:
                volume = 1
            elif dist < SOUND_ZERO_RADIUS:
                rng = SOUND_ZERO_RADIUS - SOUND_MAX_RADIUS
                reldist = rng - (dist-SOUND_MAX_RADIUS)
                volume = min(1, abs(reldist / rng))
            else:
                # No point in continuing; it's too far away
                return

            if stereo_enabled:
                hdist = x - view_x
                if abs(hdist) < SOUND_CENTERED_RADIUS:
                    balance = 0
                else:
                    rng = SOUND_TILTED_RADIUS - SOUND_CENTERED_RADIUS
                    balance = max(-SOUND_TILT_LIMIT,
                                  min(hdist / rng, SOUND_TILT_LIMIT))
            else:
                balance = 0

            sound.play(volume=volume, balance=balance, force=force)


def play_music(music, force_restart=False, noloop=False):
    """Play the given music file, starting with its start piece."""
    if music_enabled:
        loops = 1 if noloop else None
        if music:
            music_object = loaded_music.get(music)
            if music_object is None:
                try:
                    music_object = sge.snd.Music(os.path.join(hlib.datadir, "music",
                                                              music))
                except OSError:
                    sge.snd.Music.clear_queue()
                    sge.snd.Music.stop()
                    return
                else:
                    loaded_music[music] = music_object

            name, ext = os.path.splitext(music)
            music_start = ''.join([name, "-start", ext])
            music_start_object = loaded_music.get(music_start)
            if music_start_object is None:
                try:
                    music_start_object = sge.snd.Music(os.path.join(
                        hlib.datadir, "music", music_start))
                except OSError:
                    pass
                else:
                    loaded_music[music_start] = music_start_object

            if (force_restart or (not music_object.playing
                                  and (music_start_object is None
                                       or not music_start_object.playing))):
                sge.snd.Music.clear_queue()
                sge.snd.Music.stop()
                if music_start_object is not None:
                    music_start_object.play()
                    music_object.queue(loops=loops)
                else:
                    music_object.play(loops=loops)
        else:
            sge.snd.Music.clear_queue()
            sge.snd.Music.stop(fade_time=1000)
    else:
        sge.snd.Music.clear_queue()
        sge.snd.Music.stop()


def set_new_game():
    global player_name
    global watched_timelines
    global current_level
    global spawn_point
    global warp_pads
    global map_revealed
    global map_explored
    global map_removed
    global powerups
    global progress_flags
    global artifacts
    global etanks
    global time_taken

    player_name = "Anneroy"
    watched_timelines = []
    current_level = None
    spawn_point = "save"
    map_revealed = []
    map_explored = []
    map_removed = []
    warp_pads = []
    powerups = []
    progress_flags = []
    artifacts = 0
    etanks = 0
    time_taken = 0


def write_to_disk():
    # Write our saves and settings to disk.
    keys_cfg = {"left": left_key, "right": right_key, "up": up_key,
                "down": down_key, "aim_diag": aim_diag_key, "jump": jump_key,
                "shoot": shoot_key, "aim_up": aim_up_key,
                "aim_down": aim_down_key, "mode_reset": mode_reset_key,
                "mode": mode_key, "pause": pause_key, "map": map_key}
    js_cfg = {"left": left_js, "right": right_js, "up": up_js,
              "down": down_js, "aim_diag": aim_diag_js, "jump": jump_js,
              "shoot": shoot_js, "aim_up": aim_up_js, "aim_down": aim_down_js,
              "mode_reset": mode_reset_js, "mode": mode_js, "pause": pause_js,
              "map": map_js}

    cfg = {"version": 1, "fullscreen": fullscreen,
           "scale_method": scale_method, "sound_enabled": sound_enabled,
           "music_enabled": music_enabled, "stereo_enabled": stereo_enabled,
           "fps_enabled": fps_enabled, "metroid_controls": metroid_controls,
           "joystick_threshold": joystick_threshold, "keys": keys_cfg,
           "joystick": js_cfg}

    with open(os.path.join(hlib.configdir, "config.json"), 'w') as f:
        json.dump(cfg, f, indent=4)

    if DIST_AI:
        # Save to hlib.datadir instead.
        with open(os.path.join(hlib.datadir, "ai_data.json"), 'w') as f:
            json.dump(ai_data, f, indent=4)

        # Remove the local file since it's now redundant.
        fd = os.path.join(hlib.localdir, "ai_data.json")
        if os.path.exists(fd):
            os.remove(fd)
    else:
        with open(os.path.join(hlib.localdir, "ai_data.json"), 'w') as f:
            json.dump(ai_data, f)

    with open(os.path.join(hlib.localdir, "save_slots.json"), 'w') as f:
        json.dump(save_slots, f, indent=4)


def save_game():
    global save_slots

    if current_save_slot is not None:
        save_slots[current_save_slot] = {
            "save_format": 1,
            "player_name": player_name,
            "watched_timelines": watched_timelines[:],
            "current_level": current_level,
            "spawn_point": spawn_point,
            "map_revealed": map_revealed[:],
            "map_explored": map_explored[:],
            "map_removed": map_removed[:],
            "warp_pads": warp_pads[:],
            "powerups": powerups[:],
            "progress_flags": progress_flags[:],
            "artifacts": artifacts,
            "etanks": etanks,
            "time_taken": time_taken}

    write_to_disk()


def load_game():
    global player_name
    global watched_timelines
    global current_level
    global spawn_point
    global map_revealed
    global map_explored
    global map_removed
    global warp_pads
    global powerups
    global progress_flags
    global etanks
    global time_taken

    if (current_save_slot is not None
            and save_slots[current_save_slot] is not None):
        slot = save_slots[current_save_slot]
        save_format = slot.get("save_format", 0)

        if save_format == 1:
            player_name = slot.get("player_name", "Anneroy")
            watched_timelines = slot.get("watched_timelines", [])
            current_level = slot.get("current_level")
            spawn_point = slot.get("spawn_point")
            map_revealed = [tuple(i) for i in slot.get("map_revealed", [])]
            map_explored = [tuple(i) for i in slot.get("map_explored", [])]
            map_removed = [tuple(i) for i in slot.get("map_removed", [])]
            warp_pads = [tuple(i) for i in slot.get("warp_pads", [])]
            powerups = [tuple(i) for i in slot.get("powerups", [])]
            progress_flags = slot.get("progress_flags", [])
            artifacts = slot.get("artifacts", 0)
            etanks = slot.get("etanks", 0)
            time_taken = slot.get("time_taken", 0)
    else:
        set_new_game()


def start_game():
    global player

    player = Anneroy(0, 0)

    if current_level is None:
        level = SpecialScreen.load("special/intro.json")
    else:
        level = Level.load(current_level)

    if level is not None:
        level.start()
    else:
        return False

    return True


def generate_map():
    global map_rooms
    global map_objects
    global num_powerups
    global num_artifacts

    print(_("Generating new map files; this may take some time."))
    files_checked = set()
    files_remaining = {("0.json", 0, 0, None, None)}
    map_rooms = {}
    map_objects = {}
    num_powerups = 0
    num_artifacts = 0

    while files_remaining:
        fname, rm_x, rm_y, origin_level, origin_spawn = files_remaining.pop()
        files_checked.add(fname)
        room = Level.load(fname, True)
        rm_w = int(math.ceil(room.width / hlib.SCREEN_SIZE[0]))
        rm_h = int(math.ceil(room.height / hlib.SCREEN_SIZE[1]))

        for obj in room.objects:
            if isinstance(obj, Door):
                if ":" in obj.dest:
                    level_f, spawn = obj.dest.split(':', 1)
                else:
                    level_f = obj.dest
                    spawn = fname

                if level_f == origin_level and spawn == origin_spawn:
                    if isinstance(obj, LeftDoor):
                        rm_x += 1
                    elif isinstance(obj, RightDoor):
                        rm_x -= 1
                    elif isinstance(obj, UpDoor):
                        rm_y += 1
                    elif isinstance(obj, DownDoor):
                        rm_y -= 1

                    rm_x -= get_xregion(obj.image_xcenter)
                    rm_y -= get_yregion(obj.image_ycenter)

                    origin = None
                    break

        map_rooms[fname] = (rm_x, rm_y)

        ignore_regions = set()
        for obj in room.objects:
            if isinstance(obj, IgnoreRegion):
                rx1 = rm_x + get_xregion(obj.bbox_left)
                rx2 = rm_x + get_xregion(obj.bbox_right - 1)
                ry1 = rm_y + get_yregion(obj.bbox_top)
                ry2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for ry in range(ry1, ry2 + 1):
                    for rx in range(rx1, rx2 + 1):
                        ignore_regions.add((rx, ry))

        for obj in room.objects:
            if isinstance(obj, Door):
                dx = rm_x + get_xregion(obj.image_xcenter)
                dy = rm_y + get_yregion(obj.image_ycenter)

                if ":" in obj.dest:
                    level_f, spawn = obj.dest.split(':', 1)
                else:
                    level_f = obj.dest
                    spawn = fname

                if level_f not in files_checked:
                    files_remaining.add((level_f, dx, dy, fname, obj.spawn_id))
                    files_checked.add(level_f)

                if (dx, dy) in ignore_regions:
                    continue

                if isinstance(obj, LeftDoor):
                    map_objects.setdefault((dx, dy), []).append("door_left")
                elif isinstance(obj, RightDoor):
                    map_objects.setdefault((dx, dy), []).append("door_right")
                elif isinstance(obj, UpDoor):
                    map_objects.setdefault((dx, dy), []).append("door_top")
                elif isinstance(obj, DownDoor):
                    map_objects.setdefault((dx, dy), []).append("door_bottom")
            elif isinstance(obj, WarpPad):
                wx = rm_x + get_xregion(obj.image_xcenter)
                wy = rm_y + get_yregion(obj.image_ycenter)
                if (wx, wy) not in ignore_regions:
                    map_objects.setdefault((wx, wy), []).append("warp_pad")
            elif isinstance(obj, Powerup):
                if isinstance(obj, Artifact):
                    num_artifacts += 1
                else:
                    num_powerups += 1

                px = rm_x + get_xregion(obj.image_xcenter)
                py = rm_y + get_yregion(obj.image_ycenter)
                if (px, py) not in ignore_regions:
                    map_objects.setdefault((px, py), []).append("powerup")
            elif isinstance(obj, MapLeftWall):
                wx = rm_x + get_xregion(obj.bbox_left)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_left")
            elif isinstance(obj, MapRightWall):
                wx = rm_x + get_xregion(obj.bbox_right - 1)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_right")
            elif isinstance(obj, MapTopWall):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_top)
                for wx in range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_top")
            elif isinstance(obj, MapBottomWall):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wx in range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_bottom")
            elif isinstance(obj, MapLeftDoor):
                wx = rm_x + get_xregion(obj.bbox_left)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_left")
            elif isinstance(obj, MapRightDoor):
                wx = rm_x + get_xregion(obj.bbox_right - 1)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_right")
            elif isinstance(obj, MapTopDoor):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_top)
                for wx in range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_top")
            elif isinstance(obj, MapBottomDoor):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wx in range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_bottom")

        for x in range(rm_x, rm_x + rm_w):
            y = rm_y
            if ((x, y) not in ignore_regions
                    and "door_top" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_top")

            y = rm_y + rm_h - 1
            if ((x, y) not in ignore_regions
                    and "door_bottom" not in map_objects.setdefault((x, y),
                                                                    [])):
                map_objects[(x, y)].append("wall_bottom")

        for y in range(rm_y, rm_y + rm_h):
            x = rm_x
            if ((x, y) not in ignore_regions
                    and "door_left" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_left")

            x = rm_x + rm_w - 1
            if ((x, y) not in ignore_regions
                    and "door_right" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_right")

    f_objects = {}
    for x, y in map_objects:
        i = "{},{}".format(x, y)
        f_objects[i] = map_objects[(x, y)]

    info = {"powerups": num_powerups, "artifacts": num_artifacts}

    try:
        with open(os.path.join(hlib.datadir, "map", "rooms.json"), 'w') as f:
            json.dump(map_rooms, f, indent=4, sort_keys=True)

        with open(os.path.join(hlib.datadir, "map", "objects.json"), 'w') as f:
            json.dump(f_objects, f, indent=4, sort_keys=True)

        with open(os.path.join(hlib.datadir, "map", "info.json"), 'w') as f:
            json.dump(info, f, indent=4, sort_keys=True)
    except PermissionError as e:
        warnings.warn(f"Could not save generated map files - {e}")


def draw_map(x=None, y=None, w=None, h=None, player_x=None, player_y=None):
    if x is None or y is None or w is None or h is None:
        left = 0
        right = 0
        top = 0
        bottom = 0
        for rx, ry in set(map_revealed + map_explored):
            left = min(left, rx)
            right = max(right, rx)
            top = min(top, ry)
            bottom = max(bottom, ry)

        if x is None:
            x = left
        if y is None:
            y = top
        if w is None:
            w = right - x + 1
        if h is None:
            h = bottom - y + 1

    removed = []
    for obj, fname, ox, oy in map_removed:
        if fname in map_rooms:
            rm_x, rm_y = map_rooms[fname]
            removed.append((obj, rm_x + ox, rm_y + oy))
    s_w = w * MAP_CELL_WIDTH
    s_h = h * MAP_CELL_HEIGHT
    map_sprite = sge.gfx.Sprite(width=s_w, height=s_h)
    map_sprite.draw_rectangle(0, 0, s_w, s_h, fill=sge.gfx.Color("black"))

    for ex, ey in map_explored:
        dx = (ex - x) * MAP_CELL_WIDTH
        dy = (ey - y) * MAP_CELL_HEIGHT
        map_sprite.draw_rectangle(dx, dy, MAP_CELL_WIDTH, MAP_CELL_HEIGHT,
                                  fill=sge.gfx.Color((170, 68, 153)))

    for ox, oy in set(map_objects) & set(map_revealed + map_explored):
        if x <= ox < x + w and y <= oy < y + h:
            for obj in map_objects[(ox, oy)]:
                if (obj, ox, oy) in removed:
                    removed.remove((obj, ox, oy))
                    continue

                dx = (ox-x) * MAP_CELL_WIDTH
                dy = (oy-y) * MAP_CELL_HEIGHT
                if obj == "wall_left":
                    map_sprite.draw_sprite(map_wall_left_sprite, 0, dx, dy)
                elif obj == "wall_right":
                    map_sprite.draw_sprite(map_wall_right_sprite, 0, dx, dy)
                elif obj == "wall_top":
                    map_sprite.draw_sprite(map_wall_top_sprite, 0, dx, dy)
                elif obj == "wall_bottom":
                    map_sprite.draw_sprite(map_wall_bottom_sprite, 0, dx, dy)
                elif obj == "door_left":
                    map_sprite.draw_sprite(map_door_left_sprite, 0, dx, dy)
                elif obj == "door_right":
                    map_sprite.draw_sprite(map_door_right_sprite, 0, dx, dy)
                elif obj == "door_top":
                    map_sprite.draw_sprite(map_door_top_sprite, 0, dx, dy)
                elif obj == "door_bottom":
                    map_sprite.draw_sprite(map_door_bottom_sprite, 0, dx, dy)
                elif obj == "powerup":
                    if "warp_pad" not in map_objects[(ox, oy)]:
                        map_sprite.draw_sprite(map_powerup_sprite, 0, dx, dy)
                elif obj == "warp_pad":
                    map_sprite.draw_sprite(map_warp_pad_sprite, 0, dx, dy)

    if player_x is not None and player_y is not None:
        dx = (player_x - x) * MAP_CELL_WIDTH
        dy = (player_y - y) * MAP_CELL_HEIGHT
        map_sprite.draw_sprite(map_player_sprite, 0, dx, dy)

    return map_sprite


def update_fullscreen():
    if fullscreen:
        sge.game.scale = hlib.fsscale or None
        sge.game.fullscreen = True
    else:
        sge.game.fullscreen = False
        sge.game.scale = hlib.scale
        sge.game.scale = None


TYPES = {
    "solid_left": SolidLeft, "solid_right": SolidRight, "solid_top": SolidTop,
    "solid_bottom": SolidBottom, "solid": Solid, "slope_topleft": SlopeTopLeft,
    "slope_topright": SlopeTopRight, "slope_bottomleft": SlopeBottomLeft,
    "slope_bottomright": SlopeBottomRight, "moving_platform": MovingPlatform,
    "spike_left": SpikeLeft, "spike_right": SpikeRight, "spike_top": SpikeTop,
    "spike_bottom": SpikeBottom, "death": Death,

    "frog": Frog, "hedgehog": Hedgehog, "bat": Bat, "jellyfish": Jellyfish,
    "worm": Worm, "scorpion": Scorpion, "mantanoid": Mantanoid,

    "fake_tile": FakeTile, "weak_stone": WeakStone, "spike_stone": SpikeStone,

    "macguffin": Macguffin, "artifact": Artifact, "etank": Etank,
    "life_orb": LifeOrb, "map": Map, "map_disk": MapDisk,
    "atomic_compressor": AtomicCompressor, "monkey_boots": MonkeyBoots,
    "hedgehog_hormone": HedgehogHormone,

    "warp_pad": WarpPad, "doorframe_x": DoorFrameX, "doorframe_y": DoorFrameY,
    "door_left": LeftDoor, "door_right": RightDoor, "door_up": UpDoor,
    "door_down": DownDoor,

    "timeline_switcher": TimelineSwitcher,

    "enemies": get_object, "doors": get_object, "stones": get_object,
    "powerups": get_object, "objects": get_object,

    "moving_platform_path": MovingPlatformPath,
    "triggered_moving_platform_path": TriggeredMovingPlatformPath,

    "player": PlayerLayer,

    "camera_x_guide": CameraXGuide, "camera_y_guide": CameraYGuide,
    "map_wall_left": MapLeftWall, "map_wall_right": MapRightWall,
    "map_wall_top": MapTopWall, "map_wall_bottom": MapBottomWall,
    "map_door_left": MapLeftDoor, "map_door_right": MapRightDoor,
    "map_door_top": MapTopDoor, "map_door_bottom": MapBottomDoor,
    "map_ignore_region": IgnoreRegion, "mantanoid_nogo": MantanoidNoGo
    }


print(_("Initializing game system..."))
Game(*hlib.SCREEN_SIZE, scale=hlib.scale, fps=hlib.FPS, delta=DELTA,
     delta_min=hlib.DELTA_MIN, delta_max=hlib.DELTA_MAX,
     window_text="Hexoshi DEMO {}".format(__version__))
     #window_icon=os.path.join(hlib.datadir, "images", "misc", "icon.png"))
sge.game.scale = None

print(_("Initializing GUI system..."))
xsge_gui.init()
gui_handler = xsge_gui.Handler()
xsge_gui.default_font.size = 8
xsge_gui.textbox_font.size = 8

menu_color = sge.gfx.Color("black")
menu_text_color = sge.gfx.Color((64, 0, 255))
menu_text_selected_color = sge.gfx.Color("white")

print(_("Loading resources..."))

if not os.path.exists(hlib.configdir):
    os.makedirs(hlib.configdir)

if not os.path.exists(hlib.localdir):
    os.makedirs(hlib.localdir)

# Save error messages to a text file (so they aren't lost).
if not PRINT_ERRORS:
    stderr = os.path.join(hlib.localdir, "stderr.txt")
    if not os.path.isfile(stderr) or os.path.getsize(stderr) > 1000000:
        sys.stderr = open(stderr, 'w')
    else:
        sys.stderr = open(stderr, 'a')
    dt = datetime.datetime.now()
    sys.stderr.write("\n{}-{}-{} {}:{}:{}\n".format(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))
    del dt

# Load sprites
d = os.path.join(hlib.datadir, "images", "objects", "anneroy")
anneroy_torso_offset = {}

fname = os.path.join(d, "anneroy_sheet.png")

anneroy_turn_sprite = sge.gfx.Sprite.from_tileset(
    fname, 2, 109, 3, xsep=3, width=39, height=43, origin_x=19, origin_y=19,
    fps=10)
anneroy_teleport_sprite = sge.gfx.Sprite.from_tileset(
    fname, 360, 455, 7, xsep=4, width=46, height=49, origin_x=23, origin_y=25,
    fps=20)
anneroy_wall_right_sprite = sge.gfx.Sprite.from_tileset(
    fname, 439, 228, 2, xsep=5, width=32, height=45, origin_x=23, origin_y=19,
    fps=10)
anneroy_wall_left_sprite = sge.gfx.Sprite.from_tileset(
    fname, 439, 284, 2, xsep=5, width=31, height=45, origin_x=9, origin_y=19,
    fps=10)
anneroy_walljump_left_sprite = sge.gfx.Sprite.from_tileset(
    fname, 522, 229, width=34, height=46, origin_x=17, origin_y=20)
anneroy_walljump_right_sprite = sge.gfx.Sprite.from_tileset(
    fname, 522, 283, width=34, height=46, origin_x=15, origin_y=20)
anneroy_compress_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 393, 3, xsep=5, width=27, height=32, origin_x=12, origin_y=8,
    fps=15)
anneroy_ball_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 440, 8, xsep=8, width=16, height=16, origin_x=8, origin_y=-8)
anneroy_decompress_fail_sprite = sge.gfx.Sprite.from_tileset(
    fname, 150, 393, 3, xsep=5, width=27, height=32, origin_x=12, origin_y=8,
    fps=15)
anneroy_hedgehog_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 469, 8, xsep=3, width=38, height=38, origin_x=19, origin_y=3)
anneroy_hedgehog_extend_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 510, 8, xsep=3, width=38, height=38, origin_x=19, origin_y=3)
anneroy_hedgehog_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 551, 8, xsep=3, width=38, height=38, origin_x=19, origin_y=3)
anneroy_death_right_sprite = sge.gfx.Sprite.from_tileset(
    fname, 5, 597, 7, xsep=5, width=86, height=82, origin_x=40, origin_y=38,
    fps=10)
anneroy_death_left_sprite = sge.gfx.Sprite.from_tileset(
    fname, 5, 684, 7, xsep=5, width=86, height=82, origin_x=46, origin_y=38,
    fps=10)
anneroy_explode_sprite = sge.gfx.Sprite.from_tileset(
    fname, 369, 771, 3, xsep=5, width=86, height=82, origin_x=43, origin_y=38,
    fps=10)
anneroy_explode_fragments = sge.gfx.Sprite.from_tileset(
    fname, 406, 582, 21, xsep=3, width=6, height=6, origin_x=3, origin_y=3)

anneroy_torso_right_idle_sprite = sge.gfx.Sprite.from_tileset(
    fname, 317, 45, width=26, height=27, origin_x=9, origin_y=19)
anneroy_torso_right_aim_right_sprite = sge.gfx.Sprite.from_tileset(
    fname, 234, 45, width=26, height=20, origin_x=5, origin_y=19)
anneroy_torso_right_aim_up_sprite = sge.gfx.Sprite.from_tileset(
    fname, 293, 38, width=20, height=27, origin_x=6, origin_y=26)
anneroy_torso_right_aim_down_sprite = sge.gfx.Sprite.from_tileset(
    fname, 182, 52, width=20, height=30, origin_x=1, origin_y=12)
anneroy_torso_right_aim_upright_sprite = sge.gfx.Sprite.from_tileset(
    fname, 264, 39, width=25, height=26, origin_x=5, origin_y=25)
anneroy_torso_right_aim_downright_sprite = sge.gfx.Sprite.from_tileset(
    fname, 207, 45, width=23, height=26, origin_x=5, origin_y=19)

anneroy_torso_left_idle_sprite = sge.gfx.Sprite.from_tileset(
    fname, 14, 45, width=27, height=25, origin_x=18, origin_y=19)
anneroy_torso_left_aim_left_sprite = sge.gfx.Sprite.from_tileset(
    fname, 95, 45, width=26, height=20, origin_x=20, origin_y=19)
anneroy_torso_left_aim_up_sprite = sge.gfx.Sprite.from_tileset(
    fname, 45, 38, width=17, height=27, origin_x=11, origin_y=26)
anneroy_torso_left_aim_down_sprite = sge.gfx.Sprite.from_tileset(
    fname, 154, 52, width=20, height=30, origin_x=18, origin_y=12)
anneroy_torso_left_aim_upleft_sprite = sge.gfx.Sprite.from_tileset(
    fname, 66, 39, width=25, height=26, origin_x=19, origin_y=25)
anneroy_torso_left_aim_downleft_sprite = sge.gfx.Sprite.from_tileset(
    fname, 125, 45, width=23, height=26, origin_x=17, origin_y=19)

anneroy_legs_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 47, 76, width=19, height=24, origin_x=8, origin_y=0)
anneroy_legs_run_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 299, 5, 2, xsep=8, ysep=31, width=40, height=24, origin_x=17,
    origin_y=0)
anneroy_legs_jump_sprite = sge.gfx.Sprite.from_tileset(
    fname, 14, 234, 5, xsep=15, width=23, height=29, origin_x=8, origin_y=5,
    fps=30)
anneroy_legs_fall_sprite = sge.gfx.Sprite.from_tileset(
    fname, 204, 234, width=23, height=29, origin_x=8, origin_y=5)
anneroy_legs_land_sprite = sge.gfx.Sprite.from_tileset(
    fname, 242, 234, 2, xsep=15, width=23, height=29, origin_x=8, origin_y=5,
    fps=30)
anneroy_legs_crouched_sprite = sge.gfx.Sprite.from_tileset(
    fname, 23, 85, width=21, height=15, origin_x=7, origin_y=-9)
anneroy_legs_crouch_sprite = sge.gfx.Sprite.from_tileset(
    fname, 9, 189, 2, xsep=7, width=21, height=21, origin_x=8, origin_y=-3,
    fps=10)

if GOD:
    asprites = [
        anneroy_turn_sprite,
        anneroy_teleport_sprite,
        anneroy_wall_right_sprite,
        anneroy_wall_left_sprite,
        anneroy_walljump_left_sprite,
        anneroy_walljump_right_sprite,
        anneroy_compress_sprite,
        anneroy_ball_sprite,
        anneroy_decompress_fail_sprite,
        anneroy_hedgehog_start_sprite,
        anneroy_hedgehog_extend_sprite,
        anneroy_hedgehog_sprite,
        anneroy_death_right_sprite,
        anneroy_death_left_sprite,
        anneroy_explode_sprite,
        anneroy_explode_fragments,
        anneroy_torso_right_idle_sprite,
        anneroy_torso_right_aim_right_sprite,
        anneroy_torso_right_aim_up_sprite,
        anneroy_torso_right_aim_down_sprite,
        anneroy_torso_right_aim_upright_sprite,
        anneroy_torso_right_aim_downright_sprite,
        anneroy_torso_left_idle_sprite,
        anneroy_torso_left_aim_left_sprite,
        anneroy_torso_left_aim_up_sprite,
        anneroy_torso_left_aim_down_sprite,
        anneroy_torso_left_aim_upleft_sprite,
        anneroy_torso_left_aim_downleft_sprite,
        anneroy_legs_stand_sprite,
        anneroy_legs_run_sprite,
        anneroy_legs_jump_sprite,
        anneroy_legs_fall_sprite,
        anneroy_legs_land_sprite,
        anneroy_legs_crouched_sprite,
        anneroy_legs_crouch_sprite,
    ]
    for s in asprites:
        s.swap_color(sge.gfx.Color((255, 89, 45)),
                     sge.gfx.Color((255, 189, 0)))
        s.swap_color(sge.gfx.Color((246, 19, 19)),
                     sge.gfx.Color((247, 107, 0)))
        s.swap_color(sge.gfx.Color((143, 14, 47)),
                     sge.gfx.Color((115, 33, 0)))

anneroy_bullet_dust_sprite = sge.gfx.Sprite.from_tileset(
    fname, 249, 119, width=26, height=16, origin_x=2, origin_y=7, fps=10)
anneroy_bullet_sprite = sge.gfx.Sprite.from_tileset(
    fname, 287, 123, width=17, height=6, origin_x=14, origin_y=3, bbox_x=-8,
    bbox_y=-8, bbox_width=16, bbox_height=16)
anneroy_bullet_dissipate_sprite = sge.gfx.Sprite.from_tileset(
    fname, 317, 102, 2, xsep=12, width=21, height=52, origin_x=12, origin_y=23,
    fps=10)

n = id(anneroy_compress_sprite)
anneroy_torso_offset[(n, 0)] = (0, 11)
anneroy_torso_offset[(n, 1)] = (0, 11)
anneroy_torso_offset[(n, 2)] = (0, 11)

n = id(anneroy_decompress_fail_sprite)
anneroy_torso_offset[(n, 0)] = (0, 11)
anneroy_torso_offset[(n, 1)] = (0, 11)
anneroy_torso_offset[(n, 2)] = (0, 11)

n = id(anneroy_legs_run_sprite)
anneroy_torso_offset[(n, 1)] = (0, 1)
anneroy_torso_offset[(n, 2)] = (0, 3)
anneroy_torso_offset[(n, 3)] = (0, 4)
anneroy_torso_offset[(n, 4)] = (0, 2)
anneroy_torso_offset[(n, 6)] = (0, 1)
anneroy_torso_offset[(n, 7)] = (0, 3)
anneroy_torso_offset[(n, 8)] = (0, 5)
anneroy_torso_offset[(n, 9)] = (0, 3)

n = id(anneroy_legs_jump_sprite)
anneroy_torso_offset[(n, 0)] = (0, 3)
anneroy_torso_offset[(n, 1)] = (0, -5)
anneroy_torso_offset[(n, 2)] = (0, -2)
anneroy_torso_offset[(n, 3)] = (0, -2)
anneroy_torso_offset[(n, 4)] = (0, -3)

n = id(anneroy_legs_fall_sprite)
anneroy_torso_offset[(n, 0)] = (0, -2)

n = id(anneroy_legs_land_sprite)
anneroy_torso_offset[(n, 0)] = (0, -5)
anneroy_torso_offset[(n, 1)] = (0, 3)

n = id(anneroy_legs_crouched_sprite)
anneroy_torso_offset[(n, 0)] = (0, 11)

n = id(anneroy_legs_crouch_sprite)
anneroy_torso_offset[(n, 0)] = (0, 3)
anneroy_torso_offset[(n, 1)] = (0, 9)

enemy_fragment_sprite = sge.gfx.Sprite(width=1, height=1)
enemy_fragment_sprite.draw_rectangle(0, 0, 1, 1, fill=sge.gfx.Color("white"))

d = os.path.join(hlib.datadir, "images", "objects", "enemies")
frog_stand_sprite = sge.gfx.Sprite("frog_stand", d)
frog_jump_sprite = sge.gfx.Sprite("frog_jump", d)
frog_fall_sprite = sge.gfx.Sprite("frog_fall", d)
bat_sprite = sge.gfx.Sprite("bat", d, fps=10, bbox_x=3, bbox_y=4,
                            bbox_width=10, bbox_height=10)
worm_sprite = sge.gfx.Sprite("worm", d, fps=10)
worm_base_sprite = sge.gfx.Sprite("worm_base", d, fps=10)

fname = os.path.join(d, "hedgehog_sheet.png")
hedgehog_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 0, width=20, height=20)
hedgehog_walk_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 20, 6, width=20, height=20)
hedgehog_compress_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 40, 2, width=20, height=20, fps=15)
hedgehog_ball_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 60, 8, width=20, height=20)
hedgehog_uncompress_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 80, 2, width=20, height=20, fps=15)

fname = os.path.join(d, "jellyfish_sheet.png")
jellyfish_idle_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 0, 7, width=32, height=32, origin_x=24, origin_y=24, fps=20)
jellyfish_swim_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 64, 6, width=32, height=32, origin_x=24, origin_y=24, fps=50)
jellyfish_swim_sprite = sge.gfx.Sprite.from_tileset(
    fname, 192, 64, 6, width=32, height=32, origin_x=24, origin_y=24, fps=50)

fname = os.path.join(d, "wolf_sheet.png")
wolf_right_sleep_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 0, 4, width=64, height=32, origin_x=32, fps=8)
wolf_right_asleep_sprite = sge.gfx.Sprite.from_tileset(
    fname, 512, 0, width=64, height=32, origin_x=32)
wolf_right_howl_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 54, 4, width=64, height=42, origin_x=32, origin_y=10, fps=16)
wolf_right_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 96, width=64, height=32, origin_x=32)
wolf_right_walk_sprite = sge.gfx.Sprite.from_tileset(
    fname, 384, 96, 4, width=64, height=32, origin_x=32, fps=8)
wolf_right_run_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 128, 5, width=64, height=32, origin_x=32, fps=10)
wolf_right_attack_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 160, 5, width=64, height=32, origin_x=32, fps=10)

wolf_left_sleep_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 192, 4, width=64, height=32, origin_x=32, fps=8)
wolf_left_asleep_sprite = sge.gfx.Sprite.from_tileset(
    fname, 512, 192, width=64, height=32, origin_x=32)
wolf_left_howl_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 246, 4, width=64, height=42, origin_x=32, origin_y=10, fps=16)
wolf_left_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 288, width=64, height=32, origin_x=32)
wolf_left_walk_sprite = sge.gfx.Sprite.from_tileset(
    fname, 384, 288, 4, width=64, height=32, origin_x=32, fps=8)
wolf_left_run_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 320, 5, width=64, height=32, origin_x=32, fps=10)
wolf_left_attack_sprite = sge.gfx.Sprite.from_tileset(
    fname, 320, 352, 5, width=64, height=32, origin_x=32, fps=10)

fname = os.path.join(d, "scorpion_sheet.png")
scorpion_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 0, width=60, height=36, origin_x=30, origin_y=9)
scorpion_walk_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 36, 6, width=60, height=36, origin_x=30, origin_y=9)
scorpion_shoot_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 108, 11, width=60, height=36, origin_x=30, origin_y=9, fps=20)
scorpion_shoot_end_sprite = sge.gfx.Sprite.from_tileset(
    fname, 0, 144, 5, width=60, height=36, origin_x=30, origin_y=9, fps=20)

scorpion_projectile_sprite = sge.gfx.Sprite(
    "scorpion_projectile", d, origin_y=2, bbox_x=2, bbox_y=1, bbox_width=17,
    bbox_height=4)
scorpion_projectile_shard_sprite = sge.gfx.Sprite(
    "scorpion_projectile_shard", d, fps=0)

fname = os.path.join(d, "mantanoid_sheet.png")
mantanoid_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 51, width=32, height=48, origin_x=15, origin_y=15)
mantanoid_idle_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 208, 12, xsep=5, width=33, height=50, origin_x=15, origin_y=17,
    fps=10)
mantanoid_turn_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 120, 3, xsep=5, width=32, height=47, origin_x=15, origin_y=14,
    fps=10)
mantanoid_walk_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 657, 10, xsep=3, width=41, height=49, origin_x=23, origin_y=16)
mantanoid_hop_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 299, 3, xsep=5, width=32, height=57, origin_x=15, origin_y=24,
    fps=10)
mantanoid_jump_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 372, 5, xsep=5, width=32, height=57, origin_x=15, origin_y=24,
    fps=10)
mantanoid_jump_sprite = sge.gfx.Sprite.from_tileset(
    fname, 156, 299, width=32, height=57, origin_x=15, origin_y=24)
mantanoid_fall_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 193, 299, 3, xsep=5, width=32, height=57, origin_x=15, origin_y=24,
    fps=10)
mantanoid_fall_sprite = sge.gfx.Sprite.from_tileset(
    fname, 304, 299, width=32, height=57, origin_x=15, origin_y=24)
mantanoid_land_sprite = sge.gfx.Sprite.from_tileset(
    fname, 341, 299, 3, xsep=5, width=32, height=57, origin_x=15, origin_y=24,
    fps=10)
mantanoid_slash_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 41, 470, 3, xsep=5, width=45, height=65, origin_x=15, origin_y=32,
    fps=10)
mantanoid_slash_single_sprite = sge.gfx.Sprite.from_tileset(
    fname, 191, 470, 4, xsep=5, width=45, height=65, origin_x=15, origin_y=32,
    fps=10)
mantanoid_slash_double_first_sprite = sge.gfx.Sprite.from_tileset(
    fname, 233, 551, 4, xsep=3, width=61, height=65, origin_x=15, origin_y=32,
    fps=10)
mantanoid_slash_double_second_sprite = sge.gfx.Sprite.from_tileset(
    fname, 489, 551, 3, xsep=3, width=61, height=65,
    origin_x=(15 + MANTANOID_DOUBLESLASH_OFFSET), origin_y=32, fps=10)

fname = os.path.join(d, "awesomepossum.png")
awesomepossum_stand_sprite = sge.gfx.Sprite.from_tileset(
    fname, 27, 123, 4, xsep=3, width=52, height=65, origin_x=20, origin_y=63,
    fps=10)
awesomepossum_walk_sprite = sge.gfx.Sprite.from_tileset(
    fname, 29, 205, 4, xsep=3, width=45, height=65, origin_x=22, origin_y=64)
awesomepossum_roll_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 88, 585, 3, xsep=3, width=56, height=65, origin_x=29, origin_y=59)
awesomepossum_roll_sprite = sge.gfx.Sprite.from_tileset(
    fname, 278, 600, 4, xsep=3, width=51, height=51, origin_x=26, origin_y=45)
awesomepossum_shoot_sprite = sge.gfx.Sprite.from_tileset(
    fname, 19, 749, 6, xsep=3, width=46, height=64, origin_x=20, origin_y=62,
    fps=10)
awesomepossum_bullet_start_sprite = sge.gfx.Sprite.from_tileset(
    fname, 379, 783, 4, xsep=3, width=20, height=15, origin_x=12, origin_y=8,
    fps=10)
awesomepossum_bullet_sprite = sge.gfx.Sprite.from_tileset(
    fname, 478, 783, 1, width=23, height=17, origin_x=14, origin_y=9)

d = os.path.join(hlib.datadir, "images", "objects", "doors")
door_barrier_x_sprite = sge.gfx.Sprite("barrier_x", d, origin_y=-8, fps=30,
                                       bbox_y=8, bbox_width=8, bbox_height=48)
door_barrier_y_sprite = sge.gfx.Sprite("barrier_y", d, origin_x=-8, fps=30,
                                       bbox_x=8, bbox_width=48, bbox_height=8)
doorframe_regular_x_closed_sprite = sge.gfx.Sprite("regular_x_closed", d)
doorframe_regular_x_open_sprite = sge.gfx.Sprite("regular_x_open", d)
doorframe_regular_y_closed_sprite = sge.gfx.Sprite("regular_y_closed", d)
doorframe_regular_y_open_sprite = sge.gfx.Sprite("regular_y_open", d)

d = os.path.join(hlib.datadir, "images", "objects", "stones")
stone_fragment_sprite = sge.gfx.Sprite("stone_fragment", d)

d = os.path.join(hlib.datadir, "images", "objects", "powerups")
life_orb_sprite = sge.gfx.Sprite("life_orb", d, fps=10)
powerup_map_sprite = sge.gfx.Sprite("map", d, fps=3)
atomic_compressor_sprite = sge.gfx.Sprite(
    "atomic_compressor", d, origin_y=1, fps=10, bbox_width=16, bbox_height=16)
monkey_boots_sprite = sge.gfx.Sprite(
    "monkey_boots", d, bbox_y=9, bbox_width=16, bbox_height=7)
monkey_boots_gleam_sprite = sge.gfx.Sprite(
    "monkey_boots_gleam", d, origin_x=10, origin_y=5, fps=15)
hedgehog_hormone_sprite = sge.gfx.Sprite("hedgehog_hormone", d)
hedgehog_hormone_bubble_sprite = sge.gfx.Sprite("hedgehog_hormone_bubble", d,
                                                fps=5)

d = os.path.join(hlib.datadir, "images", "objects", "misc")
warp_pad_active_sprite = sge.gfx.Sprite("warp_pad_active", d)
warp_pad_inactive_sprite = sge.gfx.Sprite("warp_pad_inactive", d)

d = os.path.join(hlib.datadir, "images", "map")
map_wall_left_sprite = sge.gfx.Sprite("wall_left", d)
map_wall_right_sprite = sge.gfx.Sprite("wall_right", d)
map_wall_top_sprite = sge.gfx.Sprite("wall_top", d)
map_wall_bottom_sprite = sge.gfx.Sprite("wall_bottom", d)
map_door_left_sprite = sge.gfx.Sprite("door_left", d)
map_door_right_sprite = sge.gfx.Sprite("door_right", d)
map_door_top_sprite = sge.gfx.Sprite("door_top", d)
map_door_bottom_sprite = sge.gfx.Sprite("door_bottom", d)
map_powerup_sprite = sge.gfx.Sprite("powerup", d)
map_warp_pad_sprite = sge.gfx.Sprite("warp_pad", d)
map_player_sprite = sge.gfx.Sprite("player", d)

d = os.path.join(hlib.datadir, "images", "misc")
logo_sprite = sge.gfx.Sprite("logo", d, origin_x=125)
font_sprite = sge.gfx.Sprite.from_tileset(
    os.path.join(d, "font.png"), columns=18, rows=19, width=7, height=9)
font_small_sprite = sge.gfx.Sprite.from_tileset(
    os.path.join(d, "font_small.png"), columns=8, rows=12, width=7, height=7)
font_big_sprite = sge.gfx.Sprite.from_tileset(
    os.path.join(d, "font_big.png"), columns=8, rows=12, width=14, height=14,
    xsep=2, ysep=2)
healthbar_back_sprite = sge.gfx.Sprite("healthbar_back", d, origin_x=2,
                                       origin_y=1)
healthbar_front_sprite = sge.gfx.Sprite("healthbar_front", d,
                                        transparent=False)
healthbar_width = healthbar_front_sprite.width
healthbar_height = healthbar_front_sprite.height
etank_empty_sprite = sge.gfx.Sprite("etank_empty", d)
etank_empty_sprite.draw_rectangle(
    0, 0, etank_empty_sprite.width, etank_empty_sprite.height,
    fill=sge.gfx.Color((0, 0, 0, 128)), blend_mode=sge.BLEND_RGBA_SUBTRACT)
etank_full_sprite = sge.gfx.Sprite("etank_full", d)
life_force_sprite = sge.gfx.Sprite(
    "life_force", d, origin_x=7, origin_y=7, fps=10)

# Load backgrounds
d = os.path.join(hlib.datadir, "images", "backgrounds")
layers = []

if not NO_BACKGROUNDS:
    layers = [
        sge.gfx.BackgroundLayer(
            sge.gfx.Sprite("kawamora", d), 0, 0, -100000, xscroll_rate=0.1,
            yscroll_rate=0.1, repeat_left=True, repeat_right=True,
            repeat_up=True, repeat_down=True)]

backgrounds["kawamora"] = sge.gfx.Background(layers, sge.gfx.Color((0, 0, 0)))

if not NO_BACKGROUNDS:
    layers = [
        sge.gfx.BackgroundLayer(
            sge.gfx.Sprite("iridia", d), 0, 0, -100000, xscroll_rate=0.7,
            yscroll_rate=0.7, repeat_left=True, repeat_right=True,
            repeat_up=True, repeat_down=True)]

backgrounds["iridia"] = sge.gfx.Background(layers, sge.gfx.Color((21, 17, 22)))

# Load fonts
chars = ([chr(i) for i in range(32, 127)] + [None, ETANK_CHAR] + [' ']*11
         + [chr(i) for i in range(161, 384)])
font = sge.gfx.Font.from_sprite(font_sprite, chars, size=9, hsep=-1)
chars = [chr(i) for i in range(32, 127)] + [None]
font_big = sge.gfx.Font.from_sprite(font_big_sprite, chars, size=14,
                                    hsep=2, vsep=2)

chars = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
             "0123456789.,;:?!-_~#\"'&()[]|`\\/@^+=*$\xa3\u20ac<>  ") + [None]
font_small = sge.gfx.Font.from_sprite(font_small_sprite, chars, size=7,
                                      hsep=-1)

# Load sounds
shoot_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "shoot.wav"),
                            volume=0.5)
bullet_death_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "bullet_death.ogg"), volume=0.2)
land_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "land.ogg"), volume=0.5)
ball_land_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "ball_land.ogg"))
hedgehog_spikes_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "hedgehog_spikes.wav"), volume=0.5)
hurt_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "hurt.wav"))
death_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "death.wav"))
stone_break_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "stone_break.ogg"), volume=0.5)
powerup_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "powerup.wav"))
heal_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "heal.wav"))
warp_pad_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "warp_pad.ogg"))
teleport_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "teleport.wav"))
door_open_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "door_open.ogg"), volume=0.5)
door_close_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "door_close.ogg"), volume=0.5)
enemy_hurt_sound = stone_break_sound
enemy_death_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "enemy_death.wav"))
frog_jump_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "frog_jump.wav"))
scorpion_shoot_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "scorpion_shoot.wav"))
scorpion_projectile_break_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "scorpion_projectile_break.ogg"), volume=0.5)
mantanoid_approach_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "mantanoid_approach.wav"))
mantanoid_slash_sound = sge.snd.Sound(
    os.path.join(hlib.datadir, "sounds", "mantanoid_slash.wav"))
select_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "select.ogg"))
pause_sound = select_sound
confirm_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "confirm.wav"))
cancel_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "cancel.wav"))
error_sound = cancel_sound
type_sound = sge.snd.Sound(os.path.join(hlib.datadir, "sounds", "type.wav"))

# Create objects
##lava_animation = sge.dsp.Object(0, 0, sprite=lava_body_sprite, visible=False,
##                                tangible=False)

# Create rooms
sge.game.start_room = TitleScreen.load(
    os.path.join("special", "title_screen.json"), True)

sge.game.mouse.visible = False

# Load map data
map_rooms = {}
map_objects = {}
if not GEN_MAP:
    try:
        with open(os.path.join(hlib.datadir, "map", "rooms.json")) as f:
            d = json.load(f)
    except (OSError, ValueError):
        generate_map()
    else:
        for i in d:
            map_rooms[i] = tuple(d[i])

    try:
        with open(os.path.join(hlib.datadir, "map", "objects.json")) as f:
            d = json.load(f)
    except (OSError, ValueError):
        generate_map()
    else:
        for i in d:
            x, y = tuple(i.split(','))
            j = (int(x), int(y))
            map_objects[j] = d[i]

    try:
        with open(os.path.join(hlib.datadir, "map", "info.json")) as f:
            d = json.load(f)
    except (OSError, ValueError):
        generate_map()
    else:
        num_powerups = d.get("powerups", 0)
        num_artifacts = d.get("artifacts", 0)
else:
    generate_map()

if SAVE_MAP:
    map_revealed = list(map_objects.keys())
    map_explored = map_revealed
    draw_map().save("map.png")
    map_revealed = []
    map_explored = []

try:
    with open(os.path.join(hlib.configdir, "config.json")) as f:
        cfg = json.load(f)
except (OSError, ValueError):
    cfg = {}
finally:
    cfg_version = cfg.get("version", 0)

    fullscreen = cfg.get("fullscreen", fullscreen)
    update_fullscreen()
    scale_method = cfg.get("scale_method", scale_method)
    sge.game.scale_method = scale_method
    sound_enabled = cfg.get("sound_enabled", sound_enabled)
    music_enabled = cfg.get("music_enabled", music_enabled)
    stereo_enabled = cfg.get("stereo_enabled", stereo_enabled)
    fps_enabled = cfg.get("fps_enabled", fps_enabled)
    metroid_controls = cfg.get("metroid_controls", metroid_controls)
    joystick_threshold = cfg.get("joystick_threshold", joystick_threshold)
    xsge_gui.joystick_threshold = joystick_threshold

    keys_cfg = cfg.get("keys", {})
    left_key = keys_cfg.get("left", left_key)
    right_key = keys_cfg.get("right", right_key)
    up_key = keys_cfg.get("up", up_key)
    aim_diag_key = keys_cfg.get("aim_diag", aim_diag_key)
    down_key = keys_cfg.get("down", down_key)
    jump_key = keys_cfg.get("jump", jump_key)
    shoot_key = keys_cfg.get("shoot", shoot_key)
    aim_up_key = keys_cfg.get("aim_up", aim_up_key)
    aim_down_key = keys_cfg.get("aim_down", aim_down_key)
    mode_reset_key = keys_cfg.get("mode_reset", mode_reset_key)
    mode_key = keys_cfg.get("mode", mode_key)
    pause_key = keys_cfg.get("pause", pause_key)
    map_key = keys_cfg.get("map", map_key)

    js_cfg = cfg.get("joystick", {})
    left_js = [[tuple(j) for j in js] for js in js_cfg.get("left", left_js)]
    right_js = [[tuple(j) for j in js] for js in js_cfg.get("right", right_js)]
    up_js = [[tuple(j) for j in js] for js in js_cfg.get("up", up_js)]
    down_js = [[tuple(j) for j in js] for js in js_cfg.get("down", down_js)]
    aim_diag_js = [[tuple(j) for j in js]
                   for js in js_cfg.get("aim_diag", aim_diag_js)]
    jump_js = [[tuple(j) for j in js] for js in js_cfg.get("jump", jump_js)]
    shoot_js = [[tuple(j) for j in js] for js in js_cfg.get("shoot", shoot_js)]
    aim_up_js = [[tuple(j) for j in js]
                 for js in js_cfg.get("aim_up", aim_up_js)]
    aim_down_js = [[tuple(j) for j in js]
                   for js in js_cfg.get("aim_down", aim_down_js)]
    mode_reset_js = [[tuple(j) for j in js]
                     for js in js_cfg.get("mode_reset", mode_reset_js)]
    mode_js = [[tuple(j) for j in js] for js in js_cfg.get("mode", mode_js)]
    pause_js = [[tuple(j) for j in js] for js in js_cfg.get("pause", pause_js)]
    map_js = [[tuple(j) for j in js] for js in js_cfg.get("map", map_js)]

    set_gui_controls()

try:
    with open(os.path.join(hlib.localdir, "ai_data.json")) as f:
        d = json.load(f)
except (OSError, ValueError):
    pass
else:
    ai_data.update(d)

try:
    with open(os.path.join(hlib.localdir, "save_slots.json")) as f:
        loaded_slots = json.load(f)
except (OSError, ValueError):
    pass
else:
    for i in range(min(len(loaded_slots), len(save_slots))):
        slot = loaded_slots[i]
        if slot is not None and slot.get("save_format", 0) > 0:
            save_slots[i] = slot
        else:
            save_slots[i] = None


print(_("Starting game..."))

try:
    if not QUIT:
        sge.game.start()
    else:
        print(_("Successfully started Hexoshi. Quitting now as -q was passed."))
finally:
    write_to_disk()
