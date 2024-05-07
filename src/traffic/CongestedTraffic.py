import carla
import random

def main():
    # Connect to the client and retrieve the world object
    client = carla.Client('localhost', 2000)
    world = client.get_world()

    # Set up the simulator in synchronous mode
    settings = world.get_settings()
    settings.synchronous_mode = True  # Enables synchronous mode
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    # Set up the Traffic Manager in synchronous mode
    traffic_manager = client.get_trafficmanager()
    traffic_manager.set_synchronous_mode(True)
    traffic_manager.set_random_device_seed(0)
    random.seed(0)

    # Set up the spectator
    spectator = world.get_spectator()

    # Retrieve spawn points
    spawn_points = world.get_map().get_spawn_points()

    # Draw spawn points on the map
    for i, spawn_point in enumerate(spawn_points):
        world.debug.draw_string(spawn_point.location, str(i), life_time=10)

    # Choose vehicle models
    models = ['dodge', 'audi', 'model3', 'mini', 'mustang', 'lincoln', 'prius', 'nissan', 'crown', 'impala']
    blueprints = [bp for bp in world.get_blueprint_library().filter('*vehicle*') if any(model in bp.id for model in models)]

    # Spawn vehicles
    max_vehicles = min(50, len(spawn_points))
    vehicles = [world.try_spawn_actor(random.choice(blueprints), point) for point in random.sample(spawn_points, max_vehicles) if world.try_spawn_actor(random.choice(blueprints), point)]

    # Give control to the Traffic Manager and set behavior parameters
    for vehicle in vehicles:
        vehicle.set_autopilot(True)
        traffic_manager.ignore_lights_percentage(vehicle, random.randint(0, 50))

    # Prepare routes
    route_1_indices = [129, 28, 124, 33, 97, 119, 58, 154, 147]
    route_2_indices = [21, 76, 38, 34, 90, 3]
    route_1 = [spawn_points[i].location for i in route_1_indices]
    route_2 = [spawn_points[i].location for i in route_2_indices]

    # Spawn traffic with defined routes
    alt = False
    spawn_delay = 20
    counter = spawn_delay
    while True:
        world.tick()
        if counter == 0 and len(world.get_actors().filter('*vehicle*')) < 200:
            spawn_point = spawn_points[32] if alt else spawn_points[149]
            vehicle = world.try_spawn_actor(random.choice(blueprints), spawn_point)
            if vehicle:
                vehicle.set_autopilot(True)
                traffic_manager.auto_lane_change(vehicle, False)
                path = route_1 if alt else route_2
                traffic_manager.set_path(vehicle, path)
                alt = not alt
            counter = spawn_delay
        else:
            counter -= 1 if counter > 0 else 0

if __name__ == '__main__':
    main()
