"""
Various sensor classes for CARLA
"""

import collections
import glob
import math
import os
import sys
import weakref

try:
    # Dynamically append the path of the CARLA egg file to the system path
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla


class CollisionSensor:
    """Collision sensor for the vehicle."""

    def __init__(self, parent_actor, hud, actor_name_func):
        """
        Initialize the CollisionSensor class.

        Args:
            parent_actor (carla.Actor): The actor to attach the sensor to.
            hud (HUD): The HUD object for displaying information.
        """
        self.sensor = None
        self.history = []
        self._parent = parent_actor
        self.hud = hud
        self._actor_name_func = actor_name_func
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find('sensor.other.collision')
        self.sensor = world.spawn_actor(bp, carla.Transform(), attach_to=self._parent)
        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: CollisionSensor._on_collision(weak_self, event, actor_name_func))

    def get_collision_history(self):
        """
        Get the history of collisions.

        Returns:
            dict: A dictionary with the frame number as the key and collision intensity as the value.
        """
        history = collections.defaultdict(int)
        for frame, intensity in self.history:
            history[frame] += intensity
        return history

    @staticmethod
    def _on_collision(weak_self, event, actor_name_func):
        """
        Handle collision events.

        Args:
            weak_self (weakref.ref): Weak reference to the CollisionSensor instance.
            event (carla.CollisionEvent): The collision event.
        """
        self = weak_self()
        if not self:
            return
        actor_type = actor_name_func(event.other_actor)
        self.hud.notification('Collision with %r' % actor_type)
        impulse = event.normal_impulse
        intensity = math.sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)
        self.history.append((event.frame, intensity))
        if len(self.history) > 4000:
            self.history.pop(0)


class LaneInvasionSensor:
    """Lane invasion sensor for the vehicle."""

    def __init__(self, parent_actor, hud):
        self.sensor = None
        self._parent = parent_actor
        self.hud = hud
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find('sensor.other.lane_invasion')
        self.sensor = world.spawn_actor(bp, carla.Transform(), attach_to=self._parent)
        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: LaneInvasionSensor._on_invasion(weak_self, event))

    @staticmethod
    def _on_invasion(weak_self, event):
        """
        Handle lane invasion events.

        Args:
            weak_self (weakref.ref): Weak reference to the LaneInvasionSensor instance.
            event (carla.LaneInvasionEvent): The lane invasion event.
        """

        self = weak_self()
        if not self:
            return
        lane_types = set(x.type for x in event.crossed_lane_markings)
        text = ['%r' % str(x).split()[-1] for x in lane_types]
        self.hud.notification('Crossed line %s' % ' and '.join(text))


class GnssSensor:
    """GNSS sensor for the vehicle."""

    def __init__(self, parent_actor):
        """
        Initialize the GnssSensor class.

        Args:
            parent_actor (carla.Actor): The actor to attach the sensor to.
        """
        self.sensor = None
        self._parent = parent_actor
        self.lat = 0.0
        self.lon = 0.0
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find('sensor.other.gnss')
        self.sensor = world.spawn_actor(bp, carla.Transform(carla.Location(x=1.0, z=2.8)), attach_to=self._parent)
        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: GnssSensor._on_gnss_event(weak_self, event))

    @staticmethod
    def _on_gnss_event(weak_self, event):
        """
        Handle GNSS events.

        Args:
            weak_self (weakref.ref): Weak reference to the GnssSensor instance.
            event (carla.GnssEvent): The GNSS event.
        """
        self = weak_self()
        if not self:
            return
        self.lat = event.latitude
        self.lon = event.longitude
