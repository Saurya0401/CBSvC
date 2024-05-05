#!/usr/bin/env python

"""
Weather management classes
"""

import glob
import os
import sys
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


class WeatherType(Enum):
    CLEAR = auto()
    FOGGY = auto()
    RAINY = auto()


class WeatherManager:

    def __init__(self, world, vehicles_list):
        self.world = world
        self.vehicles = self.world.get_actors(vehicles_list)
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

    def set_car_lights(self, weather_type):
        """Set car lights for foggy and rainy weather"""
        for ve in self.vehicles:
            light_mask = ve.get_light_state()
            if weather_type == WeatherType.FOGGY:
                light_mask |= carla.VehicleLightState.Fog | carla.VehicleLightState.LowBeam
            elif weather_type == WeatherType.RAINY:
                light_mask |= carla.VehicleLightState.LowBeam
            ve.set_light_state(carla.VehicleLightState(light_mask))

    def set_weather(self, weather_type):
        if weather_type == WeatherType.CLEAR:
            self.set_car_lights(weather_type)
            self.world.set_weather(self.clear_weather)
            logging.info('Weather set to clear noon')
        elif weather_type == WeatherType.FOGGY:
            self.set_car_lights(weather_type)
            self.world.set_weather(self.foggy_weather)
            logging.info('Weather set to heavy fog noon')
        elif weather_type == WeatherType.RAINY:
            self.set_car_lights(weather_type)
            self.world.set_weather(self.rainy_weather)
            logging.info('Weather set to heavy rain noon')
        else:
            logging.error('Invalid weather type "%s"', weather_type.name)
