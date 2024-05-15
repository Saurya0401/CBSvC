#!/usr/bin/env python
# pylint: skip-file

"""
Generate various taffic scenarios
"""

import argparse
import logging
import glob
import os
import sys
import time
from enum import Enum, auto

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
from numpy import random

from src.scenarios.traffic import TrafficGenerator
from src.scenarios.weather import WeatherType, WeatherManager, TimeOfDay


class Scenario(Enum):
    default = auto()
    night = auto()
    overspeeding = auto()
    distracted = auto()
    congestion = auto()


def set_global_settings(world, traffic_manager):
    settings = world.get_settings()
    traffic_manager.set_synchronous_mode(True)
    if not settings.synchronous_mode:
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)


def main():

    scenario = Scenario[args.scenario]
    client = carla.Client(args.host, args.port)
    client.set_timeout(10.0)
    random.seed(args.seed if args.seed is not None else int(time.time()))

    vehicles_list = []
    walkers_list = []
    combined_walker_ids = []
    combined_walker_actors = []

    try:
        world = client.get_world()
        traffic_manager = client.get_trafficmanager(args.tm_port)
        set_global_settings(world, traffic_manager)

        # initialize vehicles and pedestrians
        traffic_gen = TrafficGenerator(client, world, traffic_manager, args)
        traffic_gen.set_global_tm_settings(en_auto_lane_change=scenario == Scenario.default)
        if scenario != Scenario.congestion and not args.congestion:
            traffic_gen.spawn_vehicles()
            if args.aggression:
                traffic_gen.set_aggressive_behavior_all(
                    en_ignore_light=True,
                    en_ignore_signs=True,
                    en_overspeed=True,
                    en_lane_change=True
                )
            elif scenario == Scenario.overspeeding:
                traffic_gen.set_aggressive_behavior_all(
                    en_ignore_light=False,
                    en_ignore_signs=False,
                    en_overspeed=True,
                    en_lane_change=True
                )
            elif scenario == Scenario.distracted:
                traffic_gen.set_aggressive_behavior_all(
                    en_ignore_light=True,
                    en_ignore_signs=True,
                    en_overspeed=False,
                    en_lane_change=False
                )
            if not args.disable_car_lights:
                traffic_gen.set_automatic_vehicle_lights()
        traffic_gen.spawn_walkers()
        logging.info(
            'Spawned %d vehicles and %d walkers, press Ctrl+C to exit.',
            len(traffic_gen.vehicles_list),
            len(traffic_gen.walkers_list)
        )

        # initialize weather
        weather_man = WeatherManager(world, world.get_actors(traffic_gen.vehicles_list))
        if scenario == Scenario.night:
            weather_man.set_weather(WeatherType.CLEAR)
            weather_man.set_time_of_day(TimeOfDay.NIGHT)
        else:
            weather_man.set_weather(WeatherType[args.weather.upper()])
            weather_man.set_time_of_day(TimeOfDay[args.time.upper()])
        weather_man.apply_settings()

        vehicles_list = traffic_gen.vehicles_list
        walkers_list = traffic_gen.walkers_list
        combined_walker_ids = traffic_gen.combined_walker_ids
        combined_walker_actors = traffic_gen.combined_walker_actors

        while True:
            world.tick()
            if scenario == Scenario.congestion or args.congestion:
                vehicle = traffic_gen.spawn_congestion_vehicle()
                if vehicle:
                    weather_man.set_car_lights(vehicle)

    finally:
        settings = world.get_settings()
        settings.synchronous_mode = False
        settings.no_rendering_mode = False
        settings.fixed_delta_seconds = None
        world.apply_settings(settings)

        logging.info('Destroying %d vehicles', len(vehicles_list))
        client.apply_batch([carla.command.DestroyActor(x) for x in vehicles_list])

        # stop walker controllers (list is [controller, actor, controller, actor ...])
        for i in range(0, len(combined_walker_ids), 2):
            combined_walker_actors[i].stop()

        logging.info('Destroying %d walkers', len(walkers_list))
        client.apply_batch([carla.command.DestroyActor(x) for x in combined_walker_ids])

        time.sleep(0.5)


if __name__ == '__main__':
    logging.basicConfig(format='SCENARIO-%(levelname)s: %(message)s', level=logging.INFO)
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument(
        'scenario',
        type=str,
        choices=[s.name for s in Scenario],
        help='Scenario name'
    )
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
        '-n', '--number-of-vehicles',
        metavar='N',
        default=30,
        type=int,
        help='Number of vehicles (default: %(default)s)')
    argparser.add_argument(
        '-w', '--number-of-walkers',
        metavar='W',
        default=10,
        type=int,
        help='Number of walkers (default: %(default)s)')
    argparser.add_argument(
        '--aggression',
        action='store_true',
        default=False,
        help='Enable aggressive driving')
    argparser.add_argument(
        '--congestion',
        action='store_true',
        default=False,
        help='Enable traffic congestion along fixed routes')
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
    argparser.add_argument(
        '--safe',
        action='store_true',
        help='Avoid spawning vehicles prone to accidents')
    argparser.add_argument(
        '--filterv',
        metavar='PATTERN',
        default='vehicle.*',
        help='Filter vehicle model (default: "vehicle.*")')
    argparser.add_argument(
        '--generationv',
        metavar='G',
        default='All',
        help='restrict to certain vehicle generation (values: "1","2","All" - default: "All")')
    argparser.add_argument(
        '--filterw',
        metavar='PATTERN',
        default='walker.pedestrian.*',
        help='Filter pedestrian type (default: "walker.pedestrian.*")')
    argparser.add_argument(
        '--generationw',
        metavar='G',
        default='2',
        help='restrict to certain pedestrian generation (values: "1","2","All" - default: "2")')
    argparser.add_argument(
        '--tm-port',
        metavar='P',
        default=8000,
        type=int,
        help='Port to communicate with TM (default: 8000)')
    argparser.add_argument(
        '-s', '--seed',
        metavar='S',
        type=int,
        help='Set random device seed and deterministic mode for Traffic Manager')
    argparser.add_argument(
        '--seedw',
        metavar='S',
        default=0,
        type=int,
        help='Set the seed for pedestrians module')
    argparser.add_argument(
        '--disable-car-lights',
        action='store_true',
        default=False,
        help='Disable automatic car light management')
    argparser.add_argument(
        '--hero',
        action='store_true',
        default=False,
        help='Set one of the vehicles as hero')

    args = argparser.parse_args()

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        logging.info('Done.')
