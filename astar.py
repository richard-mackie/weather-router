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
2
class Node:
    def __init__(self, lat, lng, time=0, parent=None, heading=0, distance_to_finish=0, cost=0):
        self.lat = lat
        self.lng = lng
        # This creates a semi unique identifier. Same as the index for slippy maps
        # https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
        self.grid_location = mercantile.tile(self.lat, self.lng, zoom=10) # 14 shows good resolution, 12 clips
        self.time = time
        self.cost = cost
        self.parent = parent
        self.heading = heading
        self.distance_to_finish = distance_to_finish

def astar_optimal_route(start, finish, max_steps=10000):
    # These are latlon tuples for display purposes only, they show the explored areas
    if Config.debug:
        leaflet_points = set()
    # This gives a way to end the search, nice for debugging
    step = 0
    # TODO this needs to be allowed to be a fraction
    hours_of_travel = 12
    # This holds the wind degree and speed
    wind_data = get_most_recent_netcdf()

    finish_bearing, x, total_distance_to_finish = Config.globe.inv(lats1=start['lat'],
                                                      lons1=start['lng'],
                                                      lats2=finish['lat'],
                                                      lons2=finish['lng'])

    start_node = Node(lat=start['lat'], lng=start['lng'], distance_to_finish=total_distance_to_finish)
    finish_node = Node(lat=finish['lat'], lng=finish['lng'])

    frontier = PriorityQueue()
    frontier.push((0, start_node))
    explored = {start_node.grid_location: start_node}

    # Create the boat polar diagram for get_boat_speed_numpy function
    polar_diagram = np.genfromtxt(Config.polar_diagram, delimiter=';')
    # replace the nans with - inf
    polar_diagram = np.nan_to_num(polar_diagram, nan=-np.inf)
    # sort according to the first column, wind angle
    polar_diagram = polar_diagram[np.argsort(polar_diagram[:, 0])]

    start_time = time.time()
    while not frontier.empty() and step < max_steps:
        current = frontier.pop()
        current_node = current[-1]
        wind_speed = wind_data.sel(latitude=current_node.lat,
                                   longitude=current_node.lng,
                                   method='nearest')['speed'].values.item()

        wind_degree = wind_data.sel(latitude=current_node.lat,
                                    longitude=current_node.lng,
                                    method='nearest')['degree'].values.item()
        # Timed Out Exit
        if time.time() > start_time + Config.timeout:
            if Config.debug:
                print('No route found')
                return list(leaflet_points), 'Not Found'

            else:
                print('No route found')
                return [start], 'Error: Not Found'

        # Check if the finish has been reached.
        elif current_node.grid_location == finish_node.grid_location:
            # This is the optimal route
            route = []
            # Traverse the nodes and rebuild the path
            current = current_node
            while current != None:
                route.append({'lat': current.lat, 'lng':current.lng})
                current = current.parent

            # Reverse to make sure this route has the same start and finish as the users drawn route
            route = route[::-1]
            route_time = utils.get_route_time(routes=[route])
            if Config.debug:
                print('Route:', route)
                print('Optimal Path Time', route_time)
                return list(leaflet_points), route_time

            return route, route_time

        for heading in[deg for deg in range(0, 361, 1)]:
            # Get the new location for traveling at speed. Polars are in nautical miles. fwd takes meters.
            true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
            speed = max(get_boat_speed(true_wind_angle, wind_speed, polar_diagram=polar_diagram), Config.motoring_speed)
            distance = speed * hours_of_travel * 1852
            good_heading_component = np.cos(np.radians(finish_bearing - heading))
            vmg = speed * good_heading_component

            if vmg > 0:

                # https://pyproj4.github.io/pyproj/stable/api/geod.html
                lng, lat, _ = Config.globe.fwd(lons=current_node.lng,
                                                          lats=current_node.lat,
                                                          az=heading,
                                                          dist=distance)

                finish_bearing, x, dist_finish = Config.globe.inv(lats1=lat,
                                                                   lons1=lng,
                                                                   lats2=finish_node.lat,
                                                                   lons2=finish_node.lng)

                # http://lagoon-inside.com/en/faster-thanks-to-the-vmg-concept/


                node = Node(lat=lat,
                            lng=lng,
                            time=current_node.time + hours_of_travel,
                            # larger negative take priority
                            #cost=-(1 / (current_node.time + hours_of_travel)),# This is basically Uniform Cost / Dijkstra’s Algorithm
                            #cost=-(vmg / (current_node.time + hours_of_travel)) * (1 / dist_finish ** 1.5),
                            #cost=-(vmg/dist_finish), # This goes directly towards the finish
                            #cost=-(vmg / (dist_finish + 1) * np.cos(np.radians(finish_bearing - heading)) * (current_node.time + hours_of_travel + 1 )),
                            #cost=-(vmg*10 / ((1 * current_node.time + hours_of_travel) * (dist_finish**1.5))),
                            cost=-(vmg*1)/dist_finish,
                            parent=current_node,
                            heading=heading,
                            distance_to_finish=dist_finish
                )
                # By restricting to only positive vmg of speed ratios we are headed at least towards the desitnation
                if node.grid_location not in explored:
                    explored[node.grid_location] = node
                    frontier.push((node.cost, id(node), node))
                    if Config.debug:
                        leaflet_points.add((node.lat, node.lng))
                elif explored[node.grid_location].time > node.time:
                    explored[node.grid_location] = node
                    frontier.push((node.cost, id(node), node))
        step += 1

    return [list(leaflet_points)], 'Frontier Empty or Steps exceeded'

# TODO Fix discrepancy between user drawn time and optimal route
# TODO fix heuristic
