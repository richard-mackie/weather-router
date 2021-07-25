import heapq
import datetime
import mercantile
import numpy as np

from config import Config
import utils
from pyproj import Geod
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
import os
import xarray
import glob

# Used for geodesic calculations
globe = Geod(ellps='clrk66')  # Use Clarke 1866 ellipsoid.

# Directory References
netcdf_dir = './static/data/netcdf/'
grib_dir = './static/data/gribs/'
json_dir = './static/data/json/'
proj_dir = '/home/richard/PycharmProjects/mweatherrouter'


class Node:
    def __init__(self, lat, lng, time, parent, heading, distance_to_finish, distance_traveled):
        self.lat = lat
        self.lng = lng
        self.grid_location = mercantile.tile(self.lat, self.lng, zoom=20)
        self.time = time
        self.parent = parent
        self.heading = heading
        self.distance_traveled = distance_traveled
        self.distance_to_finish = distance_to_finish

def vmg(node, speed, finish_bearing, true_wind_angle):

    vmg = speed * np.cos(np.radians(true_wind_angle))
    #print('Heading: {} True Wind Angle: {} VMG: {} '.format(node.heading, true_wind_angle, vmg))

    return vmg

def astar_optimal_route(start, finish, max_steps=36):

    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(proj_dir)
    ds = xarray.open_dataset(netcdf_dir + all_netcdfs[0])

    start_node = Node(lat=start['lat'], lng=start['lng'], time=0, parent=None, heading=None, distance_to_finish=0, distance_traveled=0)
    finish_node = Node(lat=finish['lat'], lng=finish['lng'], time=0, parent=None, heading=None, distance_to_finish=0, distance_traveled=0)

    frontier = PriorityQueue()
    frontier.push((0, start_node))
    visited = {start_node.grid_location: None}
    cost_so_far = {start_node: 0}

    circles = []

    step = 0
    hours_of_travel = 1

    while not frontier.empty() and step < max_steps:
        current_node = frontier.pop()[-1]

        print('Current Node', current_node.heading)

        wind_speed = ds.sel(latitude=current_node.lat, longitude=current_node.lng, method='nearest')['speed'].values.item()
        wind_degree = ds.sel(latitude=current_node.lat, longitude=current_node.lng, method='nearest')['degree'].values.item()

        if current_node.grid_location == finish_node.grid_location:

            result = []
            current = current_node

            while current.parent != None:
                result.append((current.lat, current.lng))
                current = current.parent

            return circles

        for heading in [deg for deg in range(0, 361, 10)]:
            true_wind_angle = utils.calculate_true_wind_angle(heading, wind_degree)
            speed = max(utils.get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
            distance = speed * hours_of_travel
            vmg = speed * np.cos(np.radians(true_wind_angle))
            # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
            lng, lat, back_azimuth = globe.fwd(lons=current_node.lng, lats=current_node.lat, az=heading, dist=distance * 1852)
            azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)

            node = Node(lat=lat,
                        lng=lng,
                        time=hours_of_travel + current_node.time,
                        parent=current_node,
                        distance_traveled=current_node.distance_traveled + distance,
                        heading=heading,
                        distance_to_finish=dist_finish
                        )
            print('Heading: {} True Wind Angle: {} VMG: {} Distance{}'.format(node.heading, true_wind_angle, vmg,
                                                                              distance))

            if node.grid_location not in cost_so_far or node.time < cost_so_far[node.grid_location]:
                cost_so_far[node.grid_location] = node.time
                frontier.push((node.time, step, heading, node))
                visited[node] = current_node
                circles.append((node.lat, node.lng))

        step += 1

    return circles




