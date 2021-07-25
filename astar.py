import heapq
import time

import mercantile
import numpy as np
import utils
from config import Config
from utils import get_most_recent_netcdf, get_boat_speed, calculate_true_wind_angle

class PriorityQueue:
    '''
    Wrapper for heapq
    '''

    def __init__(self):
        self.heap = []

    def empty(self) -> bool:
        # try to get lowest cost
        try:
            x = self.heap[0]
            return False
        # if there is no lowest cost element the priority queue is empty
        except IndexError:
            return True

    def push(self, x):
        heapq.heappush(self.heap, x)

    def pop(self):
        return heapq.heappop(self.heap)

class Node:
    def __init__(self, lat, lng, time=0, parent=None, heading=0, distance_to_finish=0, distance_traveled=0):
        self.lat = lat
        self.lng = lng
        # This creates a semi unique identifier. Same as the index for slippy maps
        # https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
        self.grid_location = mercantile.tile(self.lat, self.lng, zoom=12)
        self.time = time
        self.parent = parent
        self.heading = heading
        self.distance_traveled = distance_traveled
        self.distance_to_finish = distance_to_finish

def vmg(node, speed, finish_bearing, true_wind_angle):
    '''
    Velocity Made Good. This is the speed that is actually going towards the destination.
    '''
    vmg = speed * np.cos(np.radians(true_wind_angle))
    return vmg

def astar_optimal_route(start, finish, timeout=10, max_steps=10000):
    # These are latlon tuples for display purposes only, they show the explored areas
    leaflet_points = []
    # This gives a way to end the search, nice for debugging
    step = 0
    hours_of_travel = 1
    # This holds the wind degree and speed
    wind_data = get_most_recent_netcdf()

    start_node = Node(lat=start['lat'], lng=start['lng'])
    finish_node = Node(lat=finish['lat'], lng=finish['lng'])

    frontier = PriorityQueue()
    frontier.push((0, start_node))
    visited = {start_node.grid_location: None}
    cost_so_far = {start_node: 0}
    start_time = time.time()

    while not frontier.empty() and step < max_steps:
        current_node = frontier.pop()[-1]
        wind_speed = wind_data.sel(latitude=current_node.lat,
                                   longitude=current_node.lng,
                                   method='nearest')['speed'].values.item()
        wind_degree = wind_data.sel(latitude=current_node.lat,
                                    longitude=current_node.lng,
                                    method='nearest')['degree'].values.item()

        if time.time() > start_time + timeout:
            print('No route found')
            return leaflet_points

        elif current_node.grid_location == finish_node.grid_location:
            # This is the optimal route
            route = []
            # Traverse the nodes and rebuild the path
            current = current_node
            while current.parent != None:
                route.append({'lat': current.lat, 'lng':current.lng})
                current = current.parent

            print('Optimal Path', utils.get_wind_speed_and_degree_for_routes(routes=[route]))
            return leaflet_points

        for heading in [deg for deg in range(0, 361, 1)]:
            true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
            speed = max(get_boat_speed(true_wind_angle, wind_speed), Config.motoring_speed)
            distance = speed * hours_of_travel
            # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
            lng, lat, back_azimuth = Config.globe.fwd(lons=current_node.lng,
                                                      lats=current_node.lat,
                                                      az=heading,
                                                      dist=distance * 1852)
            azimuth1, azimuth2, dist_finish = Config.globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)

            node = Node(lat=lat,
                        lng=lng,
                        time=hours_of_travel + current_node.time,
                        parent=current_node,
                        distance_traveled=current_node.distance_traveled + distance,
                        heading=heading,
                        distance_to_finish=dist_finish
                        )

            #print('Heading: {} True Wind Angle: {} VMG: {} Distance{}'.format(node.heading, true_wind_angle, vmg,
            #                                                                  distance))

            if node.grid_location not in cost_so_far or node.time < cost_so_far[node.grid_location]:
                cost_so_far[node.grid_location] = node.time
                # vmg = speed * np.cos(np.radians(true_wind_angle))
                #TODO come up with a better heuristic
                frontier.push(((node.time * 100000) - (node.distance_to_finish * 10) - (speed * 1000), step, heading, node))
                visited[node] = current_node
                leaflet_points.append((node.lat, node.lng))

        step += 1

    return leaflet_points




