#!/usr/bin/env python

"""
Traffic management classes
"""

import glob
import os
import sys
import logging

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
from numpy import random

class TrafficGenerator:
    """Helper class to generate traffic"""

    # we can play around with these values
    IGNORE_LIGHTS_PERCENT = 100.0
    IGNORE_SIGNS_PERCENT = 100.0
    SPEED_DIFF_PERCENT = -20.0

    def __init__(self, client, world, traffic_manager, args):
        self.client = client
        self.world = world
        self.traffic_manager = traffic_manager
        self.args = args
        self.vehicle_blueprints = self.get_actor_blueprints(self.args.filterv, self.args.generationv)
        if not self.vehicle_blueprints:
            raise ValueError('Couldn\'t find any vehicles with the specified filters')
        self.walker_blueprints = self.get_actor_blueprints(self.args.filterw, self.args.generationw)
        if not self.walker_blueprints:
            raise ValueError('Couldn\'t find any walkers with the specified filters')

        self.n_vehicles = self.args.number_of_vehicles
        self.n_walkers = self.args.number_of_walkers
        self.spawn_actor = carla.command.SpawnActor
        self.spawn_points = self.world.get_map().get_spawn_points()

        # Congestion variables
        self.route_1_indices = [129, 28, 124, 33, 97, 119, 58, 154, 147]
        self.route_2_indices = [21, 76, 38, 34, 90, 3]
        self.route_1 = [self.spawn_points[i].location for i in self.route_1_indices]
        self.route_2 = [self.spawn_points[i].location for i in self.route_2_indices]
        self.alt = False
        self.spawn_delay = 20
        self.counter = self.spawn_delay

        self.vehicles_list = []

        self.walkers_list = []
        self.combined_walker_ids = []
        self.combined_walker_actors = []

    def get_actor_blueprints(self, filter, generation):
        bps = self.world.get_blueprint_library().filter(filter)

        if generation.lower() == "all":
            return bps

        # If the filter returns only one bp, we assume that this one needed
        # and therefore, we ignore the generation
        if len(bps) == 1:
            return bps

        try:
            int_generation = int(generation)
            # Check if generation is in available generations
            if int_generation in [1, 2, 3]:
                bps = [x for x in bps if int(x.get_attribute('generation')) == int_generation]
                return bps
            logging.warning("Warning! Actor Generation is not valid. No actor will be spawned.")
            return []
        except:
            logging.warning("Warning! Actor Generation is not valid. No actor will be spawned.")
            return []

    def set_global_tm_settings(self, en_auto_lane_change):
        # global traffic manager settings
        self.traffic_manager.set_global_distance_to_leading_vehicle(2.5)
        if self.args.seed is not None:
            self.traffic_manager.set_random_device_seed(self.args.seed)
        if en_auto_lane_change:
            for vehicle_actor in self.world.get_actors(self.vehicles_list):
                self.traffic_manager.auto_lane_change(vehicle_actor, False)
                logging.info('Auto lane change turned off for vehicle "%s"', self.get_vehicle_desc(vehicle_actor))

    def spawn_congestion_vehicle(self):
        n_congestion_vehicles = len(self.world.get_actors().filter('*vehicle*'))
        if self.counter == 0 and n_congestion_vehicles < 200:
            spawn_point = self.spawn_points[32] if self.alt else self.spawn_points[149]
            vehicle = self.world.try_spawn_actor(random.choice(self.vehicle_blueprints), spawn_point)
            if vehicle:
                vehicle.set_autopilot(True)
                self.traffic_manager.auto_lane_change(vehicle, True)
                if self.args.aggression:
                    self.set_aggressive_behavior(vehicle, True, True, True, True)
                if not self.args.disable_car_lights:
                    self.traffic_manager.update_vehicle_lights(vehicle, True)
                path = self.route_1 if self.alt else self.route_2
                self.traffic_manager.set_path(vehicle, path)
                self.alt = not self.alt
                self.vehicles_list.append(vehicle.id)
                logging.info('Spawned congestion vehicle (current: %d vehicles)', n_congestion_vehicles)
                return vehicle
            self.counter = self.spawn_delay
        else:
            self.counter -= 1 if self.counter > 0 else 0
        return None

    def spawn_vehicles(self):
        if self.args.safe:
            # spawns only cars cus apparently those are less prone to accidents
            self.vehicle_blueprints = [x for x in self.vehicle_blueprints if x.get_attribute('base_type') == 'car']

        self.vehicle_blueprints = sorted(self.vehicle_blueprints, key=lambda bp: bp.id)
        n_spawn_points = len(self.spawn_points)
        if self.n_vehicles < n_spawn_points:
            random.shuffle(self.spawn_points)
        elif self.n_vehicles > n_spawn_points:
            msg = 'requested %d vehicles, but could only find %d spawn points'
            logging.warning(msg, self.n_vehicles, n_spawn_points)
            self.n_vehicles = n_spawn_points

        batch = []
        hero = self.args.hero
        for n, transform in enumerate(self.spawn_points):
            if n >= self.args.number_of_vehicles:
                break
            blueprint = random.choice(self.vehicle_blueprints)
            if blueprint.has_attribute('color'):
                color = random.choice(blueprint.get_attribute('color').recommended_values)
                blueprint.set_attribute('color', color)
            if blueprint.has_attribute('driver_id'):
                driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
                blueprint.set_attribute('driver_id', driver_id)
            if hero:
                blueprint.set_attribute('role_name', 'hero')
                hero = False
            else:
                blueprint.set_attribute('role_name', 'autopilot')

            # spawn the cars and set their autopilot and light state all together
            SetAutopilot = carla.command.SetAutopilot
            FutureActor = carla.command.FutureActor
            batch.append(self.spawn_actor(blueprint, transform)
                .then(SetAutopilot(FutureActor, True, self.traffic_manager.get_port())))

        for response in self.client.apply_batch_sync(batch, True):
            if response.error:
                logging.error(response.error)
            else:
                self.vehicles_list.append(response.actor_id)

        logging.info('Spawned %d vehicles', len(self.vehicles_list))

    def set_aggressive_behavior(self, vehicle_actor, en_lane_change, en_ignore_light, en_ignore_signs, en_overspeed):
        # lead_dist = 0.5 + random.random_sample() # random value between 0.5 and 1.5
        # self.traffic_manager.distance_to_leading_vehicle(vehicle_actor, lead_dist)
        # logging.info('Vehicle "%s" distance to lead vehicle set to %.2f m',
        #              self.get_vehicle_desc(vehicle_actor), lead_dist)
        lane_change, ignore_light, ignore_signs, overspeed = [self.coin_toss() for _ in range(4)]
        if en_lane_change and lane_change:
            self.traffic_manager.force_lane_change(vehicle_actor, self.coin_toss())
            logging.info('Vehicle "%s" has force lane change behavior', self.get_vehicle_desc(vehicle_actor))
        if en_ignore_light and ignore_light:
            self.traffic_manager.ignore_lights_percentage(vehicle_actor, TrafficGenerator.IGNORE_LIGHTS_PERCENT)
            logging.info('Vehicle "%s" has a %.1f percent chance of ignoring traffic lights',
                         self.get_vehicle_desc(vehicle_actor), TrafficGenerator.IGNORE_LIGHTS_PERCENT)
        if en_ignore_signs and ignore_signs:
            self.traffic_manager.ignore_signs_percentage(vehicle_actor, TrafficGenerator.IGNORE_SIGNS_PERCENT)
            logging.info('Vehicle "%s" has a %.1f percent chance of ignoring traffic signs',
                         self.get_vehicle_desc(vehicle_actor), TrafficGenerator.IGNORE_SIGNS_PERCENT)
        if en_overspeed and overspeed:
            self.traffic_manager.vehicle_percentage_speed_difference(vehicle_actor, TrafficGenerator.SPEED_DIFF_PERCENT)
            logging.info('Vehicle "%s" will drive %.1f percent faster than the speed limit',
                         self.get_vehicle_desc(vehicle_actor), -1*TrafficGenerator.SPEED_DIFF_PERCENT)

    def set_aggressive_behavior_all(self, en_lane_change, en_ignore_light, en_ignore_signs, en_overspeed):
        all_vehicle_actors = self.world.get_actors(self.vehicles_list)
        for vehicle_actor in all_vehicle_actors:
            self.set_aggressive_behavior(vehicle_actor, en_lane_change, en_ignore_light, en_ignore_signs, en_overspeed)

    def set_automatic_vehicle_lights(self):
        """Set automatic vehicle lights update if specified"""
        
        all_vehicle_actors = self.world.get_actors(self.vehicles_list)
        for actor in all_vehicle_actors:
            self.traffic_manager.update_vehicle_lights(actor, True)
        logging.info('Car lights will be automatically managed by Traffic Manager')

    def spawn_walkers(self):
        # some settings
        percentagePedestriansRunning = 0.0      # how many pedestrians will run
        percentagePedestriansCrossing = 0.0     # how many pedestrians will walk through the road
        if self.args.seedw:
            self.world.set_pedestrians_seed(self.args.seedw)
            random.seed(self.args.seedw)

        # 1. take all the random locations to spawn
        w_spawn_points = []
        for _ in range(self.n_walkers):
            spawn_point = carla.Transform()
            loc = self.world.get_random_location_from_navigation()
            if loc is not None:
                spawn_point.location = loc
                w_spawn_points.append(spawn_point)

        # 2. we spawn the walker object
        batch = []
        walker_speed = []
        for spawn_point in w_spawn_points:
            walker_bp = random.choice(self.walker_blueprints)
            # set as not invincible
            if walker_bp.has_attribute('is_invincible'):
                walker_bp.set_attribute('is_invincible', 'false')
            # set the max speed
            if walker_bp.has_attribute('speed'):
                if (random.random() > percentagePedestriansRunning):
                    # walking
                    walker_speed.append(walker_bp.get_attribute('speed').recommended_values[1])
                else:
                    # running
                    walker_speed.append(walker_bp.get_attribute('speed').recommended_values[2])
            else:
                logging.warning('Walker has no speed')
                walker_speed.append(0.0)
            batch.append(self.spawn_actor(walker_bp, spawn_point))
        results = self.client.apply_batch_sync(batch, True)
        walker_speed2 = []
        for i in range(len(results)):
            if results[i].error:
                logging.error(results[i].error)
            else:
                self.walkers_list.append({'id': results[i].actor_id})
                walker_speed2.append(walker_speed[i])
        walker_speed = walker_speed2

        # 3. we spawn the walker controller
        batch = []
        walker_controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
        for i in range(len(self.walkers_list)):
            batch.append(self.spawn_actor(walker_controller_bp, carla.Transform(), self.walkers_list[i]['id']))
        results = self.client.apply_batch_sync(batch, True)
        for i in range(len(results)):
            if results[i].error:
                logging.error(results[i].error)
            else:
                self.walkers_list[i]['con'] = results[i].actor_id

        # 4. we put together the walkers and controllers id to get the objects from their id
        for i in range(len(self.walkers_list)):
            self.combined_walker_ids.append(self.walkers_list[i]['con'])
            self.combined_walker_ids.append(self.walkers_list[i]['id'])
        self.combined_walker_actors = self.world.get_actors(self.combined_walker_ids)
        # wait for a tick to ensure client receives the last transform of the walkers we have just created
        self.world.tick()

        # 5. initialize each controller and set target to walk to (list is [controler, actor, controller, actor ...])
        # set how many pedestrians can cross the road
        self.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
        for i in range(0, len(self.combined_walker_ids), 2):
            # start walker
            self.combined_walker_actors[i].start()
            # set walk to random point
            self.combined_walker_actors[i].go_to_location(self.world.get_random_location_from_navigation())
            # max speed
            self.combined_walker_actors[i].set_max_speed(float(walker_speed[int(i/2)]))

        logging.info('Spawned %d walkers', len(self.walkers_list))

    @staticmethod
    def get_vehicle_desc(vehicle_actor):
        _, company, model = vehicle_actor.type_id.split('.')
        return f'{company} {model} (id: {vehicle_actor.id})'

    @staticmethod
    def coin_toss():
        return random.random_sample() < 0.5
