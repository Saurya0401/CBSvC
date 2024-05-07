import carla
import random

# Connect to the CARLA client and retrieve the world object
client = carla.Client('localhost', 2000)
world = client.get_world()

# Set up the simulator in synchronous mode
settings = world.get_settings()
settings.synchronous_mode = True
settings.fixed_delta_seconds = 0.05
world.apply_settings(settings)

# Set up the Traffic Manager in synchronous mode
traffic_manager = client.get_trafficmanager()
traffic_manager.set_synchronous_mode(True)
traffic_manager.set_random_device_seed(0)
random.seed(0)

# Set up the spectator view
spectator = world.get_spectator()

# Retrieve spawn points from the map
spawn_points = world.get_map().get_spawn_points()

# Draw spawn point locations on the map for visualization
for i, spawn_point in enumerate(spawn_points):
    world.debug.draw_string(spawn_point.location, str(i), life_time=10)

# Spawn vehicles at random spawn points
models = ['dodge', 'audi', 'model3', 'mini', 'mustang', 'lincoln', 'prius', 'nissan', 'crown', 'impala']
blueprints = [bp for bp in world.get_blueprint_library().filter('*vehicle*') if any(model in bp.id for model in models)]
max_vehicles = min(50, len(spawn_points))
vehicles = []

for i, spawn_point in enumerate(random.sample(spawn_points, max_vehicles)):
    vehicle = world.try_spawn_actor(random.choice(blueprints), spawn_point)
    if vehicle:
        vehicles.append(vehicle)

# Control vehicles with Traffic Manager
for vehicle in vehicles:
    vehicle.set_autopilot(True)
    traffic_manager.ignore_lights_percentage(vehicle, random.randint(0, 50))

# Define routes for traffic congestion
# Example routes created using indices from previously visualized spawn points
route_1_indices = [129, 28, 124, 33, 97, 119, 58, 154, 147]
route_1 = [spawn_points[ind].location for ind in route_1_indices]

route_2_indices = [21, 76, 38, 34, 90, 3]
route_2 = [spawn_points[ind].location for ind in route_2_indices]

# Spawn vehicles and set paths for congestion simulation
spawn_delay = 20
counter = spawn_delay
max_vehicles = 200
alt = False

while True:
    world.tick()

    if counter == spawn_delay and len(world.get_actors().filter('*vehicle*')) < max_vehicles:
        spawn_point = spawn_point_1 if alt else spawn_point_2
        vehicle = world.try_spawn_actor(random.choice(blueprints), spawn_point)
        if vehicle:
            vehicle.set_autopilot(True)
            traffic_manager.update_vehicle_lights(vehicle, True)
            traffic_manager.random_left_lanechange_percentage(vehicle, 0)
            traffic_manager.random_right_lanechange_percentage(vehicle, 0)
            traffic_manager.auto_lane_change(vehicle, False)
            traffic_manager.set_path(vehicle, route_1 if alt else route_2)
            alt = not alt
            vehicle = None
        counter = spawn_delay
    else:
        counter -= 1
