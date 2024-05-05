#!/usr/bin/env python

"""
Weather management classes
"""

import argparse
import glob
import os
import sys
import time
import logging
from enum import Enum, auto

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla


class TimeOfDay(Enum):
    NOON = auto()
    NIGHT = auto()


class WeatherType(Enum):
    CLEAR = auto()
    FOGGY = auto()
    RAINY = auto()


class WeatherManager:

    def __init__(self, world, vehicles_list=None):
        self.world = world
        if vehicles_list:
            self.vehicles = self.world.get_actors(vehicles_list)
        else:
            self.vehicles = []
        self.weather = self.world.get_weather()
        self.clear_weather = carla.WeatherParameters.ClearNoon
        self.rainy_weather = carla.WeatherParameters.HardRainNoon
        self.foggy_weather = carla.WeatherParameters(
            sun_azimuth_angle=self.clear_weather.sun_azimuth_angle,
            sun_altitude_angle=self.clear_weather.sun_altitude_angle,
            fog_density=40.0,
            fog_distance=1.0,
            fog_falloff=1.0,
        )
        self.current_weather = None
        self.weather_type = None
        self.time_of_day = None

    def set_car_lights(self, weather_type):
        """Set car lights for foggy and rainy weather"""
        if not self.vehicles:
            logging.warning("Cannot set car lights (no vehicle info)")
        for ve in self.vehicles:
            light_mask = ve.get_light_state()
            if weather_type == WeatherType.FOGGY:
                light_mask |= carla.VehicleLightState.Fog | carla.VehicleLightState.LowBeam
            elif weather_type == WeatherType.RAINY:
                light_mask |= carla.VehicleLightState.LowBeam
            ve.set_light_state(carla.VehicleLightState(light_mask))

    def apply_settings(self):
        self.set_car_lights(self.weather_type)
        self.world.set_weather(self.current_weather)
        logging.info(
            'Weather set to %s %s', self.weather_type.name.lower(), self.time_of_day.name.lower()
        )

    def set_weather(self, weather_type):
        self.weather_type = weather_type
        if self.weather_type == WeatherType.CLEAR:
            self.current_weather = self.clear_weather
        elif self.weather_type == WeatherType.FOGGY:
            self.current_weather = self.foggy_weather
        elif self.weather_type == WeatherType.RAINY:
            self.current_weather = self.rainy_weather
        else:
            raise ValueError(f'Invalid weather type "{str(weather_type)}"')

    def set_time_of_day(self, time_of_day):
        if self.current_weather is None:
            logging.error('Set weather before setting time of day')
            return
        self.time_of_day = time_of_day
        if self.time_of_day == TimeOfDay.NOON:
            self.current_weather.sun_altitude_angle = 90.0
        elif self.time_of_day == TimeOfDay.NIGHT:
            self.current_weather.sun_altitude_angle = -90.0
            # increasing density here because the fog seems less dense at night for some reason
            if self.weather_type == WeatherType.FOGGY:
                self.current_weather.fog_density += 20
        else:
            raise ValueError(f'Invalid time of day "{str(time_of_day)}"')


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    argparser = argparse.ArgumentParser(description=__doc__)
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
        '--weather',
        choices=['clear', 'foggy', 'rainy'],
        default='clear',
        help='Set weather type (default: %(default)s)')
    argparser.add_argument(
        '--time',
        choices=['noon', 'night'],
        default='noon',
        help='Set time of day (default: %(default)s)')
    args = argparser.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(10.0)

    try:
        try:
            world = client.get_world()
            weather_man = WeatherManager(world)
            weather_man.set_weather(WeatherType[args.weather.upper()])
            weather_man.set_time_of_day(TimeOfDay[args.time.upper()])
            weather_man.apply_settings()
            while True:
                world.tick()
        finally:
            settings = world.get_settings()
            settings.synchronous_mode = False
            settings.no_rendering_mode = False
            settings.fixed_delta_seconds = None
            world.apply_settings(settings)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        logging.info('Done.')
