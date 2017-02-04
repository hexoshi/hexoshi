#!/usr/bin/env python2

# Hexoshi
# Copyright (C) 2014-2017 Julie Marchant <onpon4@riseup.net>
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

__version__ = "0.1a0"

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
import six
import xsge_gui
import xsge_lighting
import xsge_path
import xsge_physics
import xsge_tmx


if getattr(sys, "frozen", False):
    __file__ = sys.executable

DATA = os.path.join(os.path.dirname(__file__), "data")
CONFIG = os.path.join(os.path.expanduser("~"), ".config", "hexoshi")
SCREEN_SIZE = [400, 224]
TILE_SIZE = 16
FPS = 60
DELTA_MIN = FPS / 2
DELTA_MAX = FPS * 4
SCALE = 2
FSSCALE = None

if six.PY2:
    gettext.install("hexoshi", os.path.abspath(os.path.join(DATA, "locale")),
                    unicode=True)
else:
    gettext.install("hexoshi", os.path.abspath(os.path.join(DATA, "locale")))

parser = argparse.ArgumentParser()
parser.add_argument(
    "-p", "--print-errors",
    help=_("Print errors directly to stdout rather than saving them in a file."),
    action="store_true")
parser.add_argument(
    "-l", "--lang",
    help=_("Manually choose a different language to use."))
parser.add_argument(
    "--nodelta",
    help=_("Disable delta timing. Causes the game to slow down when it can't run at full speed instead of becoming choppier."),
    action="store_true")
parser.add_argument(
    "-d", "--datadir",
    help=_('Where to load the game data from (Default: "{}")').format(DATA))
parser.add_argument(
    "--scale",
    help=_('The scale factor to use by default in windowed mode (Default: "{}")').format(SCALE))
parser.add_argument(
    "--fsscale",
    help=_("Specify a scale factor to use in fullscreen mode instead of using dynamic scaling. This will cause the screen resolution to change, which may improve performance. For best results, specify this as the target resolution width divided by {w}, or as the target resolution height divided by {h} (whichever is smaller). For example, to target a resolution of 640x480, use {ex}. A scale factor of 1 will always be fastest, but may result in windowboxing.").format(
        w=SCREEN_SIZE[0], h=SCREEN_SIZE[1],
        ex=min(640 / SCREEN_SIZE[0], 480 / SCREEN_SIZE[1])))
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
parser.add_argument("--god")
args = parser.parse_args()

PRINT_ERRORS = args.print_errors
DELTA = not args.nodelta
if args.datadir:
    DATA = args.datadir
if args.scale:
    SCALE = eval(args.scale)
if args.fsscale:
    FSSCALE = eval(args.fsscale)
NO_BACKGROUNDS = args.no_backgrounds
NO_HUD = args.no_hud
GEN_MAP = args.gen_map
SAVE_MAP = args.save_map
GOD = (args.god and args.god.lower() == "inbailey")

if args.lang:
    lang = gettext.translation("hexoshi",
                               os.path.abspath(os.path.join(DATA, "locale")),
                               [args.lang])
    if six.PY2:
        lang.install(unicode=True)
    else:
        lang.install()

GRAVITY = 0.4

PLAYER_MAX_HP = 100
PLAYER_MAX_SPEED = 3
PLAYER_ACCELERATION = 0.5
PLAYER_AIR_ACCELERATION = 0.1
PLAYER_FRICTION = 0.75
PLAYER_AIR_FRICTION = 0.01
PLAYER_JUMP_HEIGHT = 5 * TILE_SIZE + 2
PLAYER_FALL_SPEED = 7
PLAYER_SLIDE_SPEED = 0.25
PLAYER_RUN_FRAMES_PER_PIXEL = 1 / 10
PLAYER_HITSTUN = FPS
WARP_TIME = FPS / 2
DEATH_TIME = 3 * FPS

ANNEROY_BBOX_X = -7
ANNEROY_BBOX_WIDTH = 14
ANNEROY_STAND_BBOX_Y = -16
ANNEROY_STAND_BBOX_HEIGHT = 40
ANNEROY_CROUCH_BBOX_Y = -5
ANNEROY_CROUCH_BBOX_HEIGHT = 29
ANNEROY_BULLET_SPEED = 8
ANNEROY_BULLET_DSPEED = ANNEROY_BULLET_SPEED * math.sin(math.radians(45))
ANNEROY_BULLET_LIFE = 45
ANNEROY_EXPLODE_TIME = 0.6 * FPS

CEILING_LAX = 2

CAMERA_HSPEED_FACTOR = 1 / 8
CAMERA_VSPEED_FACTOR = 1 / 20
CAMERA_OFFSET_FACTOR = 10
CAMERA_MARGIN_TOP = 3 * TILE_SIZE
CAMERA_MARGIN_BOTTOM = 3 * TILE_SIZE
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

ETANK_CHAR = '\x80'

backgrounds = {}
loaded_music = {}
tux_grab_sprites = {}

fullscreen = False
scale_method = None
sound_enabled = True
music_enabled = True
stereo_enabled = True
fps_enabled = False
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
save_slots = [None for i in six.moves.range(SAVE_NSLOTS)]

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
etanks = 0

spawn_xoffset = 0
spawn_yoffset = 0

player = None


class Game(sge.dsp.Game):

    fps_time = 0
    fps_frames = 0
    fps_text = ""
    cheatcode = ""

    def event_step(self, time_passed, delta_mult):
        if fps_enabled:
            self.fps_time += time_passed
            self.fps_frames += 1
            if self.fps_time >= 250:
                self.fps_text = str(round(
                    (1000 * self.fps_frames) / self.fps_time, 2))
                self.fps_time = 0
                self.fps_frames = 0

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
                    warp(self.cheatcode[4:])
                else:
                    print(_("Invalid cheat code: {}").format(self.cheatcode))

    def event_mouse_button_press(self, button):
        if button == "middle":
            self.event_close()

    def event_close(self):
        self.end()

    def event_paused_close(self):
        self.event_close()


class Level(sge.dsp.Room):

    """Handles levels."""

    def __init__(self, objects=(), width=None, height=None, views=None,
                 background=None, background_x=0, background_y=0,
                 object_area_width=TILE_SIZE * 2,
                 object_area_height=TILE_SIZE * 2,
                 name=None, bgname=None, music=None, timeline=None,
                 ambient_light=None, disable_lights=False):
        self.fname = None
        self.name = name
        self.music = music
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

        super(Level, self).__init__(objects, width, height, views, background,
                                    background_x, background_y,
                                    object_area_width, object_area_height)
        self.add(gui_handler)

    def load_timeline(self, timeline):
        self.timeline = {}
        self.timeline_name = ""
        self.timeline_step = 0
        self.timeline_skip_target = None
        if timeline:
            self.timeline_name = timeline
            fname = os.path.join(DATA, "timelines", timeline)
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
                                           buffer=TILE_SIZE * 2)
        else:
            xsge_lighting.clear_lights()

        if not NO_HUD:
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
                                                       "credits.tmx"))
        credits_room.start()

    def event_room_start(self):
        if player is not None:
            self.add(player)
        ##self.add(lava_animation)

        xsge_lighting.clear_lights()

        play_music(self.music)

    def event_room_resume(self):
        play_music(self.music)

    def event_step(self, time_passed, delta_mult):
        global watched_timelines

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
                                    m = _("An error occurred in a timeline 'setattr' command:\n\n{}").format(
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
                            args = arg.split(None, 1)
                            if len(args) >= 2:
                                portrait, text = args[:2]
                                sprite = portrait_sprites.get(portrait)
                                DialogBox(gui_handler, _(text), sprite).show()
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
                                six.exec_(arg)
                            except Exception as e:
                                m = _("An error occurred in a timeline 'exec' command:\n\n{}").format(
                                    traceback.format_exc())
                                show_error(m)
                        elif command == "if":
                            try:
                                r = eval(arg)
                            except Exception as e:
                                m = _("An error occurred in a timeline 'if' statement:\n\n{}").format(
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
                                m = _("An error occurred in a timeline 'while' statement:\n\n{}").format(
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
                    view.width + LIGHT_RANGE * 2,
                    view.height + LIGHT_RANGE * 2):
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
                sge.game.project_rectangle(x - w / 2, y - h / 2, w, h,
                                           fill=sge.gfx.Color("black"))
                sge.game.project_text(font, text, x, y,
                                      color=sge.gfx.Color("white"),
                                      halign="center", valign="middle")
                sge.game.refresh()
            else:
                print(_("Loading \"{}\"...").format(fname))

        try:
            r = xsge_tmx.load(os.path.join(DATA, "rooms", fname), cls=cls,
                              types=TYPES)
        except Exception as e:
            m = _("An error occurred when trying to load the level:\n\n{}").format(
                traceback.format_exc())
            show_error(m)
            r = None
        else:
            r.fname = fname

        return r


class SpecialScreen(Level):

    def event_room_start(self):
        super(SpecialScreen, self).event_room_start()
        if player is not None:
            player.destroy()


class TitleScreen(SpecialScreen):

    def show_hud(self):
        pass

    def event_room_start(self):
        super(TitleScreen, self).event_room_start()
        MainMenu.create()

    def event_room_resume(self):
        super(TitleScreen, self).event_room_resume()
        MainMenu.create()

    def event_key_press(self, key, char):
        pass


class CreditsScreen(SpecialScreen):

    def event_room_start(self):
        super(CreditsScreen, self).event_room_start()

        with open(os.path.join(DATA, "credits.json"), 'r') as f:
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
                y = self.sections[-1].bbox_bottom + font_big.size * 3
                head_section = sge.dsp.Object.create(x, y, sprite=head_sprite,
                                                     tangible=False)
                self.sections.append(head_section)

            if "lines" in section:
                for line in section["lines"]:
                    list_sprite = sge.gfx.Sprite.from_text(
                        font, line, width=self.width - 2 * TILE_SIZE,
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
            self.alarms["end"] = 3.5 * FPS

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
        elif (key in itertools.chain.from_iterable(jump_key) or
                key in itertools.chain.from_iterable(shoot_key) or
                key in itertools.chain.from_iterable(pause_key)):
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
            elif (js in itertools.chain.from_iterable(jump_js) or
                    js in itertools.chain.from_iterable(shoot_js) or
                    js in itertools.chain.from_iterable(pause_js)):
                sge.game.start_room.start()


class SolidLeft(xsge_physics.SolidLeft):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SolidLeft, self).__init__(*args, **kwargs)


class SolidRight(xsge_physics.SolidRight):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SolidRight, self).__init__(*args, **kwargs)


class SolidTop(xsge_physics.SolidTop):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SolidTop, self).__init__(*args, **kwargs)


class SolidBottom(xsge_physics.SolidBottom):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SolidBottom, self).__init__(*args, **kwargs)


class Solid(xsge_physics.Solid):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(Solid, self).__init__(*args, **kwargs)


class SlopeTopLeft(xsge_physics.SlopeTopLeft):

    xsticky_top = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SlopeTopLeft, self).__init__(*args, **kwargs)


class SlopeTopRight(xsge_physics.SlopeTopRight):

    xsticky_top = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SlopeTopRight, self).__init__(*args, **kwargs)


class SlopeBottomLeft(xsge_physics.SlopeBottomLeft):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SlopeBottomLeft, self).__init__(*args, **kwargs)


class SlopeBottomRight(xsge_physics.SlopeBottomRight):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SlopeBottomRight, self).__init__(*args, **kwargs)


class MovingPlatform(xsge_physics.SolidTop, xsge_physics.MobileWall):

    sticky_top = True

    def __init__(self, x, y, z=0, **kwargs):
        kwargs.setdefault("sprite", platform_sprite)
        super(MovingPlatform, self).__init__(x, y, z, **kwargs)
        self.path = None
        self.following = False

    def event_step(self, time_passed, delta_mult):
        super(MovingPlatform, self).event_step(time_passed, delta_mult)

        if self.path and not self.following:
            for other in self.collision(Player, y=(self.y - 1)):
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
        super(Death, self).__init__(*args, **kwargs)


class Player(xsge_physics.Collider):

    name = "Ian C."
    max_hp = PLAYER_MAX_HP
    max_speed = PLAYER_MAX_SPEED
    acceleration = PLAYER_ACCELERATION
    air_acceleration = PLAYER_AIR_ACCELERATION
    friction = PLAYER_FRICTION
    air_friction = PLAYER_AIR_FRICTION
    jump_height = PLAYER_JUMP_HEIGHT
    gravity = GRAVITY
    fall_speed = PLAYER_FALL_SPEED
    slide_speed = PLAYER_SLIDE_SPEED
    hitstun_time = PLAYER_HITSTUN
    can_move = True

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
        guides = self.collision(CameraXGuide)
        if guides:
            return guides[0].x
        else:
            return (self.x - self.view.width / 2 +
                    self.xvelocity * CAMERA_OFFSET_FACTOR)

    @property
    def camera_target_y(self):
        guides = self.collision(CameraYGuide)
        if guides:
            self.camera_guided_y = True
            return guides[0].y
        else:
            self.camera_guided_y = False
            return self.y - self.view.height + CAMERA_TARGET_MARGIN_BOTTOM

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

        self.hud_sprite = sge.gfx.Sprite(width=SCREEN_SIZE[0],
                                         height=SCREEN_SIZE[1])

        self.reset_input()
        self.etanks_used = 0
        self.hitstun = False
        self.facing = 1
        self.aim_direction = None
        self.aim_direction_time = 0
        self.view = None
        self.__hp = self.max_hp
        healthbar_front_sprite.width = healthbar_width
        self.last_xr = None
        self.last_yr = None
        self.camera_guided_y = False

        if GOD:
            image_blend = sge.gfx.Color("olive")

        super(Player, self).__init__(
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

    def refresh_input(self):
        if self.human and not self.input_lock:
            key_controls = [left_key, right_key, up_key, down_key, aim_diag_key,
                            jump_key, shoot_key, aim_up_key, aim_down_key]
            js_controls = [left_js, right_js, up_js, down_js, aim_diag_js,
                           jump_js, shoot_js, aim_up_js, aim_down_js]
            states = [0 for i in key_controls]

            for i in six.moves.range(len(key_controls)):
                for choice in key_controls[i][self.player]:
                    value = sge.keyboard.get_pressed(choice)
                    states[i] = max(states[i], value)

            for i in six.moves.range(len(js_controls)):
                for choice in js_controls[i][self.player]:
                    j, t, c = choice
                    value = min(sge.joystick.get_value(j, t, c), 1)
                    if value >= joystick_threshold:
                        states[i] = max(states[i], value)

            self.left_pressed = states[0]
            self.right_pressed = states[1]
            self.up_pressed = states[2]
            self.down_pressed = states[3]
            self.aim_diag_pressed = states[4]
            self.jump_pressed = states[5]
            self.shoot_pressed = states[6]
            self.aim_up_pressed = states[7]
            self.aim_down_pressed = states[8]

    def press_up(self):
        if not self.aim_diag_pressed:
            warp_pads = self.collision(WarpPad)
            if warp_pads:
                warp_pad = warp_pads[0]
                warp_pad.teleport(self)

    def press_down(self):
        pass

    def jump(self):
        if self.on_floor or self.was_on_floor:
            self.yvelocity = get_jump_speed(self.jump_height, self.gravity)
            self.on_floor = []
            self.was_on_floor = []
            self.event_jump()

    def jump_release(self):
        if self.yvelocity < 0:
            self.yvelocity /= 2

    def shoot(self):
        pass

    def hurt(self, damage=1):
        if not self.hitstun:
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
        if not NO_HUD:
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
            for i in six.moves.range(etanks):
                if i < etanks - self.etanks_used:
                    self.hud_sprite.draw_sprite(etank_full_sprite, 0, x, y)
                else:
                    self.hud_sprite.draw_sprite(etank_empty_sprite, 0, x, y)

                x += w
                if x + w >= start_x + healthbar_width:
                    x = start_x
                    y += h

            if "map" in progress_flags:
                w = 7
                h = 5
                rm_x, rm_y = map_rooms.get(sge.game.current_room.fname, (0, 0))
                pl_x = rm_x + get_xregion(self.x)
                pl_y = rm_y + get_yregion(self.y)
                x = pl_x - w // 2
                y = pl_y - h // 2
                map_s = draw_map(x, y, w, h, pl_x, pl_y)
                c = sge.gfx.Color((255, 255, 255, 192))
                map_s.draw_rectangle(0, 0, map_s.width, map_s.height, fill=c,
                                     blend_mode=sge.BLEND_RGBA_MULTIPLY)

                x = SCREEN_SIZE[0] - start_x - w * MAP_CELL_WIDTH
                y = start_y
                self.hud_sprite.draw_sprite(map_s, 0, x, y)
                self.hud_sprite.draw_rectangle(x, y, map_s.width, map_s.height,
                                               outline=sge.gfx.Color("white"))
                

    def show_hud(self):
        if not NO_HUD:
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

        prev_aim_direction = self.aim_direction

        if "shooting" in self.alarms:
            self.aim_direction = 0
        else:
            self.aim_direction = None

        if v_control:
            if self.aim_diag_pressed:
                self.aim_direction = 1 * -v_control
            else:
                self.aim_direction = 2 * -v_control

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

        if abs(self.xvelocity) >= self.max_speed:
            self.xvelocity = self.max_speed * current_h_movement

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
                    self.xacceleration = self.acceleration * h_control
                else:
                    self.xacceleration = self.air_acceleration * h_control
            else:
                if self.on_floor or self.was_on_floor:
                    dc = self.friction
                else:
                    dc = self.air_friction

                if abs(self.xvelocity) - dc * delta_mult > target_speed:
                    self.xdeceleration = dc
                else:
                    self.xvelocity = target_speed * current_h_movement

        if current_h_movement and h_control != current_h_movement:
            if self.on_floor or self.was_on_floor:
                self.xdeceleration = self.friction
            else:
                self.xdeceleration = self.air_friction

        if not self.on_floor and not self.was_on_floor:
            if self.yvelocity < self.fall_speed:
                self.yacceleration = self.gravity
            else:
                self.yvelocity = self.fall_speed
        elif self.on_slope:
            if self.xvelocity:
                self.yvelocity = (self.slide_speed *
                                  (self.on_slope[0].bbox_height /
                                   self.on_slope[0].bbox_width))
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
                self.view.x += ((view_target_x - self.view.x) *
                                CAMERA_HSPEED_FACTOR)
            else:
                self.view.x = view_target_x

            view_min_y = self.y - self.view.height + CAMERA_MARGIN_BOTTOM
            view_max_y = self.y - CAMERA_MARGIN_TOP

            view_target_y = self.camera_target_y
            if (self.on_floor and self.was_on_floor) or self.camera_guided_y:
                if abs(view_target_y - self.view.y) > 0.5:
                    self.view.y += ((view_target_y - self.view.y) *
                                    CAMERA_VSPEED_FACTOR)
                else:
                    self.view.y = view_target_y

            if not self.camera_guided_y:
                if self.view.y < view_min_y:
                    self.view.y = view_min_y
                elif self.view.y > view_max_y:
                    self.view.y = view_max_y

        self.last_x = self.x
        self.last_y = self.y

        xr, yr = map_rooms.get(sge.game.current_room.fname, (0, 0))
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
            if key in up_key[self.player]:
                self.press_up()
            if key in down_key[self.player]:
                self.press_down()
            if key in jump_key[self.player]:
                self.jump()
            if key in shoot_key[self.player]:
                self.shoot()
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

    def event_joystick(self, js_name, js_id, input_type, input_id, value):
        if self.human and not self.input_lock:
            js = (js_id, input_type, input_id)
            if value >= joystick_threshold:
                if js in up_js[self.player]:
                    self.press_up()
                if js in down_js[self.player]:
                    self.press_down()
                if js in jump_js[self.player]:
                    self.jump()
                if js in shoot_js[self.player]:
                    self.shoot()
                if js in pause_js[self.player]:
                    sge.game.current_room.pause(player_x=self.last_xr,
                                                player_y=self.last_yr)
                if js in map_js[self.player]:
                    if "map" in progress_flags:
                        play_sound(select_sound)
                        MapDialog(self.last_xr, self.last_yr).show()
            else:
                if js in jump_js[self.player]:
                    self.jump_release()

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
        for i in six.moves.range(CEILING_LAX):
            if (not self.get_left_touching_wall() and
                    not self.get_left_touching_slope()):
                self.x -= 1
                tmv -= 1
                if (not self.get_top_touching_wall() and
                        not self.get_top_touching_slope()):
                    self.move_y(-move_loss)
                    break
        else:
            self.x -= tmv
            tmv = 0
            for i in six.moves.range(CEILING_LAX):
                if (not self.get_left_touching_wall() and
                        not self.get_left_touching_slope()):
                    self.x += 1
                    tmv += 1
                    if (not self.get_top_touching_wall() and
                            not self.get_top_touching_slope()):
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
        for block in self.get_bottom_touching_wall():
            if isinstance(block, HurtTop):
                self.hurt()

        if isinstance(other, xsge_physics.SolidTop):
            self.yvelocity = min(self.yvelocity, 0)
        elif isinstance(other, (xsge_physics.SlopeTopLeft,
                                xsge_physics.SlopeTopRight)):
            self.yvelocity = min(self.slide_speed * (other.bbox_height /
                                                     other.bbox_width),
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
        super(Anneroy, self).__init__(*args, **kwargs)

        self.torso = None
        self.fixed_sprite = False
        self.crouching = False
        self.last_aim_direction = 0

    def press_up(self):
        if self.crouching:
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
        else:
            super(Anneroy, self).press_up()

    def press_down(self):
        h_control = bool(self.right_pressed) - bool(self.left_pressed)
        if (not self.crouching and not h_control and self.on_floor and
                self.was_on_floor and not self.aim_diag_pressed):
            if self.fixed_sprite != "crouch":
                self.reset_image()
                self.sprite = anneroy_legs_crouch_sprite
                self.image_index = 0
            self.image_speed = anneroy_legs_crouch_sprite.speed
            self.fixed_sprite = "crouch"
            self.crouching = True
            self.bbox_y = ANNEROY_CROUCH_BBOX_Y
            self.bbox_height = ANNEROY_CROUCH_BBOX_HEIGHT

    def jump(self):
        if self.crouching:
            self.press_up()

        if not self.crouching:
            super(Anneroy, self).jump()

    def shoot(self):
        if "shoot_lock" not in self.alarms:
            if self.aim_direction is None:
                self.aim_direction = 0
            self.alarms["shooting"] = 30
            self.alarms["shoot_lock"] = 15

            if self.aim_direction is not None:
                self.last_aim_direction = self.aim_direction
            else:
                self.last_aim_direction = 0

            x = 0
            y = 0
            xv = 0
            yv = 0
            image_rotation = 0

            if self.facing > 0:
                if self.aim_direction == 0:
                    x = 25
                    y = -3
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
                    x = 19
                    y = 9
                    xv = ANNEROY_BULLET_DSPEED
                    yv = ANNEROY_BULLET_DSPEED
                    image_rotation = 45
                elif self.aim_direction == -2:
                    x = 9
                    y = 21
                    yv = ANNEROY_BULLET_SPEED
                    image_rotation = 90
            else:
                if self.aim_direction == 0:
                    x = -25
                    y = -3
                    xv = -ANNEROY_BULLET_SPEED
                    image_rotation = 180
                elif self.aim_direction == 1:
                    x = -22
                    y = -27
                    xv = -ANNEROY_BULLET_DSPEED
                    yv = -ANNEROY_BULLET_DSPEED
                    image_rotation = 225
                elif self.aim_direction == 2:
                    x = -6
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
                    x = -9
                    y = 21
                    yv = ANNEROY_BULLET_SPEED
                    image_rotation = 90

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
            for i in six.moves.range(xsteps):
                guide.move_x(math.copysign(guide.bbox_width, x))
            for i in six.moves.range(ysteps):
                guide.move_y(math.copysign(guide.bbox_height, y))
            guide.move_x(xfinal)
            guide.move_y(yfinal)

            if abs(self.aim_direction) == 1 and m:
                target_x = self.torso.x + x
                target_y = self.torso.y + y
                xdiff = guide.x - self.torso.x
                ydiff = guide.y - self.torso.y
                if abs(guide.x - target_x) >= 1:
                    guide.y = self.torso.y + m * xdiff
                elif abs(guide.y - target_y) >= 1:
                    guide.x = self.torso.x + ydiff / m

            bs = AnneroyBullet.create(
                guide.x, guide.y, self.z + 0.2,
                sprite=anneroy_bullet_sprite, xvelocity=xv,
                yvelocity=yv, regulate_origin=True,
                image_xscale=abs(self.image_xscale),
                image_yscale=self.image_yscale,
                image_rotation=image_rotation, image_blend=self.image_blend)

            guide.destroy()

            Smoke.create(
                xdest, ydest, self.torso.z,
                sprite=anneroy_bullet_dust_sprite, xvelocity=self.xvelocity,
                yvelocity=self.yvelocity, regulate_origin=True,
                image_xscale=abs(self.image_xscale),
                image_yscale=self.image_yscale,
                image_rotation=image_rotation, image_blend=self.image_blend)
            play_sound(shoot_sound, xdest, ydest)

    def kill(self):
        if self.lose_on_death:
            sge.snd.Music.stop()
            sge.game.current_room.alarms["death"] = DEATH_TIME

        play_sound(death_sound, self.x, self.y)
        self.alarms["death"] = ANNEROY_EXPLODE_TIME
        self.input_lock = True
        self.tangible = False
        self.reset_input()
        self.xvelocity = 0
        self.yvelocity = 0
        self.gravity = 0
        self.fixed_sprite = True
        self.image_speed = 0

    def warp_in(self):
        super(Anneroy, self).warp_in()
        self.alarms["fixed_sprite"] = WARP_TIME
        self.sprite = anneroy_turn_sprite
        self.image_index = 1
        self.image_speed = 0
        self.torso.visible = False
        self.fixed_sprite = True

    def warp_out(self):
        super(Anneroy, self).warp_out()
        self.alarms["fixed_sprite"] = WARP_TIME + 1
        self.sprite = anneroy_turn_sprite
        self.image_index = 1
        self.image_speed = 0
        self.torso.visible = False
        self.fixed_sprite = True

    def reset_image(self):
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
        if not self.crouching:
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
            self.reset_image()

            # Set legs
            if self.on_floor and self.was_on_floor:
                if self.crouching:
                    self.sprite = anneroy_legs_crouched_sprite
                else:
                    xm = (self.xvelocity > 0) - (self.xvelocity < 0)
                    speed = abs(self.xvelocity)
                    if speed > 0:
                        self.sprite = anneroy_legs_run_sprite
                        self.image_speed = speed * PLAYER_RUN_FRAMES_PER_PIXEL
                        if xm != self.facing:
                            self.image_speed *= -1

                        idle_torso_right = anneroy_torso_right_aim_right_sprite
                        idle_torso_left = anneroy_torso_left_aim_left_sprite
                    else:
                        self.sprite = anneroy_legs_stand_sprite
            else:
                self.sprite = anneroy_legs_jump_sprite
                self.image_index = -1

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
        self.torso.x = self.x + x * self.image_xscale
        self.torso.y = self.y + y * self.image_yscale
        self.torso.z = self.z + 0.1
        self.torso.image_xscale = abs(self.image_xscale)
        self.torso.image_yscale = self.image_yscale
        self.torso.image_alpha = self.image_alpha
        self.torso.image_blend = self.image_blend

    def event_create(self):
        self.torso = sge.dsp.Object.create(self.x, self.y, self.z + 0.1,
                                           regulate_origin=True)
        super(Anneroy, self).event_create()

    def event_begin_step(self, time_passed, delta_mult):
        super(Anneroy, self).event_begin_step(time_passed, delta_mult)

        if not self.on_floor and self.crouching:
            self.press_up()

    def event_alarm(self, alarm_id):
        super(Anneroy, self).event_alarm(alarm_id)

        if alarm_id == "fixed_sprite":
            self.fixed_sprite = False
        elif alarm_id == "shoot_lock":
            if self.shoot_pressed:
                self.shoot()
        elif alarm_id == "death":
            self.destroy()

    def event_animation_end(self):
        if self.fixed_sprite in {"turn", "crouch", "anim"}:
            self.fixed_sprite = False

    def event_physics_collision_top(self, other, move_loss):
        super(Anneroy, self).event_physics_collision_top(other, move_loss)
        self.event_animation_end()

    def event_physics_collision_bottom(self, other, move_loss):
        super(Anneroy, self).event_physics_collision_bottom(other, move_loss)

        if not self.was_on_floor:
            self.reset_image()
            self.sprite = anneroy_legs_land_sprite
            self.image_speed = None
            self.image_index = 0
            self.fixed_sprite = "anim"
            play_sound(land_sound, self.x, self.y)

    def event_jump(self):
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

    killed_by_void = True
    shootable = False
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

    def move(self):
        pass

    def touch(self, other):
        pass

    def shoot(self, other):
        pass

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
                    self.stop_down()
            elif on_slope:
                self.yvelocity = self.slide_speed * (on_slope[0].bbox_height /
                                                     on_slope[0].bbox_width)
        else:
            if self.yvelocity < self.fall_speed:
                self.yacceleration = self.gravity
            else:
                self.yvelocity = self.fall_speed
                self.yacceleration = 0

        self.was_on_floor = on_floor or on_slope


class WalkingObject(FallingObject):

    """
    Walks toward the player.  Turns around at walls, and can also be set
    to turn around at ledges with the stayonplatform attribute.
    """

    walk_speed = PLAYER_MAX_SPEED
    stayonplatform = False

    def set_direction(self, direction):
        self.xvelocity = self.walk_speed * direction
        self.image_xscale = abs(self.image_xscale) * direction

    def move(self):
        super(WalkingObject, self).move()

        if not self.xvelocity:
            player = self.get_nearest_player()
            if player is not None:
                self.set_direction(1 if self.x < player.x else -1)
            else:
                self.set_direction(-1)

        on_floor = self.get_bottom_touching_wall()
        on_slope = self.get_bottom_touching_slope()
        if (on_floor or on_slope) and self.stayonplatform:
            if self.xvelocity < 0:
                for tile in on_floor:
                    if tile.bbox_left < self.x:
                        break
                else:
                    if not on_slope:
                        self.set_direction(1)
            else:
                for tile in on_floor:
                    if tile.bbox_right > self.x:
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


class CrowdObject(WalkingObject, CrowdBlockingObject):

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
            super(CrowdObject, self).event_collision(other, xdirection,
                                                     ydirection)


class Shard(FallingObject):

    """Like Corpse, but bounces around a bit before disappearing."""

    fall_speed = 99
    bounce = 0.5
    friction = 0.95
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
        super(Shard, self).move()
        self.speed *= self.friction

    def event_alarm(self, alarm_id):
        if alarm_id == "die":
            self.destroy()


class Enemy(InteractiveObject):

    shootable = True
    touch_damage = 5
    hp = 1

    def touch(self, other):
        other.hurt(self.touch_damage)

    def shoot(self, other):
        # TODO: Handle different kinds of bullets
        self.hp -= 1
        if self.hp <= 0:
            self.kill()
        else:
            self.hurt()

    def hurt(self):
        pass

    def kill(self):
        blend = sge.gfx.Color((255, 255, 255, 0))
        spr = sge.gfx.Sprite.from_tween(
            self.sprite, int(FPS / 6), fps=FPS, blend=blend,
            blend_mode=sge.BLEND_RGBA_MULTIPLY)
        Smoke.create(self.x, self.y, z=self.z, sprite=spr, tangible=False,
                     image_xscale=self.image_xscale,
                     image_yscale=self.image_yscale,
                     image_rotation=self.image_rotation,
                     image_alpha=self.image_alpha,
                     image_blend=self.image_blend,
                     image_blend_mode=self.image_blend_mode)

        if ("life_orb" in progress_flags and
                random.random() < LIFE_FORCE_CHANCE):
            LifeForce.create(self.image_xcenter, self.image_ycenter,
                             z=self.z - 0.1)

        play_sound(enemy_death_sound, self.image_xcenter, self.image_ycenter)
        self.destroy()


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


class Frog(Enemy, FallingObject, CrowdBlockingObject):

    slide_speed = 0
    jump_distance = 200
    jump_height = 2 * TILE_SIZE + 1
    jump_speed = 3
    jump_interval = FPS / 2

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
        super(Frog, self).event_step(time_passed, delta_mult)

        if ("jump" not in self.alarms and self.was_on_floor and
                not self.yvelocity):
            self.alarms["jump"] = self.jump_interval
            target = self.get_nearest_player()
            if target is not None:
                xvec = target.x - self.image_xcenter
                self.image_xscale = math.copysign(self.image_xscale, xvec)

        if self.was_on_floor:
            self.sprite = frog_stand_sprite
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


class Bat(Enemy, InteractiveCollider, CrowdBlockingObject):

    charge_distance = 200
    charge_speed = 3
    return_speed = 2
    return_delay = 15
    repeat_delay = 60

    def __init__(self, x, y, **kwargs):
        self.returning = False
        kwargs["sprite"] = bat_sprite
        sge.dsp.Object.__init__(self, x, y, **kwargs)

    def attack(self, target):
        xvec = target.x - self.image_xcenter
        yvec = target.y - self.image_ycenter
        dist = math.hypot(xvec, yvec)
        if dist <= self.charge_distance:
            self.speed = self.charge_speed
            self.move_direction = math.degrees(math.atan2(yvec, xvec))
            self.image_speed = self.sprite.speed * 2

    def stop(self):
        self.speed = 0
        self.image_speed = None
        if self.returning:
            self.returning = False
            self.alarms["charge_wait"] = self.repeat_delay
        else:
            self.returning = True
            self.alarms["return"] = self.return_delay

    def stop_left(self):
        self.stop()

    def stop_right(self):
        self.stop()

    def stop_up(self):
        self.stop()

    def stop_down(self):
        self.stop()

    def event_create(self):
        self.image_xscale *= random.choice([1, -1])

    def event_step(self, time_passed, delta_mult):
        super(Bat, self).event_step(time_passed, delta_mult)

        if (self.speed == 0 and "charge_wait" not in self.alarms and
                not self.returning):
            target = self.get_nearest_player()
            if target is not None:
                self.attack(target)

        if self.xvelocity:
            self.image_xscale = math.copysign(self.image_xscale, self.xvelocity)

    def event_alarm(self, alarm_id):
        if alarm_id == "return":
            xvec = self.xstart - self.x
            yvec = self.ystart - self.y
            pth = xsge_path.Path.create(self.x, self.y, points=[(xvec, yvec)])
            def evt_follow_end(obj, self=pth): obj.stop()
            pth.event_follow_end = evt_follow_end
            pth.follow_start(self, self.return_speed)


class Boss(InteractiveObject):

    def __init__(self, x, y, ID="boss", death_timeline=None, stage=0,
                 **kwargs):
        self.ID = ID
        self.death_timeline = death_timeline
        self.stage = stage
        super(Boss, self).__init__(x, y, **kwargs)

    def event_create(self):
        super(Boss, self).event_create()
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
        super(LifeForce, self).__init__(*args, **kwargs)

    def move(self):
        if "set_direction" not in self.alarms:
            self.alarms["set_direction"] = FPS / 4
            target = self.get_nearest_player()
            if target is not None:
                xvec = target.x - self.image_xcenter
                yvec = target.y - self.image_ycenter
                self.speed = LIFE_FORCE_SPEED
                self.move_direction = math.degrees(math.atan2(yvec, xvec))
            else:
                self.speed = 0

    def touch(self, other):
        other.hp += LIFE_FORCE_HEAL
        play_sound(heal_sound, other.x, other.y)
        self.destroy()


class AnneroyBullet(InteractiveObject):

    def dissipate(self, xdirection=0, ydirection=0):
        if self in sge.game.current_room.objects:
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

    def event_create(self):
        self.alarms["die"] = ANNEROY_BULLET_LIFE

    def event_step(self, time_passed, delta_mult):
        room = sge.game.current_room
        if (self.bbox_right < 0 or self.bbox_left > room.width or
                self.bbox_bottom < 0 or self.bbox_top > room.height):
            self.destroy()

    def event_collision(self, other, xdirection, ydirection):
        super(AnneroyBullet, self).event_collision(other, xdirection, ydirection)

        if isinstance(other, InteractiveObject) and other.shootable:
            other.shoot(self)
            self.dissipate(xdirection, ydirection)
        elif isinstance(other, xsge_physics.Wall):
            point_x = self.x
            point_y = self.y
            if ((self.xvelocity > 0 and self.yvelocity > 0) or
                    (self.xvelocity < 0 and self.yvelocity < 0)):
                collisions = sge.collision.line(
                    self.bbox_left, self.bbox_top, self.bbox_right,
                    self.bbox_bottom)
            elif ((self.xvelocity > 0 and self.yvelocity < 0) or
                  (self.xvelocity < 0 and self.yvelocity > 0)):
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
                                if isinstance(obj, Stone):
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
                                if isinstance(obj, Stone):
                                    obj.destroy()

                if touching:
                    self.dissipate(xdirection, ydirection)

    def event_alarm(self, alarm_id):
        if alarm_id == "die":
            self.destroy()


class FakeTile(sge.dsp.Object):

    def event_create(self):
        self.tangible = False


class Stone(xsge_physics.Solid):

    shard_num_min = 1
    shard_num_max = 4
    shard_speed_min = 2
    shard_speed_max = 5
    shootable = False
    spikeable = False

    fakes = ()

    def event_create(self):
        self.checks_collisions = False
        self.fakes = []
        for other in sge.game.current_room.get_objects_at(
                self.image_left, self.image_top, self.image_width,
                self.image_height):
            if (isinstance(other, FakeTile) and
                    self.image_left < other.image_right and
                    self.image_right > other.image_left and
                    self.image_top < other.image_bottom and
                    self.image_bottom > other.image_top):
                self.fakes.append(other)

    def event_destroy(self):
        for other in self.fakes:
            other.destroy()

        shard_num = random.randint(self.shard_num_min, self.shard_num_max)
        for i in six.moves.range(shard_num):
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


class Powerup(InteractiveObject):

    message = _("USELESS ARTIFACT\n\nIt doesn't seem to do anything")

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
        rm_x, rm_y = map_rooms.get(sge.game.current_room.fname, (0, 0))
        px = rm_x + get_xregion(self.image_xcenter)
        py = rm_y + get_yregion(self.image_ycenter)
        map_removed.append(("powerup", px, py))

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


class Etank(Powerup):

    message = _("E-TANK\n\nExtra energy capacity acquired")

    def collect(self, other):
        global etanks
        etanks += 1
        other.refresh()


class LifeOrb(Powerup):

    message = _("LIFE ORB\n\nAbsorb life force from defeated enemies")

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = life_orb_sprite
        super(LifeOrb, self).__init__(x, y, **kwargs)

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("life_orb")


class Map(Powerup):

    message = _(
        'HANDHELD MAP\n\nSee mini-map in HUD; see full map by pressing "map" button or from pause menu')

    def __init__(self, x, y, **kwargs):
        kwargs["sprite"] = powerup_map_sprite
        super(Map, self).__init__(x, y, **kwargs)

    def collect(self, other):
        global progress_flags
        progress_flags = progress_flags[:]
        progress_flags.append("map")


class MapDisk(Powerup):

    message = _("MAP DISK\n\nArea map data loaded")

    def __init__(self, x, y, rooms=None, **kwargs):
        if rooms:
            self.rooms = rooms.split(',')
        else:
            self.rooms = []
        super(MapDisk, self).__init__(x, y, **kwargs)

    def collect(self, other):
        global map_revealed

        for fname in self.rooms:
            room = Level.load(fname, True)
            rm_x, rm_y = map_rooms.get(fname, (0, 0))
            rm_w = int(math.ceil(room.width / SCREEN_SIZE[0]))
            rm_h = int(math.ceil(room.height / SCREEN_SIZE[1]))
            
            ignore_regions = set()
            for obj in room.objects:
                if isinstance(obj, IgnoreRegion):
                    rx1 = rm_x + get_xregion(obj.bbox_left)
                    rx2 = rm_x + get_xregion(obj.bbox_right - 1)
                    ry1 = rm_y + get_yregion(obj.bbox_top)
                    ry2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                    for ry in six.moves.range(ry1, ry2 + 1):
                        for rx in six.moves.range(rx1, rx2 + 1):
                            ignore_regions.add((rx, ry))

            for y in six.moves.range(rm_y, rm_y + rm_h):
                for x in six.moves.range(rm_x, rm_x + rm_w):
                    if ((x, y) not in ignore_regions and
                            (x, y) not in map_revealed):
                        map_revealed = map_revealed[:]
                        map_revealed.append((x, y))

        sge.game.regulate_speed()


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
            other.yvelocity = get_jump_speed(TILE_SIZE / 2, other.gravity)

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
        x, y = map_rooms.get(sge.game.current_room.fname, (0, 0))
        x += get_xregion(self.image_xcenter)
        y += get_yregion(self.image_ycenter)
        i = (sge.game.current_room.fname, self.spawn_id, x, y)
        if i not in warp_pads:
            warp_pads = warp_pads[:]
            warp_pads.append(i)
        save_game()

    def spawn(self, other):
        if not self.created:
            self.create_children()
        other.x = self.image_xcenter
        other.bbox_bottom = self.image_top
        other.z = self.z - 0.5
        other.init_position()
        other.warp_in()
        self.activate()
        play_sound(teleport_sound, self.image_xcenter, self.image_ycenter)

    def teleport(self, other):
        x, y = map_rooms.get(sge.game.current_room.fname, (0, 0))
        x += get_xregion(self.image_xcenter)
        y += get_yregion(self.image_ycenter)
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
        super(WarpPad, self).event_create()
        if not self.created:
            self.create_children()

    def event_collision(self, other, xdirection, ydirection):
        global progress_flags

        if isinstance(other, Player):
            if not self.activated and (xdirection or ydirection):
                self.activate()
                other.refresh()
                play_sound(warp_pad_sound, self.image_xcenter,
                           self.image_ycenter)

                if "warp" not in progress_flags:
                    progress_flags.append("warp")
                    DialogBox(gui_handler, self.message).show()


class DoorBarrier(InteractiveObject, xsge_physics.Solid):

    shootable = True

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
        super(DoorFrameX, self).event_create()


class DoorFrameY(DoorFrame):

    edge2_area = (56, 0, 8, 8)

    def event_create(self):
        self.closed_sprite = doorframe_regular_y_closed_sprite
        self.open_sprite = doorframe_regular_y_open_sprite
        self.barrier_sprite = door_barrier_y_sprite
        super(DoorFrameY, self).event_create()


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
        Tunnel.create(frame.barrier.bbox_left - TILE_SIZE,
                      frame.barrier.bbox_top, dest=self.dest,
                      bbox_width=TILE_SIZE,
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
                      dest=self.dest, bbox_width=TILE_SIZE,
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
                      frame.barrier.bbox_top - TILE_SIZE, dest=self.dest,
                      bbox_width=frame.barrier.bbox_width,
                      bbox_height=TILE_SIZE)
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
                      bbox_height=TILE_SIZE)
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
        super(MovingObjectPath, self).__init__(x, y, **kwargs)

    def event_create(self):
        if self.parent is not None:
            for obj in sge.game.current_room.objects:
                if (isinstance(obj, self.__class__) and
                        obj.path_id == self.parent):
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
        super(MovingPlatformPath, self).event_create()
        obj = self.obj()
        if obj:
            obj.path = self

    def follow_start(self, obj, *args, **kwargs):
        super(MovingPlatformPath, self).follow_start(obj, *args, **kwargs)
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
        x += TILE_SIZE / 2
        y += TILE_SIZE / 2
        super(CircoflamePath, self).__init__(x, y, z=z, points=points)

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
        super(CameraGuide, self).__init__(x, y, **kwargs)


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
                                                           "credits.tmx"))
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

        if self.choice in six.moves.range(len(save_slots)):
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

        if self.choice in six.moves.range(len(save_slots)):
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
            play_music(sge.game.current_room.music)
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
            # This somewhat complicated method is to prevent rounding
            # irregularities.
            threshold = ((int(joystick_threshold * 100) + 5) % 100) / 100
            if not threshold:
                threshold = 0.0001
            joystick_threshold = threshold
            xsge_gui.joystick_threshold = threshold
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 7:
            play_sound(confirm_sound)
            KeyboardMenu.create_page()
        elif self.choice == 8:
            play_sound(confirm_sound)
            JoystickMenu.create_page()
        elif self.choice == 9:
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
        def toggle_key(key, new_key, self=self):
            if new_key in key:
                if len(key) > 1:
                    key.remove(new_key)
            else:
                refused = False
                for other_key in [
                        left_key[self.page], right_key[self.page],
                        up_key[self.page], down_key[self.page],
                        jump_key[self.page], shoot_key[self.page],
                        aim_diag_key[self.page], aim_up_key[self.page],
                        aim_down_key[self.page], mode_reset_key[self.page],
                        mode_key[self.page], pause_key[self.page],
                        map_key[self.page]]:
                    if new_key in other_key:
                        if len(other_key) > 1:
                            other_key.remove(new_key)
                        else:
                            refused = True

                if not refused:
                    key.append(new_key)
                    while len(key) > 2:
                        key.pop(0)

        if self.choice == 0:
            play_sound(select_sound)
            KeyboardMenu.create_page(default=self.choice, page=(self.page + 1))
        elif self.choice == 1:
            k = wait_key()
            if k is not None:
                toggle_key(left_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 2:
            k = wait_key()
            if k is not None:
                toggle_key(right_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 3:
            k = wait_key()
            if k is not None:
                toggle_key(up_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 4:
            k = wait_key()
            if k is not None:
                toggle_key(down_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 5:
            k = wait_key()
            if k is not None:
                toggle_key(jump_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 6:
            k = wait_key()
            if k is not None:
                toggle_key(shoot_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 7:
            k = wait_key()
            if k is not None:
                toggle_key(aim_diag_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 8:
            k = wait_key()
            if k is not None:
                toggle_key(aim_up_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 9:
            k = wait_key()
            if k is not None:
                toggle_key(aim_down_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 10:
            k = wait_key()
            if k is not None:
                toggle_key(mode_reset_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 11:
            k = wait_key()
            if k is not None:
                toggle_key(mode_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 12:
            k = wait_key()
            if k is not None:
                toggle_key(pause_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 13:
            k = wait_key()
            if k is not None:
                toggle_key(map_key[self.page], k)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            KeyboardMenu.create_page(default=self.choice, page=self.page)
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
        def toggle_js(js, new_js, self=self):
            if new_js in js:
                js.remove(new_js)
            else:
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

        if self.choice == 0:
            play_sound(select_sound)
            JoystickMenu.create_page(default=self.choice, page=(self.page + 1))
        elif self.choice == 1:
            js = wait_js()
            if js is not None:
                toggle_js(left_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 2:
            js = wait_js()
            if js is not None:
                toggle_js(right_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 3:
            js = wait_js()
            if js is not None:
                toggle_js(up_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 4:
            js = wait_js()
            if js is not None:
                toggle_js(down_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 5:
            js = wait_js()
            if js is not None:
                toggle_js(jump_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 6:
            js = wait_js()
            if js is not None:
                toggle_js(shoot_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 7:
            js = wait_js()
            if js is not None:
                toggle_js(aim_diag_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 8:
            js = wait_js()
            if js is not None:
                toggle_js(aim_up_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 9:
            js = wait_js()
            if js is not None:
                toggle_js(aim_down_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 10:
            js = wait_js()
            if js is not None:
                toggle_js(mode_reset_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 11:
            js = wait_js()
            if js is not None:
                toggle_js(mode_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 12:
            js = wait_js()
            if js is not None:
                toggle_js(pause_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
        elif self.choice == 13:
            js = wait_js()
            if js is not None:
                toggle_js(map_js[self.page], js)
                set_gui_controls()
                play_sound(confirm_sound)
            else:
                play_sound(cancel_sound)
            JoystickMenu.create_page(default=self.choice, page=self.page)
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
            self.show()
            return self

    def event_change_keyboard_focus(self):
        play_sound(select_sound)


class PauseMenu(ModalMenu):

    @classmethod
    def create(cls, default=0, player_x=None, player_y=None):
        if "map" in progress_flags:
            items = [_("Continue"), _("View Map"), _("Return to Title Screen")]
        else:
            items = [_("Continue"), _("Return to Title Screen")]

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
        self.show()
        return self

    def event_choose(self):
        if self.choice == 1:
            if "map" in progress_flags:
                play_sound(select_sound)
                MapDialog(self.player_x, self.player_y).show()
            else:
                sge.game.start_room.start()
        elif self.choice == 2:
            sge.game.start_room.start()
        else:
            play_sound(select_sound)


class MapDialog(xsge_gui.Dialog):

    def __init__(self, player_x, player_y):
        self.xcells = int(sge.game.width / MAP_CELL_WIDTH)
        self.ycells = int(sge.game.height / MAP_CELL_HEIGHT)
        w = self.xcells * MAP_CELL_WIDTH
        h = self.ycells * MAP_CELL_HEIGHT
        super(MapDialog, self).__init__(
            gui_handler, 0, 0, w, h, background_color=sge.gfx.Color("black"),
            border=False)
        self.player_x = player_x
        self.player_y = player_y
        self.map_x = player_x
        self.map_y = player_y
        self.map = xsge_gui.Widget(self, 0, 0, 0)
        self.draw_map()

    def draw_map(self):
        x = self.map_x - int(self.xcells / 2)
        y = self.map_y - int(self.ycells / 2)
        self.map.sprite = draw_map(x, y, self.xcells, self.ycells,
                                   self.player_x, self.player_y)

    def event_press_left(self):
        play_sound(select_sound)
        self.map_x -= 1
        self.draw_map()

    def event_press_right(self):
        play_sound(select_sound)
        self.map_x += 1
        self.draw_map()

    def event_press_up(self):
        play_sound(select_sound)
        self.map_y -= 1
        self.draw_map()

    def event_press_down(self):
        play_sound(select_sound)
        self.map_y += 1
        self.draw_map()

    def event_press_enter(self):
        play_sound(select_sound)
        self.destroy()

    def event_press_escape(self):
        play_sound(select_sound)
        self.destroy()


class TeleportDialog(MapDialog):

    def __init__(self, selection):
        self.selection = selection
        x = self.selection[2]
        y = self.selection[3]
        super(TeleportDialog, self).__init__(x, y)

    def update_selection(self):
        self.map_x = self.selection[2]
        self.map_y = self.selection[3]
        self.player_x = self.map_x
        self.player_y = self.map_y
        self.draw_map()

    def event_press_left(self):
        play_sound(select_sound)

        if self.selection in warp_pads:
            i = warp_pads.index(self.selection)
        else:
            i = 0

        self.selection = warp_pads[(i - 1) % len(warp_pads)]
        self.update_selection()

    def event_press_right(self):
        play_sound(select_sound)

        if self.selection in warp_pads:
            i = warp_pads.index(self.selection)
        else:
            i = -1

        self.selection = warp_pads[(i + 1) % len(warp_pads)]
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
        if self.text[-1] not in (' ', '\n', '\t'):
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
        x = sge.game.width / 2 - width / 2
        y = sge.game.height / 2 - height / 2
        super(DialogBox, self).__init__(
            parent, x, y, width, height,
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
        if (isinstance(room, Level) and
                room.timeline_skip_target is not None and
                room.timeline_step < room.timeline_skip_target):
            room.timeline_skipto(room.timeline_skip_target)


def get_object(x, y, cls=None, **kwargs):
    cls = TYPES.get(cls, xsge_tmx.Decoration)
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
    return int(x / SCREEN_SIZE[0])


def get_yregion(y):
    return int(y / SCREEN_SIZE[1])


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
    # Set the controls for xsge_gui based on the player controls.
    xsge_gui.next_widget_keys = list(itertools.chain.from_iterable(down_key))
    xsge_gui.previous_widget_keys = list(itertools.chain.from_iterable(up_key))
    xsge_gui.left_keys = list(itertools.chain.from_iterable(left_key))
    xsge_gui.right_keys = list(itertools.chain.from_iterable(right_key))
    xsge_gui.up_keys = list(itertools.chain.from_iterable(up_key))
    xsge_gui.down_keys = list(itertools.chain.from_iterable(down_key))
    xsge_gui.enter_keys = (list(itertools.chain.from_iterable(jump_key)) +
                           list(itertools.chain.from_iterable(shoot_key)) +
                           list(itertools.chain.from_iterable(pause_key)))
    xsge_gui.escape_keys = (list(itertools.chain.from_iterable(mode_key)) +
                            list(itertools.chain.from_iterable(map_key)) +
                            ["escape"])
    xsge_gui.next_widget_joystick_events = (
        list(itertools.chain.from_iterable(down_js)))
    xsge_gui.previous_widget_joystick_events = (
        list(itertools.chain.from_iterable(up_js)))
    xsge_gui.left_joystick_events = list(itertools.chain.from_iterable(left_js))
    xsge_gui.right_joystick_events = (
        list(itertools.chain.from_iterable(right_js)))
    xsge_gui.up_joystick_events = list(itertools.chain.from_iterable(up_js))
    xsge_gui.down_joystick_events = list(itertools.chain.from_iterable(down_js))
    xsge_gui.enter_joystick_events = (
        list(itertools.chain.from_iterable(jump_js)) +
        list(itertools.chain.from_iterable(shoot_js)) +
        list(itertools.chain.from_iterable(pause_js)))
    xsge_gui.escape_joystick_events = (
        list(itertools.chain.from_iterable(mode_js)) +
        list(itertools.chain.from_iterable(map_js)))


def wait_key():
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
        text = _("Press the key you wish to toggle, or Escape to cancel.")
        sge.game.project_text(font, text, sge.game.width / 2,
                              sge.game.height / 2, width=sge.game.width,
                              height=sge.game.height,
                              color=sge.gfx.Color("white"),
                              halign="center", valign="middle")

        # Refresh
        sge.game.refresh()


def wait_js():
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
                                             "hat_center_y"} and
                        event.value >= joystick_threshold):
                    sge.game.pump_input()
                    sge.game.input_events = []
                    return (event.js_id, event.input_type, event.input_id)

        # Regulate speed
        sge.game.regulate_speed(fps=10)

        # Project text
        text = _("Press the joystick button, axis, or hat direction you wish to toggle, or the Escape key to cancel.")
        sge.game.project_text(font, text, sge.game.width / 2,
                              sge.game.height / 2, width=sge.game.width,
                              height=sge.game.height,
                              color=sge.gfx.Color("white"),
                              halign="center", valign="middle")

        # Refresh
        sge.game.refresh()


def show_error(message):
    if sge.game.current_room is not None:
        sge.game.pump_input()
        sge.game.input_events = []
        sge.game.mouse.visible = True
        xsge_gui.show_message(message=message, title=_("Error"),
                              buttons=[_("Ok")], width=392)
        sge.game.mouse.visible = False
    else:
        print(message)


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
                vx = view.x + view.width / 2
                vy = view.y + view.height / 2
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
                reldist = rng - (dist - SOUND_MAX_RADIUS)
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


def play_music(music, force_restart=False):
    """Play the given music file, starting with its start piece."""
    if music_enabled:
        if music:
            music_object = loaded_music.get(music)
            if music_object is None:
                try:
                    music_object = sge.snd.Music(os.path.join(DATA, "music",
                                                              music))
                except (IOError, OSError):
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
                    music_start_object = sge.snd.Music(os.path.join(DATA, "music",
                                                                    music_start))
                except (IOError, OSError):
                    pass
                else:
                    loaded_music[music_start] = music_start_object

            if (force_restart or (not music_object.playing and
                                  (music_start_object is None or
                                   not music_start_object.playing))):
                sge.snd.Music.clear_queue()
                sge.snd.Music.stop()
                if music_start_object is not None:
                    music_start_object.play()
                    music_object.queue(loops=None)
                else:
                    music_object.play(loops=None)
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
    global etanks

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
    etanks = 0


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
           "fps_enabled": fps_enabled,
           "joystick_threshold": joystick_threshold, "keys": keys_cfg,
           "joystick": js_cfg}

    with open(os.path.join(CONFIG, "config.json"), 'w') as f:
        json.dump(cfg, f, indent=4)

    with open(os.path.join(CONFIG, "save_slots.json"), 'w') as f:
        json.dump(save_slots, f, indent=4)


def save_game():
    global save_slots

    if current_save_slot is not None:
        save_slots[current_save_slot] = {
            "player_name": player_name,
            "watched_timelines": watched_timelines,
            "current_level": current_level,
            "spawn_point": spawn_point,
            "map_revealed": map_revealed,
            "map_explored": map_explored,
            "map_removed": map_removed,
            "warp_pads": warp_pads,
            "powerups": powerups,
            "progress_flags": progress_flags,
            "etanks": etanks}

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

    if (current_save_slot is not None and
            save_slots[current_save_slot] is not None):
        slot = save_slots[current_save_slot]
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
        etanks = slot.get("etanks", 0)
    else:
        set_new_game()


def start_game():
    global player

    player = Anneroy(0, 0)

    if current_level is None:
        level = Level.load("0.tmx")
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

    print(_("Generating new map files; this may take some time."))
    files_checked = set()
    files_remaining = {("0.tmx", 0, 0, None, None)}
    map_rooms = {}
    map_objects = {}

    while files_remaining:
        fname, rm_x, rm_y, origin_level, origin_spawn = files_remaining.pop()
        files_checked.add(fname)
        room = Level.load(fname, True)
        rm_w = int(math.ceil(room.width / SCREEN_SIZE[0]))
        rm_h = int(math.ceil(room.height / SCREEN_SIZE[1]))

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
                for ry in six.moves.range(ry1, ry2 + 1):
                    for rx in six.moves.range(rx1, rx2 + 1):
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

                if (dx, dy) not in ignore_regions:
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
                px = rm_x + get_xregion(obj.image_xcenter)
                py = rm_y + get_yregion(obj.image_ycenter)
                if (px, py) not in ignore_regions:
                    map_objects.setdefault((px, py), []).append("powerup")
            elif isinstance(obj, MapLeftWall):
                wx = rm_x + get_xregion(obj.bbox_left)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in six.moves.range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_left")
            elif isinstance(obj, MapRightWall):
                wx = rm_x + get_xregion(obj.bbox_right - 1)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in six.moves.range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_right")
            elif isinstance(obj, MapTopWall):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_top)
                for wx in six.moves.range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_top")
            elif isinstance(obj, MapBottomWall):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wx in six.moves.range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("wall_bottom")
            elif isinstance(obj, MapLeftDoor):
                wx = rm_x + get_xregion(obj.bbox_left)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in six.moves.range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_left")
            elif isinstance(obj, MapRightDoor):
                wx = rm_x + get_xregion(obj.bbox_right - 1)
                wy1 = rm_y + get_yregion(obj.bbox_top)
                wy2 = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wy in six.moves.range(wy1, wy2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_right")
            elif isinstance(obj, MapTopDoor):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_top)
                for wx in six.moves.range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_top")
            elif isinstance(obj, MapBottomDoor):
                wx1 = rm_x + get_xregion(obj.bbox_left)
                wx2 = rm_x + get_xregion(obj.bbox_right - 1)
                wy = rm_y + get_yregion(obj.bbox_bottom - 1)
                for wx in six.moves.range(wx1, wx2 + 1):
                    if (wx, wy) not in ignore_regions:
                        map_objects.setdefault((wx, wy), []).append("door_bottom")

        for x in six.moves.range(rm_x, rm_x + rm_w):
            y = rm_y
            if ((x, y) not in ignore_regions and
                    "door_top" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_top")

            y = rm_y + rm_h - 1
            if ((x, y) not in ignore_regions and
                    "door_bottom" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_bottom")

        for y in six.moves.range(rm_y, rm_y + rm_h):
            x = rm_x
            if ((x, y) not in ignore_regions and
                    "door_left" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_left")

            x = rm_x + rm_w - 1
            if ((x, y) not in ignore_regions and
                    "door_right" not in map_objects.setdefault((x, y), [])):
                map_objects[(x, y)].append("wall_right")

    f_objects = {}
    for x, y in map_objects:
        i = "{},{}".format(x, y)
        f_objects[i] = map_objects[(x, y)]

    with open(os.path.join(DATA, "map", "rooms.json"), 'w') as f:
        json.dump(map_rooms, f, indent=4, sort_keys=True)

    with open(os.path.join(DATA, "map", "objects.json"), 'w') as f:
        json.dump(f_objects, f, indent=4, sort_keys=True)


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

    removed = map_removed[:]
    s_w = w * MAP_CELL_WIDTH
    s_h = h * MAP_CELL_HEIGHT
    map_sprite = sge.gfx.Sprite(width=s_w, height=s_h)
    map_sprite.draw_rectangle(0, 0, s_w, s_h, fill=sge.gfx.Color("black"))

    for ex, ey in map_explored:
        dx = (ex - x) * MAP_CELL_WIDTH
        dy = (ey - y) * MAP_CELL_HEIGHT
        map_sprite.draw_rectangle(dx, dy, MAP_CELL_WIDTH, MAP_CELL_HEIGHT,
                                  fill=sge.gfx.Color("navy"))

    for ox, oy in set(map_objects) & set(map_revealed + map_explored):
        if x <= ox < x + w and y <= oy < y + h:
            for obj in map_objects[(ox, oy)]:
                if (obj, ox, oy) in removed:
                    removed.remove((obj, ox, oy))
                else:
                    dx = (ox - x) * MAP_CELL_WIDTH
                    dy = (oy - y) * MAP_CELL_HEIGHT
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
        sge.game.scale = FSSCALE if FSSCALE else None
        sge.game.fullscreen = True
    else:
        sge.game.scale = SCALE
        sge.game.fullscreen = False
        sge.game.scale = None


TYPES = {"solid_left": SolidLeft, "solid_right": SolidRight,
         "solid_top": SolidTop, "solid_bottom": SolidBottom, "solid": Solid,
         "slope_topleft": SlopeTopLeft, "slope_topright": SlopeTopRight,
         "slope_bottomleft": SlopeBottomLeft,
         "slope_bottomright": SlopeBottomRight,
         "moving_platform": MovingPlatform, "spike_left": SpikeLeft,
         "spike_right": SpikeRight, "spike_top": SpikeTop,
         "spike_bottom": SpikeBottom, "death": Death, "frog": Frog, "bat": Bat,
         "fake_tile": FakeTile, "weak_stone": WeakStone,
         "spike_stone": SpikeStone, "artifact": Powerup, "etank": Etank,
         "life_orb": LifeOrb, "map": Map, "map_disk": MapDisk,
         "warp_pad": WarpPad, "doorframe_x": DoorFrameX,
         "doorframe_y": DoorFrameY, "door_left": LeftDoor,
         "door_right": RightDoor, "door_up": UpDoor, "door_down": DownDoor,
         "timeline_switcher": TimelineSwitcher, "enemies": get_object,
         "doors": get_object, "stones": get_object, "powerups": get_object,
         "objects": get_object, "moving_platform_path": MovingPlatformPath,
         "triggered_moving_platform_path": TriggeredMovingPlatformPath,
         "player": PlayerLayer, "camera_x_guide": CameraXGuide,
         "camera_y_guide": CameraYGuide, "map_wall_left": MapLeftWall,
         "map_wall_right": MapRightWall, "map_wall_top": MapTopWall,
         "map_wall_bottom": MapBottomWall, "map_door_left": MapLeftDoor,
         "map_door_right": MapRightDoor, "map_door_top": MapTopDoor,
         "map_door_bottom": MapBottomDoor, "map_ignore_region": IgnoreRegion}


print(_("Initializing game system..."))
Game(SCREEN_SIZE[0], SCREEN_SIZE[1], scale=SCALE, fps=FPS, delta=DELTA,
     delta_min=DELTA_MIN, delta_max=DELTA_MAX,
     window_text="Hexoshi {}".format(__version__))
     #window_icon=os.path.join(DATA, "images", "misc", "icon.png"))
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

if not os.path.exists(CONFIG):
    os.makedirs(CONFIG)

# Save error messages to a text file (so they aren't lost).
if not PRINT_ERRORS:
    stderr = os.path.join(CONFIG, "stderr.txt")
    if not os.path.isfile(stderr) or os.path.getsize(stderr) > 1000000:
        sys.stderr = open(stderr, 'w')
    else:
        sys.stderr = open(stderr, 'a')
    dt = datetime.datetime.now()
    sys.stderr.write("\n{}-{}-{} {}:{}:{}\n".format(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))
    del dt

# Load sprites
d = os.path.join(DATA, "images", "objects", "anneroy")
anneroy_torso_offset = {}

fname = os.path.join(d, "anneroy_sheet.png")

anneroy_turn_sprite = sge.gfx.Sprite.from_tileset(
    fname, 2, 109, 3, xsep=3, width=39, height=43, origin_x=19, origin_y=19,
    fps=10)

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

anneroy_bullet_dust_sprite = sge.gfx.Sprite.from_tileset(
    fname, 249, 119, width=26, height=16, origin_x=2, origin_y=7, fps=10)
anneroy_bullet_sprite = sge.gfx.Sprite.from_tileset(
    fname, 287, 123, width=17, height=6, origin_x=14, origin_y=3, bbox_x=-8,
    bbox_y=-8, bbox_width=16, bbox_height=16)
anneroy_bullet_dissipate_sprite = sge.gfx.Sprite.from_tileset(
    fname, 317, 102, 2, xsep=12, width=21, height=52, origin_x=12, origin_y=23,
    fps=10)

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

d = os.path.join(DATA, "images", "objects", "enemies")
frog_stand_sprite = sge.gfx.Sprite("frog_stand", d)
frog_jump_sprite = sge.gfx.Sprite("frog_jump", d)
frog_fall_sprite = sge.gfx.Sprite("frog_fall", d)
bat_sprite = sge.gfx.Sprite("bat", d, fps=10, bbox_x=3, bbox_y=4,
                            bbox_width=10, bbox_height=10)

d = os.path.join(DATA, "images", "objects", "doors")
door_barrier_x_sprite = sge.gfx.Sprite("barrier_x", d, origin_y=-8, fps=30,
                                       bbox_y=8, bbox_width=8, bbox_height=48)
door_barrier_y_sprite = sge.gfx.Sprite("barrier_y", d, origin_x=-8, fps=30,
                                       bbox_x=8, bbox_width=48, bbox_height=8)
doorframe_regular_x_closed_sprite = sge.gfx.Sprite("regular_x_closed", d)
doorframe_regular_x_open_sprite = sge.gfx.Sprite("regular_x_open", d)
doorframe_regular_y_closed_sprite = sge.gfx.Sprite("regular_y_closed", d)
doorframe_regular_y_open_sprite = sge.gfx.Sprite("regular_y_open", d)

d = os.path.join(DATA, "images", "objects", "stones")
stone_fragment_sprite = sge.gfx.Sprite("stone_fragment", d)

d = os.path.join(DATA, "images", "objects", "powerups")
life_orb_sprite = sge.gfx.Sprite("life_orb", d, fps=10)
powerup_map_sprite = sge.gfx.Sprite("map", d, fps=3)

d = os.path.join(DATA, "images", "objects", "misc")
warp_pad_active_sprite = sge.gfx.Sprite("warp_pad_active", d)
warp_pad_inactive_sprite = sge.gfx.Sprite("warp_pad_inactive", d)

d = os.path.join(DATA, "images", "map")
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

d = os.path.join(DATA, "images", "misc")
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
etank_full_sprite = sge.gfx.Sprite("etank_full", d)
life_force_sprite = sge.gfx.Sprite(
    "life_force", d, origin_x=7, origin_y=7, fps=10)

d = os.path.join(DATA, "images", "portraits")
portrait_sprites = {}
for fname in os.listdir(d):
    root, ext = os.path.splitext(fname)
    try:
        portrait = sge.gfx.Sprite(root, d)
    except (IOError, OSError):
        pass
    else:
        portrait_sprites[root] = portrait

# Load backgrounds
# TODO

# Load fonts
chars = ([six.unichr(i) for i in six.moves.range(32, 127)] +
         [None, ETANK_CHAR] + [' '] * 11 +
         [six.unichr(i) for i in six.moves.range(161, 384)])
font = sge.gfx.Font.from_sprite(font_sprite, chars, size=9, hsep=-1)
chars = [six.unichr(i) for i in six.moves.range(32, 127)] + [None]
font_big = sge.gfx.Font.from_sprite(font_big_sprite, chars, size=14,
                                    hsep=2, vsep=2)

chars = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" +
             "0123456789.,;:?!-_~#\"'&()[]|`\\/@^+=*$\xa3\u20ac<>  ") + [None]
font_small = sge.gfx.Font.from_sprite(font_small_sprite, chars, size=7,
                                      hsep=-1)

# Load sounds
shoot_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "shoot.wav"))
bullet_death_sound = sge.snd.Sound(
    os.path.join(DATA, "sounds", "bullet_death.ogg"), volume=0.2)
land_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "land.ogg"), volume=0.5)
hurt_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "hurt.wav"))
death_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "death.wav"))
powerup_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "powerup.wav"))
heal_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "heal.wav"))
warp_pad_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "warp_pad.ogg"))
teleport_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "teleport.wav"))
door_open_sound = sge.snd.Sound(
    os.path.join(DATA, "sounds", "door_open.ogg"), volume=0.5)
door_close_sound = sge.snd.Sound(
    os.path.join(DATA, "sounds", "door_close.ogg"), volume=0.5)
enemy_death_sound = sge.snd.Sound(
    os.path.join(DATA, "sounds", "enemy_death.wav"))
frog_jump_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "frog_jump.wav"))
select_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "select.ogg"))
pause_sound = select_sound
confirm_sound = sge.snd.Sound(None)
cancel_sound = sge.snd.Sound(None)
error_sound = sge.snd.Sound(None)
type_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "type.wav"))

# Create objects
##lava_animation = sge.dsp.Object(0, 0, sprite=lava_body_sprite, visible=False,
##                                tangible=False)

# Create rooms
sge.game.start_room = TitleScreen.load(
    os.path.join("special", "title_screen.tmx"), True)

sge.game.mouse.visible = False

# Load map data
map_rooms = {}
map_objects = {}
if not GEN_MAP:
    try:
        with open(os.path.join(DATA, "map", "rooms.json")) as f:
            d = json.load(f)
    except (IOError, ValueError):
        generate_map()
    else:
        for i in d:
            map_rooms[i] = tuple(d[i])

    try:
        with open(os.path.join(DATA, "map", "objects.json")) as f:
            d = json.load(f)
    except (IOError, ValueError):
        generate_map()
    else:
        for i in d:
            x, y = tuple(i.split(','))
            j = (int(x), int(y))
            map_objects[j] = d[i]
else:
    generate_map()

if SAVE_MAP:
    map_revealed = list(map_objects.keys())
    map_explored = map_revealed
    draw_map().save("map.png")
    map_revealed = []
    map_explored = []

try:
    with open(os.path.join(CONFIG, "config.json")) as f:
        cfg = json.load(f)
except (IOError, ValueError):
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
    with open(os.path.join(CONFIG, "save_slots.json")) as f:
        loaded_slots = json.load(f)
except (IOError, ValueError):
    pass
else:
    for i in six.moves.range(min(len(loaded_slots), len(save_slots))):
        save_slots[i] = loaded_slots[i]


if __name__ == '__main__':
    print(_("Starting game..."))

    try:
        sge.game.start()
    finally:
        write_to_disk()
