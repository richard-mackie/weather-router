from shapely.geometry import Point, Polygon
from scipy.ndimage.filters import gaussian_filter
import heapq
import datetime
import numpy as np
import os
import glob
import xarray
import pandas as pd
from config import Config
from utils import get_boat_speed, calculate_true_wind_angle

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

class isochrone_Node:
    def __init__(self, lat, lng, time, parent, heading, dist_start, dist_finish, true_wind_angle, start_heading, dist_traveled):
        self.lat = lat
        self.lng = lng
        self.dist_start = dist_start
        self.dist_finish = dist_finish
        self.dist_traveled = dist_traveled
        self.time = datetime.timedelta(seconds=time).seconds
        self.parent = parent
        self.heading = heading
        self.true_wind_angle = true_wind_angle
        self.start_heading = int(start_heading)

def isochrone_optimal_route(start, finish, max_steps=2):
    os.chdir(Config.netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(Config.proj_dir)
    ds = xarray.open_dataset(Config.netcdf_dir + all_netcdfs[0])

    start_node = isochrone_Node(lat=start['lat'], lng=start['lng'], time=0, parent=None, heading=None, dist_start=0, dist_finish=0, true_wind_angle=0, start_heading=0, dist_traveled=0)
    finish_node = isochrone_Node(lat=finish['lat'], lng=finish['lng'], time=0, parent=None, heading=None, dist_start=0, dist_finish=0, true_wind_angle=0, start_heading=0, dist_traveled=0)
    isochrones_nodes = [[start_node]]
    isochrones_lat_lng = []

    # Hours of travel for each step
    hours_of_travel = 3

    # Calculate all the potential positions the boat could be in one time step
    for step in range(max_steps):
        next_isochrone = {}
        print('STEP:', step)

        for parent_node in isochrones_nodes[-1]:
            wind_speed = ds.sel(latitude=parent_node.lat, longitude=parent_node.lng, method='nearest')['speed'].values.item()
            wind_degree = ds.sel(latitude=parent_node.lat, longitude=parent_node.lng, method='nearest')['degree'].values.item()

            if step == 0:
                for heading in [deg for deg in range(0, 361, 1)]:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = Config.globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=heading, dist=distance)
                    azimuth1, azimuth2, dist_finish = Config.globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)
                    azimuth1, azimuth2, dist_start = Config.globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat, lons2=lng)
                    node = isochrone_Node(lat=lat, lng=lng, time=0, parent=start_node, heading=heading, dist_start=dist_start, dist_finish=dist_finish, true_wind_angle=true_wind_angle, start_heading=azimuth2, dist_traveled=distance)
                    next_isochrone[heading] = node

            else:
                child_points = PriorityQueue()

                for heading in [parent_node.heading + deg for deg in range(-90, 91, 1)]:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = Config.globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=heading, dist=distance)
                    azimuth1, azimuth2, dist_finish = Config.globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)
                    azimuth1, azimuth2, dist_start = Config.globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat, lons2=lng)
                    node = isochrone_Node(lat=lat, lng=lng, time=0, parent=start_node, heading=heading, dist_start=dist_start, dist_finish=dist_finish, true_wind_angle=true_wind_angle, start_heading=azimuth2, dist_traveled=distance)
                    # Take the node that goes furthest outward from the parent node
                    child_points.push((-np.tan(heading - parent_node.heading), node))
                chosen_node = child_points.pop()[-1]

                # Do not keep any headings with an angle less than 24 degree, We may however use their opposing tack at -90
                if chosen_node.heading + chosen_node.true_wind_angle >= 20:
                    next_isochrone[chosen_node.start_heading] = chosen_node

                # if the true wind angle is less than 45 we should consider tacking. We should then keep both points.
                if chosen_node.true_wind_angle <= 90:
                    for tack in [-90, 90]:
                        true_wind_angle = calculate_true_wind_angle(chosen_node.heading + tack, wind_degree)
                        speed = max(get_boat_speed(true_wind_angle, wind_speed), Config.motoring_speed)
                        distance = speed * 1852 * hours_of_travel
                        # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                        lng, lat, back_azimuth = Config.globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=chosen_node.heading + tack,
                                                           dist=distance)
                        azimuth1, azimuth2, dist_finish = Config.globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat,
                                                                    lons2=lng)
                        azimuth1, azimuth2, dist_start = Config.globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat,
                                                                   lons2=lng)
                        node = isochrone_Node(lat=lat, lng=lng, time=0, parent=parent_node, heading=chosen_node.heading + tack, dist_start=distance,
                                              dist_finish=dist_finish, true_wind_angle=true_wind_angle, start_heading=azimuth2, dist_traveled=distance)

                        # Do not head back towards the start!
                        if node.dist_start > parent_node.dist_start:
                            if not node.start_heading in next_isochrone:
                                next_isochrone[node.start_heading] = node
                            elif next_isochrone[node.start_heading].dist_start < node.dist_start:
                                next_isochrone[node.start_heading] = node


        # Attempt to filter the isochrone by stand deivation
        #next_isochrone_dist_start = [(node.dist_start) for node in next_isochrone_list]
        #print(next_isochrone_dist_start)
        #std = scipy.stats.tstd(next_isochrone_dist_start)
        #mean = scipy.stats.tmean(next_isochrone_dist_start)
        #print(mean, std)
        #cleaned_nodes = [node for node in next_isochrone_list if mean - std < node.dist_start < mean + std]

        next_isochrone_list = list(next_isochrone.values())
        next_isochrone_list.sort(key=lambda x: x.start_heading)
        next_isochrone_lat_lng = [(node.lat, node.lng) for node in next_isochrone_list]

        #next_isochrone_list, next_isochrone_lat_lng = create_smoothed_node_isochrones(list(next_isochrone.values()), start_node)

        isochrones_nodes.append(next_isochrone_list)
        isochrones_lat_lng.append(next_isochrone_lat_lng)

    return isochrones_lat_lng


def create_smoothed_node_isochrones(isochrone_list, start):
    isochrone_list.sort(key=lambda x: x.start_heading)

    lats, lngs = zip(*[(node.lat, node.lng) for node in isochrone_list])
    lats_smoothed = gaussian_filter(lats, sigma=2)
    lngs_smoothed = gaussian_filter(lngs, sigma=2)
    smoothed_lat_lng = list(zip(lats_smoothed, lngs_smoothed))
    lat_lng = []
    for i in range(len(isochrone_list)):
        current_node = isochrone_list[i]
        lat, lng = smoothed_lat_lng[i][0], smoothed_lat_lng[i][1]
        current_node.lat, current_node.lng = lat, lng
        _, current_node.heading, _ = Config.globe.inv(lats1=current_node.lat, lons1=current_node.lng, lats2=start.lat, lons2=start.lng)
        lat_lng.append((lat, lng))
    return isochrone_list, lat_lng

def found_goal(isochrone, finish_lng, finish_lat):
    # https://automating-gis-processes.github.io/CSC18/lessons/L4/point-in-polygon.html
    # Create Point objects
    p1 = Point(finish_lat, finish_lng)
    # Create a Polygon
    poly = Polygon(isochrone)
    return p1.within(poly)