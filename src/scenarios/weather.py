#!/usr/bin/env python

"""
This module defines a WeatherManager class for managing weather settings and vehicle light states
in a CARLA simulation environment. It also provides command-line functionality to set the weather
and time of day in the simulation.
"""

import argparse
import glob
import os
import sys
import logging
from enum import Enum, auto

try:
    # Dynamically append the path of the CARLA egg file to the system path
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla


class TimeOfDay(Enum):
    """Enumeration for different times of the day."""
    NOON = auto()
    NIGHT = auto()


class WeatherType(Enum):
    """Enumeration for different types of weather conditions."""
    CLEAR = auto()
    FOGGY = auto()
    RAINY = auto()
    CLOUDY = auto()


class WeatherManager:
    """
    Manages weather settings and vehicle lights in a CARLA simulation environment.
    
    Attributes:
        world (carla.World): The world instance where weather settings are applied.
        vehicles (list[carla.Vehicle]): Vehicles to manage lights for, defaults to empty list.
        clear_weather, cloudy_weather, rainy_weather, foggy_weather (carla.WeatherParameters):
            Presets for different weather conditions.
        current_weather (carla.WeatherParameters): Currently applied weather parameters.
        weather_type (WeatherType): Current type of weather being simulated.
        time_of_day (TimeOfDay): Current time of day in the simulation.
    """

    def __init__(self, world, vehicles=None):
        """
        Initializes the WeatherManager with a world instance and optional vehicle list.
        
        Parameters:
            world (carla.World): The world instance for weather management.
            vehicles (list[carla.Vehicle], optional): Vehicles to manage lights, defaults to None.
        """
        self.world = world
        self.vehicles = vehicles or []
        self.clear_weather = carla.WeatherParameters.ClearNoon
        self.cloudy_weather = carla.WeatherParameters.CloudyNoon
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

    def set_car_lights(self, vehicle):
        """
        Sets the lights of a vehicle based on the current weather conditions.
        
        Parameters:
            vehicle (carla.Vehicle): Vehicle to set lights for.
        """
        if not self.weather_type:
            logging.error("Cannot set vehicle lights (weather not set)")
            return
        light_mask = vehicle.get_light_state()
        if self.weather_type == WeatherType.FOGGY:
            light_mask |= carla.VehicleLightState.Fog | carla.VehicleLightState.LowBeam
        elif self.weather_type == WeatherType.RAINY:
            light_mask |= carla.VehicleLightState.LowBeam
        vehicle.set_light_state(carla.VehicleLightState(light_mask))

    def set_car_lights_all(self):
        """
        Sets lights for all vehicles based on the current weather conditions.
        """
        if not self.vehicles:
            logging.warning("Cannot set car lights (no vehicle info)")
        for ve in self.vehicles:
            self.set_car_lights(ve)

    def apply_settings(self):
        """
        Applies current weather and time settings to the world and updates vehicle lights.
        """
        self.set_car_lights_all()
        self.world.set_weather(self.current_weather)
        logging.info(
            'Weather set to %s %s', self.weather_type.name.lower(), self.time_of_day.name.lower()
        )

    def set_weather(self, weather_type):
        """
        Sets the weather condition based on a given weather type.
        
        Parameters:
            weather_type (WeatherType): Desired weather type to set.
        
        Raises:
            ValueError: If an invalid weather type is provided.
        """
        self.weather_type = weather_type
        if self.weather_type == WeatherType.CLEAR:
            self.current_weather = self.clear_weather
        elif self.weather_type == WeatherType.FOGGY:
            self.current_weather = self.foggy_weather
        elif self.weather_type == WeatherType.RAINY:
            self.current_weather = self.rainy_weather
        elif self.weather_type == WeatherType.CLOUDY:
            self.current_weather = self.cloudy_weather
        else:
            raise ValueError(f'Invalid weather type "{str(weather_type)}"')

    def set_time_of_day(self, time_of_day):
        """
        Sets the time of day in the simulation.
        
        Parameters:
            time_of_day (TimeOfDay): Desired time of day to set.
        
        Raises:
            ValueError: If an invalid time of day is provided.
        """
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


WEATHER_PRESETS = [
    ('clear noon', WeatherType.CLEAR, TimeOfDay.NOON),
    ('cloudy noon', WeatherType.CLOUDY, TimeOfDay.NOON),
    ('rainy noon', WeatherType.RAINY, TimeOfDay.NOON),
    ('foggy noon', WeatherType.FOGGY, TimeOfDay.NOON),
    ('clear night', WeatherType.CLEAR, TimeOfDay.NIGHT),
    ('cloudy night', WeatherType.CLOUDY, TimeOfDay.NIGHT),
    ('rainy night', WeatherType.RAINY, TimeOfDay.NIGHT),
    ('foggy night', WeatherType.FOGGY, TimeOfDay.NIGHT),
]


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
        choices=['clear', 'cloudy', 'foggy', 'rainy'],
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
    world = client.get_world()
    weather_man = WeatherManager(world)
    weather_man.set_weather(WeatherType[args.weather.upper()])
    weather_man.set_time_of_day(TimeOfDay[args.time.upper()])
    weather_man.apply_settings()

    world.wait_for_tick()
