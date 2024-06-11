"""
CARLA manual control with steering wheel Logitech G920.

Change your wheel_config.ini according to your steering wheel.

To find out the values of your steering wheel use jstest-gtk in Ubuntu.

"""
from configparser import ConfigParser
import argparse
import collections
import datetime
import logging
import math
import random
import weakref

# add CARLA to sys path
import glob
import os
import sys
try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

try:
    import pygame
except ImportError as exc:
    raise RuntimeError('Cannot import pygame, make sure pygame package is installed') from exc

try:
    import numpy as np
    from multiprocessing import Pipe, Process
    sys.path.append('App_Zephyr_main')
except ImportError as exc:
    raise RuntimeError('Cannot import required libraries') from exc

import carla
from carla import ColorConverter as cc

from src.driving.sensors import CollisionSensor, GnssSensor, LaneInvasionSensor
from src.driving.zephyr_stream import monitor_and_send_biometrics
from src.scenarios.weather import WeatherManager, WEATHER_PRESETS


# global functions
def get_actor_display_name(actor, truncate=250):
    """
    Get a human-readable name for an actor.

    Args:
        actor (carla.Actor): The actor to get the name of.
        truncate (int, optional): Maximum length of the name. Defaults to 250.

    Returns:
        str: The display name of the actor.
    """
    name = ' '.join(actor.type_id.replace('_', '.').title().split('.')[1:])
    return (name[:truncate - 1] + u'\u2026') if len(name) > truncate else name


class World:
    """Controls simulation world settings"""

    def __init__(self, carla_world, hud, actor_filter):
        """
        Initialize the World class.

        Args:
            carla_world (carla.World): The CARLA world object.
            hud (HUD): The HUD object for displaying information.
            actor_filter (str): The filter to select the actor.
        """
        self.world = carla_world
        self.hud = hud
        self.player = None
        self.collision_sensor = None
        self.lane_invasion_sensor = None
        self.gnss_sensor = None
        self.camera_manager = None
        self._weather_man = WeatherManager(
            self.world,
            [act for act in self.world.get_actors() if "vehicle." in act.type_id]
        )
        self._weather_index = 0
        self._actor_filter = actor_filter
        self.restart()
        self.world.on_tick(hud.on_world_tick)

    def restart(self):
        """Restart world and default to initial settings"""
        # Keep same camera config if the camera manager exists.
        cam_index = self.camera_manager.index if self.camera_manager is not None else 0
        cam_pos_index = self.camera_manager.transform_index if self.camera_manager is not None else 0
        # Get a random blueprint.
        blueprint = random.choice(self.world.get_blueprint_library().filter(self._actor_filter))
        blueprint.set_attribute('role_name', 'hero')
        if blueprint.has_attribute('color'):
            color = random.choice(blueprint.get_attribute('color').recommended_values)
            blueprint.set_attribute('color', color)
        # Spawn the player.
        if self.player is not None:
            spawn_point = self.player.get_transform()
            spawn_point.location.z += 2.0
            spawn_point.rotation.roll = 0.0
            spawn_point.rotation.pitch = 0.0
            self.destroy()
            self.player = self.world.try_spawn_actor(blueprint, spawn_point)
        while self.player is None:
            spawn_points = self.world.get_map().get_spawn_points()
            spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()
            self.player = self.world.try_spawn_actor(blueprint, spawn_point)
        # Set up the sensors.
        self.collision_sensor = CollisionSensor(self.player, self.hud, get_actor_display_name)
        self.lane_invasion_sensor = LaneInvasionSensor(self.player, self.hud)
        self.gnss_sensor = GnssSensor(self.player)
        self.camera_manager = CameraManager(self.player, self.hud)
        self.camera_manager.transform_index = cam_pos_index
        self.camera_manager.set_sensor(cam_index, notify=False)
        actor_type = get_actor_display_name(self.player)
        self.hud.notification(actor_type)

    def next_weather(self):
        """Cycle through and apply weather presets."""
        self._weather_index +=  1
        self._weather_index %= len(WEATHER_PRESETS)
        preset = WEATHER_PRESETS[self._weather_index]
        self._weather_man.set_weather(preset[1])
        self._weather_man.set_time_of_day(preset[2])
        self._weather_man.apply_settings()

    def tick(self, clock):
        """
        Update HUD information every tick.

        Args:
            clock (pygame.time.Clock): Pygame clock to control the frame rate.
        """
        self.hud.tick(self, clock)

    def render(self, display):
        """
        Render driver camera view and HUD.

        Args:
            display (pygame.Surface): Pygame display surface.
        """
        self.camera_manager.render(display)
        self.hud.render(display)

    def destroy(self):
        """Destroy all sensors and the player actor."""
        sensors = [
            self.camera_manager.sensor,
            self.collision_sensor.sensor,
            self.lane_invasion_sensor.sensor,
            self.gnss_sensor.sensor]
        for sensor in sensors:
            if sensor is not None:
                sensor.stop()
                sensor.destroy()
        if self.player is not None:
            self.player.destroy()


class SteeringControl:
    """Parses and applies steering controls"""

    def __init__(self, world, start_in_autopilot):
        """
        Initialize the SteeringControl class.

        Args:
            world (World): The World object.
            start_in_autopilot (bool): Whether to start in autopilot mode.
        """
        self._autopilot_enabled = start_in_autopilot
        if isinstance(world.player, carla.Vehicle):
            self._control = carla.VehicleControl()
            world.player.set_autopilot(self._autopilot_enabled)
        elif isinstance(world.player, carla.Walker):
            self._control = carla.WalkerControl()
            self._autopilot_enabled = False
            self._rotation = world.player.get_transform().rotation
        else:
            raise NotImplementedError("Actor type not supported")
        self._steer_cache = 0.0
        world.hud.notification("Press 'H' or '?' for help.", seconds=4.0)

        # initialize steering wheel
        pygame.joystick.init()

        joystick_count = pygame.joystick.get_count()
        if joystick_count > 1:
            raise ValueError("Please Connect Just One Joystick")

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()

        self._parser = ConfigParser()
        self._parser.read('src/driving/wheel_config.ini')
        self._steer_idx = int(
            self._parser.get('G29 Racing Wheel', 'steering_wheel'))
        self._throttle_idx = int(
            self._parser.get('G29 Racing Wheel', 'throttle'))
        self._brake_idx = int(self._parser.get('G29 Racing Wheel', 'brake'))
        self._reverse_idx = int(self._parser.get('G29 Racing Wheel', 'reverse'))
        self._handbrake_idx = int(
            self._parser.get('G29 Racing Wheel', 'handbrake'))

    def parse_events(self, world, _):
        """
        Parse events from the steering wheel and apply controls.

        Args:
            world (World): The World object.
            _ (pygame.time.Clock): Unused argument.

        Returns:
            bool: True if quit event is detected, False otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    world.restart()
                elif event.button == 1:
                    world.hud.toggle_info()
                elif event.button == 2:
                    world.camera_manager.toggle_camera()
                elif event.button == 3:
                    world.next_weather()
                elif event.button == self._reverse_idx:
                    self._control.gear = 1 if self._control.reverse else -1
                elif event.button == 23:
                    world.camera_manager.next_sensor()

        if not self._autopilot_enabled:
            if isinstance(self._control, carla.VehicleControl):
                self._parse_vehicle_wheel()
                self._control.reverse = self._control.gear < 0
            world.player.apply_control(self._control)

    def _parse_vehicle_wheel(self):
        """Parse inputs from the steering wheel and pedals."""
        numAxes = self._joystick.get_numaxes()
        jsInputs = [float(self._joystick.get_axis(i)) for i in range(numAxes)]
        # print (jsInputs)
        jsButtons = [float(self._joystick.get_button(i)) for i in
                     range(self._joystick.get_numbuttons())]

        # Custom function to map range of inputs [1, -1] to outputs [0, 1]
        # For the steering, it seems fine as it is
        K1 = 1.0  # 0.55
        steerCmd = K1 * math.tan(1.1 * jsInputs[self._steer_idx])

        K2 = 1.6  # 1.6
        throttleCmd = K2 + (2.05 * math.log10(
            -0.7 * jsInputs[self._throttle_idx] + 1.4) - 1.2) / 0.92
        if throttleCmd <= 0:
            throttleCmd = 0
        elif throttleCmd > 1:
            throttleCmd = 1

        brakeCmd = 1.6 + (2.05 * math.log10(
            -0.7 * jsInputs[self._brake_idx] + 1.4) - 1.2) / 0.92
        if brakeCmd <= 0:
            brakeCmd = 0
        elif brakeCmd > 1:
            brakeCmd = 1

        self._control.steer = steerCmd
        self._control.brake = brakeCmd
        self._control.throttle = throttleCmd

        #toggle = jsButtons[self._reverse_idx]

        self._control.hand_brake = bool(jsButtons[self._handbrake_idx])


class HUD:
    """Heads-up display for the driver vehicle."""

    def __init__(self, width, height, name, zephyr_conn):
        """
        Initialize the HUD.

        Args:
            width (int): Width of the display.
            height (int): Height of the display.
            name (str): Unique name for log files.
            zephyr_conn (multiprocessing.connection.Connection): Pipe for biometrics data stream.
        """
        self.dim = (width, height)
        self.zephyr_conn = zephyr_conn
        font = pygame.font.Font(pygame.font.get_default_font(), 20)
        font_name = 'courier' if os.name == 'nt' else 'mono'
        fonts = [x for x in pygame.font.get_fonts() if font_name in x]
        default_font = 'ubuntumono'
        mono = default_font if default_font in fonts else fonts[0]
        mono = pygame.font.match_font(mono)
        self._font_mono = pygame.font.Font(mono, 12 if os.name == 'nt' else 14)
        self._notifications = FadingText(font, (width, 40), (0, height - 40))
        self.help = HelpText(pygame.font.Font(mono, 24), width, height)
        self.server_fps = 0
        self.frame = 0
        self.simulation_time = 0
        self._show_info = True
        self._info_text = []
        self._server_clock = pygame.time.Clock()

        # biometrics data
        self.heart_rate = 0.0
        self.breathing_rate = 0.0
        self.hr_log = collections.deque([0], 200)
        self.br_log = collections.deque([0], 200)
        self.valid_data = False

        # log files
        self.speed_log = f'src/logs/data_log_{name}_{datetime.datetime.now().strftime("%m-%d_%H%M")}.csv'
        self.collisions_log = f'src/logs/collisions_{name}_{datetime.datetime.now().strftime("%m-%d_%H%M")}.txt'
        with open(self.speed_log, 'w', encoding='utf-8') as f:
            f.write('time_seconds,time,speed,throttle,brake,steer,heart_rate,breathing_rate\n')
        # with open(self.collisions_log, 'w', encoding='utf-8') as f:
        #     f.write('time_seconds,time,collision\n')

    def on_world_tick(self, timestamp):
        """
        Update server clock and simulation time.

        Args:
            timestamp (carla.Timestamp): Simulation timestamp.
        """
        self._server_clock.tick()
        self.server_fps = self._server_clock.get_fps()
        self.frame = timestamp.frame
        self.simulation_time = timestamp.elapsed_seconds

    def tick(self, world, clock):
        """
        Update HUD information every tick.

        Args:
            world (World): The World object.
            clock (pygame.time.Clock): Pygame clock to control the frame rate.
        """
        self._notifications.tick(world, clock)
        if not self._show_info:
            return
        timestamp = datetime.timedelta(seconds=int(self.simulation_time))
        t = world.player.get_transform()
        v = world.player.get_velocity()
        c = world.player.get_control()
        speed = 3.6 * math.sqrt(v.x**2 + v.y**2 + v.z**2)
        heading = 'N' if abs(t.rotation.yaw) < 89.5 else ''
        heading += 'S' if abs(t.rotation.yaw) > 90.5 else ''
        heading += 'E' if 179.5 > t.rotation.yaw > 0.5 else ''
        heading += 'W' if -0.5 > t.rotation.yaw > -179.5 else ''
        colhist = world.collision_sensor.get_collision_history()
        collision = [colhist[x + self.frame - 200] for x in range(0, 200)]
        max_col = max(1.0, max(collision))
        collision = [x / max_col for x in collision]
        vehicles = world.world.get_actors().filter('vehicle.*')
        self._info_text = [
            'Server:  % 16.0f FPS' % self.server_fps,
            'Client:  % 16.0f FPS' % clock.get_fps(),
            '',
            'Vehicle: % 20s' % get_actor_display_name(world.player, truncate=20),
            'Map:     % 20s' % world.world.get_map().name.split('/')[-1],
            'Simulation time: % 12s' % timestamp,
            '',
            'Speed:   % 15.0f km/h' % speed,
            u'Heading:% 16.0f\N{DEGREE SIGN} % 2s' % (t.rotation.yaw, heading),
            'Location:% 20s' % ('(% 5.1f, % 5.1f)' % (t.location.x, t.location.y)),
            'GNSS:% 24s' % ('(% 2.6f, % 3.6f)' % (world.gnss_sensor.lat, world.gnss_sensor.lon)),
            'Height:  % 18.0f m' % t.location.z,
            '']
        if isinstance(c, carla.VehicleControl):
            self._info_text += [
                ('Throttle:', c.throttle, 0.0, 1.0),
                ('Steer:', c.steer, -1.0, 1.0),
                ('Brake:', c.brake, 0.0, 1.0),
                ('Reverse:', c.reverse),
                ('Hand brake:', c.hand_brake),
                ('Manual:', c.manual_gear_shift),
                'Gear:        %s' % {-1: 'R', 0: 'N'}.get(c.gear, c.gear)]
        elif isinstance(c, carla.WalkerControl):
            self._info_text += [
                ('Speed:', c.speed, 0.0, 5.556),
                ('Jump:', c.jump)]
        self._info_text += [
            '',
            'Collision:',
            collision,
            '',
            'Number of vehicles: % 8d' % len(vehicles)]

        # receive biometrics data
        if self.zephyr_conn.poll():
            biometrics = self.zephyr_conn.recv()
            self.heart_rate = biometrics[0]
            self.breathing_rate = biometrics[1]

        # check if biometrics data is valid
        try:
            heart_rate = float(self.heart_rate)
            breathing_rate = float(self.breathing_rate)
            self.valid_data = True
        except (TypeError, ValueError):
            logging.error('Invalid data received from Zephyr: %s', str(biometrics))
            self.valid_data = False

        if self.valid_data:
            self.hr_log.append(heart_rate)
            hr_plot = list(self.hr_log)
            hr_plot = [x / 150 for x in hr_plot]

            self.br_log.append(breathing_rate)
            br_plot = list(self.br_log)
            br_plot = [x / 35 for x in br_plot]

            self._info_text += [
                '',
                'Heart Rate: % 16.1f' % heart_rate,
                hr_plot,
                '',
                'Breathing Rate: % 12.1f' % breathing_rate,
                br_plot,
            ]
        else:
            self._info_text += [
                '',
                'Heart Rate: % 16s' % self.heart_rate,
                'Breathing Rate: % 12s' % self.breathing_rate,
            ]

        if len(vehicles) > 1:
            self._info_text += ['Nearby vehicles:']
            distance = lambda l: math.sqrt((l.x - t.location.x)**2 + (l.y - t.location.y)**2 + (l.z - t.location.z)**2)
            vehicles = [(distance(x.get_location()), x) for x in vehicles if x.id != world.player.id]
            for d, vehicle in sorted(vehicles):
                if d > 200.0:
                    break
                vehicle_type = get_actor_display_name(vehicle, truncate=22)
                self._info_text.append('% 4dm %s' % (d, vehicle_type))
                      
        with open(self.speed_log, 'a', encoding='utf-8') as speed_f:
            speed_f.write(f'{timestamp.seconds},{timestamp},{speed:.2f},{c.throttle:.2f},{c.brake:.2f},{c.steer:.2f},{self.heart_rate},{self.breathing_rate}\n')

        # with open(self.collisions_log, 'a', encoding='utf-8') as coll_f:
        #     coll_f.write(f'{timestamp.seconds},{timestamp},{collision}\n')

    def toggle_info(self):
        """Toggle the display of HUD information."""
        self._show_info = not self._show_info

    def notification(self, text, seconds=2.0):
        """
        Display a notification on the HUD.

        Args:
            text (str): The text of the notification.
            seconds (float, optional): Duration to display the notification. Defaults to 2.0 seconds.
        """
        self._notifications.set_text(text, seconds=seconds)

    def error(self, text):
        """
        Display an error message on the HUD.

        Args:
            text (str): The text of the error message.
        """
        self._notifications.set_text('Error: %s' % text, (255, 0, 0))

    def render(self, display):
        """
        Render the HUD on the display.

        Args:
            display (pygame.Surface): Pygame display surface.
        """
        if self._show_info:
            info_surface = pygame.Surface((220, self.dim[1]))
            info_surface.set_alpha(100)
            display.blit(info_surface, (0, 0))
            v_offset = 4
            bar_h_offset = 100
            bar_width = 106
            for item in self._info_text:
                if v_offset + 18 > self.dim[1]:
                    break
                if isinstance(item, list):
                    if len(item) > 1:
                        points = [(x + 8, v_offset + 8 + (1.0 - y) * 30) for x, y in enumerate(item)]
                        pygame.draw.lines(display, (255, 136, 0), False, points, 2)
                    item = None
                    v_offset += 18
                elif isinstance(item, tuple):
                    if isinstance(item[1], bool):
                        rect = pygame.Rect((bar_h_offset, v_offset + 8), (6, 6))
                        pygame.draw.rect(display, (255, 255, 255), rect, 0 if item[1] else 1)
                    else:
                        rect_border = pygame.Rect((bar_h_offset, v_offset + 8), (bar_width, 6))
                        pygame.draw.rect(display, (255, 255, 255), rect_border, 1)
                        f = (item[1] - item[2]) / (item[3] - item[2])
                        if item[2] < 0.0:
                            rect = pygame.Rect((bar_h_offset + f * (bar_width - 6), v_offset + 8), (6, 6))
                        else:
                            rect = pygame.Rect((bar_h_offset, v_offset + 8), (f * bar_width, 6))
                        pygame.draw.rect(display, (255, 255, 255), rect)
                    item = item[0]
                if item:  # At this point has to be a str.
                    surface = self._font_mono.render(item, True, (255, 255, 255))
                    display.blit(surface, (8, v_offset))
                v_offset += 18
        self._notifications.render(display)
        self.help.render(display)


class FadingText(object):
    """Display text that fades over time."""

    def __init__(self, font, dim, pos):
        """
        Initialize the FadingText class.

        Args:
            font (pygame.font.Font): Pygame font object.
            dim (tuple): Dimensions of the text surface.
            pos (tuple): Position of the text surface.
        """
        self.font = font
        self.dim = dim
        self.pos = pos
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)

    def set_text(self, text, color=(255, 255, 255), seconds=2.0):
        """
        Set the text to display.

        Args:
            text (str): The text to display.
            color (tuple, optional): Color of the text. Defaults to white.
            seconds (float, optional): Duration to display the text. Defaults to 2.0 seconds.
        """
        text_texture = self.font.render(text, True, color)
        self.surface = pygame.Surface(self.dim)
        self.seconds_left = seconds
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(text_texture, (10, 11))

    def tick(self, _, clock):
        """
        Update the remaining time for the text to be displayed.

        Args:
            _ (any): Placeholder argument.
            clock (pygame.time.Clock): Pygame clock to control the frame rate.
        """
        delta_seconds = 1e-3 * clock.get_time()
        self.seconds_left = max(0.0, self.seconds_left - delta_seconds)
        self.surface.set_alpha(500.0 * self.seconds_left)

    def render(self, display):
        """
        Render the fading text on the display.

        Args:
            display (pygame.Surface): Pygame display surface.
        """
        display.blit(self.surface, self.pos)


class HelpText(object):
    """Display help text on the screen."""

    def __init__(self, font, width, height):
        """
        Initialize the HelpText class.

        Args:
            font (pygame.font.Font): Pygame font object.
            width (int): Width of the display.
            height (int): Height of the display.
        """
        lines = __doc__.split('\n')
        self.font = font
        self.dim = (680, len(lines) * 22 + 12)
        self.pos = (0.5 * width - 0.5 * self.dim[0], 0.5 * height - 0.5 * self.dim[1])
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)
        self.surface.fill((0, 0, 0, 0))
        for n, line in enumerate(lines):
            text_texture = self.font.render(line, True, (255, 255, 255))
            self.surface.blit(text_texture, (22, n * 22))
            self._render = False
        self.surface.set_alpha(220)

    def toggle(self):
        """Toggle the display of help text."""
        self._render = not self._render

    def render(self, display):
        """
        Render the help text on the display.

        Args:
            display (pygame.Surface): Pygame display surface.
        """
        if self._render:
            display.blit(self.surface, self.pos)


class CameraManager(object):
    """Manages camera sensors attached to the vehicle."""

    def __init__(self, parent_actor, hud):
        """
        Initialize the CameraManager class.

        Args:
            parent_actor (carla.Actor): The actor to attach the camera to.
            hud (HUD): The HUD object for displaying information.
        """
        self.sensor = None
        self.surface = None
        self._parent = parent_actor
        self.hud = hud
        self.recording = False
        self._camera_transforms = [
            carla.Transform(carla.Location(x=-5.5, z=2.8), carla.Rotation(pitch=-15)),
            carla.Transform(carla.Location(x=1.6, z=1.7)),
            carla.Transform(carla.Location(x=1.6, z=1.7), carla.Rotation(yaw=-45)),
            carla.Transform(carla.Location(x=1.6, z=1.7), carla.Rotation(yaw=45)),
            ]
        self.transform_index = 1
        self.sensors = [
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB'],
            ['sensor.camera.depth', cc.Raw, 'Camera Depth (Raw)'],
            ['sensor.camera.depth', cc.Depth, 'Camera Depth (Gray Scale)'],
            ['sensor.camera.depth', cc.LogarithmicDepth, 'Camera Depth (Logarithmic Gray Scale)'],
            ['sensor.camera.semantic_segmentation', cc.Raw, 'Camera Semantic Segmentation (Raw)'],
            ['sensor.camera.semantic_segmentation', cc.CityScapesPalette,
                'Camera Semantic Segmentation (CityScapes Palette)'],
            ['sensor.lidar.ray_cast', None, 'Lidar (Ray-Cast)']]
        world = self._parent.get_world()
        bp_library = world.get_blueprint_library()
        for item in self.sensors:
            bp = bp_library.find(item[0])
            if item[0].startswith('sensor.camera'):
                bp.set_attribute('image_size_x', str(hud.dim[0]))
                bp.set_attribute('image_size_y', str(hud.dim[1]))
            elif item[0].startswith('sensor.lidar'):
                bp.set_attribute('range', '50')
            item.append(bp)
        self.index = None

    def toggle_camera(self):
        """Toggle the camera position."""
        self.transform_index = (self.transform_index + 1) % len(self._camera_transforms)
        self.sensor.set_transform(self._camera_transforms[self.transform_index])

    def set_sensor(self, index, notify=True):
        """
        Set the active sensor.

        Args:
            index (int): Index of the sensor to set.
            notify (bool, optional): Whether to display a notification. Defaults to True.
        """
        index = index % len(self.sensors)
        needs_respawn = True if self.index is None \
            else self.sensors[index][0] != self.sensors[self.index][0]
        if needs_respawn:
            if self.sensor is not None:
                self.sensor.destroy()
                self.surface = None
            self.sensor = self._parent.get_world().spawn_actor(
                self.sensors[index][-1],
                self._camera_transforms[self.transform_index],
                attach_to=self._parent)
            # We need to pass the lambda a weak reference to self to avoid
            # circular reference.
            weak_self = weakref.ref(self)
            self.sensor.listen(lambda image: CameraManager._parse_image(weak_self, image))
        if notify:
            self.hud.notification(self.sensors[index][2])
        self.index = index

    def next_sensor(self):
        """Switch to the next sensor."""
        self.set_sensor(self.index + 1)

    def toggle_recording(self):
        """Toggle recording of camera feed."""
        self.recording = not self.recording
        self.hud.notification('Recording %s' % ('On' if self.recording else 'Off'))

    def render(self, display):
        """
        Render the camera feed on the display.

        Args:
            display (pygame.Surface): Pygame display surface.
        """
        if self.surface is not None:
            display.blit(self.surface, (0, 0))

    @staticmethod
    def _parse_image(weak_self, image):
        """
        Parse the image from the camera.

        Args:
            weak_self (weakref.ref): Weak reference to the CameraManager instance.
            image (carla.Image): The image from the camera.
        """
        self = weak_self()
        if not self:
            return
        if self.sensors[self.index][0].startswith('sensor.lidar'):
            points = np.frombuffer(image.raw_data, dtype=np.dtype('f4'))
            points = np.reshape(points, (int(points.shape[0] / 4), 4))
            lidar_data = np.array(points[:, :2])
            lidar_data *= min(self.hud.dim) / 100.0
            lidar_data += (0.5 * self.hud.dim[0], 0.5 * self.hud.dim[1])
            lidar_data = np.fabs(lidar_data) # pylint: disable=E1111
            lidar_data = lidar_data.astype(np.int32)
            lidar_data = np.reshape(lidar_data, (-1, 2))
            lidar_img_size = (self.hud.dim[0], self.hud.dim[1], 3)
            lidar_img = np.zeros(lidar_img_size)
            lidar_img[tuple(lidar_data.T)] = (255, 255, 255)
            self.surface = pygame.surfarray.make_surface(lidar_img)
        else:
            image.convert(self.sensors[self.index][1])
            array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (image.height, image.width, 4))
            array = array[:, :, :3]
            array = array[:, :, ::-1]
            self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        if self.recording:
            image.save_to_disk('_out/%08d' % image.frame)


def game_loop(args, parent_conn, child_conn):
    """
    Main game loop.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
        parent_conn (multiprocessing.connection.Connection): Parent connection for biometrics data.
        child_conn (multiprocessing.connection.Connection): Child connection for biometrics data.
    """
    pygame.init()
    pygame.font.init()

    try:
        client = carla.Client('127.0.0.1', 2000)
        client.set_timeout(2.0)

        display = pygame.display.set_mode(
            (args.width, args.height),
            pygame.HWSURFACE | pygame.DOUBLEBUF)

        hud = HUD(args.width, args.height, args.name, parent_conn)
        world = World(client.get_world(), hud, args.vehicle)
        controller = SteeringControl(world, args.autopilot)

        clock = pygame.time.Clock()
        while True:
            clock.tick_busy_loop(60)
            if controller.parse_events(world, clock):
                return
            world.tick(clock)
            world.render(display)
            pygame.display.flip()

    finally:
        parent_conn.send(True)
        child_conn.close()
        parent_conn.close()
        if world is not None:
            world.destroy()

        pygame.quit()


def main():
    """Main function to set up and run the CARLA client and Zephyr stream."""
    if os.path.exists(args.name):
        if input('This will overwrite an existing log file. Proceed? [Y/n]: ') not in ('Y', 'y'):
            return
    parent_conn, child_conn = Pipe()
    p = Process(target=monitor_and_send_biometrics, args=(child_conn,))
    try:
        p.start()
        logging.info(str(parent_conn.recv()))
    except (AttributeError, TypeError, ValueError) as e:
        logging.error('Error initializing Zephyr stream: %s', e.args[0])
    except KeyboardInterrupt:
        logging.info('Cancelled by user. Bye!')
    else:
        try:
            game_loop(args, parent_conn, child_conn)
        except KeyboardInterrupt:
            logging.info('Cancelled by user. Bye!')
    finally:
        p.join()
        logging.info('Zephyr stream terminated.')


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='CARLA Manual Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: %(default)s)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: %(default)s)')
    argparser.add_argument(
        '--name',
        type=str,
        required=True,
        help='unique name for log files')
    argparser.add_argument(
        '-a', '--autopilot',
        action='store_true',
        help='enable autopilot')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        #default='4160x768',
        help='window resolution (default: %(default)s)')
    argparser.add_argument(
        '--vehicle',
        metavar='PATTERN',
        default='vehicle.dodge.charger_2020',
        help='actor vehicle (default: "%(default)s")')
    args = argparser.parse_args()
    args.width, args.height = [int(x) for x in args.res.split('x')]

    logging.basicConfig(
        format='CONTROL-%(levelname)s: %(message)s',
        level=logging.DEBUG if args.debug else logging.INFO
    )
    logging.info('listening to server %s:%s', args.host, args.port)

    print(__doc__)

    main()
