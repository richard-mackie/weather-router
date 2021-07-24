import numpy as np
import glob, os, time, requests, xarray, datetime, math
import pandas as pd
import scipy.stats
from pyproj import Geod
from shapely.geometry import Point, Polygon, MultiPolygon
from scipy.ndimage.filters import gaussian_filter
import heapq
from config import Config
from shapely.geometry import shape, JOIN_STYLE

from scipy import stats


# Directory References
netcdf_dir = './static/data/netcdf/'
grib_dir = './static/data/gribs/'
json_dir = './static/data/json/'
proj_dir = '/home/richard/PycharmProjects/mweatherrouter'

# Used for geodesic calculations
globe = Geod(ellps='clrk66')  # Use Clarke 1866 ellipsoid.

# Create the boat polar diagram for get_boat_speed function
boat_polar_df = pd.read_csv('./static/data/boat_polars/polar', header=0, sep=';')
boat_polar_df.set_index('twa/tws')

# Create the boat polar diagram for get_boat_speed_numpy function
polar_diagram = np.genfromtxt('./static/data/boat_polars/polar', delimiter=';')
# replace the nans with - inf
polar_diagram = np.nan_to_num(polar_diagram, nan=-np.inf)
# sort according to the first comuln, wind angle
polar_diagram = polar_diagram[np.argsort(polar_diagram[:, 0])]


class Node:
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


def create_wind_spd_deg_jsons_from_all_gribs(input_dir=grib_dir, output_dir=json_dir, verbose=False):
    '''Takes a grib file and converts to a json file'''
    os.chdir(input_dir)
    all_gribs = [file for file in glob.glob('*.grib2')]
    os.chdir(proj_dir)
    if len(all_gribs) == 0 and verbose:
        print('There are no gribs in the input directory.')
    else:
        for filename in all_gribs:
            ds = xarray.open_dataset(input_dir + filename, engine='cfgrib')
            # convert the 0-360 to -180 + 180
            ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180))
            # Need to do this for the wind speed lookup later
            ds = ds.sortby('longitude')
            extents = Config.extents
            max_extents = extents[0]
            min_extents = extents[1]
            ds = ds.where((ds.latitude >= min_extents['lat'])
                          & (ds.latitude <= max_extents['lat'])
                          & (ds.longitude >= min_extents['lng'])
                          & (ds.longitude <= max_extents['lng']), drop=True)
            ds = ds.assign(speed=np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
            # https://www.eol.ucar.edu/content/wind-direction-quick-reference
            # https://en.wikipedia.org/wiki/Atan2
            ds = ds.assign(degree=(270 - np.arctan2(ds['v10'], ds['u10']) * (180 / np.pi)) % 360)
            # Save the modified data to the netcdf folder so we can refer to it later with netcdf
            ds.to_netcdf(netcdf_dir + filename.replace('grib2', 'nc'))
            pandas_result = ds.to_dataframe()[['speed','degree']].to_json(orient='table', indent=4)
            # Save the modified data for leaflet presentation
            with open(output_dir + filename.replace('grib2', 'json'), 'w') as outfile:
                outfile.write(pandas_result)


def get_gribs(degrees=1, left_lon=0, right_lon=360, top_lat=90, bottom_lat=-90, YYYYMMDD=''):
    '''
    Gets u-10 and v-10 wind grib data from NOAA. https://www.nco.ncep.noaa.gov/pmb/products/gfs/
    :params: YYYYMMDD is the Year, Month and Day
    :returns:Nothing
    '''
    DEG = {.25:'0p25', .5:'0p50', 1: '1p00'} # TODO only 1 is working atm
    # CC is the model cycle runtime (i.e. 00, 06, 12, 18) just using the first one as this doesn't really matter for simulation purposes
    CC = '00' # TODO Take the most recent forecast, currently just using the midnight since it's easy
    # FFF is the timestamp for the prediction based on the hours from the forecast conception
    FFF = ['000']

    if len(YYYYMMDD) == 0:
        YYYYMMDD = str(datetime.datetime.now().date()).replace('-','')
    print('Downloading Gribs', end='', flush=True)
    for i in range(len(FFF)):
        print('.', end='', flush=True)
        url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{}.pl?file=gfs.t00z.pgrb2.1p00.f{}' \
              '&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon={}&rightlon={}&toplat={}&bottomlat={}&dir=%2Fgfs.{}%2F00%2Fatmos'.format(DEG[degrees], FFF[i], left_lon, right_lon, top_lat, bottom_lat, YYYYMMDD)
        file_name = YYYYMMDD + '.' + DEG[degrees] + '.' + FFF[i] + '.grib2'
        r = requests.get(url, allow_redirects=True)
        open(grib_dir + file_name, 'wb').write(r.content)
        # Do not upset NOAA servers
        time.sleep(2)
    print(flush=True)


def slice_lat_lon(ds):
    '''Used for preprocessing to reduce the size of the datasets before merging'''
    ds = ds.drop('time')
    return ds.isel(latitude=slice(0, 3), longitude=slice(0, 3))


def get_jsons():
    '''
    Get the jsons update the directories as neededd
    :return:
    '''
    # Get the JSONs to serve up for the wind
    os.chdir(json_dir)
    jsons = [file for file in glob.glob('*.json')]
    jsons.sort()
    os.chdir(proj_dir)

    # If there are no jsons then check to see if there are any gribs available to convert, if not then get some
    if len(jsons) == 0:
        os.chdir(grib_dir)
        gribs = [file for file in glob.glob('*.grib2')]
        gribs.sort()
        os.chdir(proj_dir)
        if len(gribs) == 0:
            get_gribs(degrees=1)
        create_wind_spd_deg_jsons_from_all_gribs()
        os.chdir(json_dir)
        jsons = [file for file in glob.glob('*.json')]
        jsons.sort()
        os.chdir(proj_dir)
    return jsons


def get_boat_speed_numpy(true_wind_angle, wind_speed, np_polars=polar_diagram):
    # get the wind degree column
    degree = np_polars[:,0]
    # subract the wind angle so we can sort to the the closest .1 errs on the side of the a wider angle
    row_index = np.argmin(abs(degree - true_wind_angle - .1))
    col_index = np.argmin(abs(np_polars[0] - wind_speed))
    return np_polars[row_index][col_index]


def get_boat_speed(true_wind_angle, wind_speed, df=boat_polar_df):
    # This selects the row of the correct wind angle
    polar_angle = df.iloc[abs(df['twa/tws'] - true_wind_angle).idxmin()]
    # This selects the correct wind speed in the chosen row, +1 is to offset the index column
    polar_speed = abs(polar_angle.values[1:] - wind_speed).argmin() + 1
    return polar_angle.iloc[polar_speed]


def get_wind_speed_and_degree_for_routes(routes):
    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(proj_dir)
    ds = xarray.open_dataset(netcdf_dir + all_netcdfs[0])
    route = routes[0]

    route_segments = []
    start_time = datetime.timedelta(minutes=0, seconds=0)

    for i in range(len(route) - 1):
        # Need to convert the leaflet coordinate system back to gfs system
        # TODO create a single cordinate system
        start_lat = route[i]['lat']
        start_lng = route[i]['lng']
        finish_lat = route[i + 1]['lat']
        finish_lng = route[i + 1]['lng']

        # https://pyproj4.github.io/pyproj/stable/api/geod.html
        azimuth1, azimuth2, distance = globe.inv(start_lng, start_lat, finish_lng, finish_lat)
        # Convert meters to nautical miles
        distance *= 0.000539957
        course_bearing = azimuth2 + 180

        wind_speed = ds.sel(latitude=start_lat, longitude=start_lng, method='nearest')['speed'].values.item()
        wind_degree = ds.sel(latitude=start_lat, longitude=start_lng, method='nearest')['degree'].values.item()

        true_wind_angle = calculate_true_wind_angle(course_bearing, wind_degree)
        boat_speed = get_boat_speed(true_wind_angle, wind_speed)

        # This gives us a mininum boat speed of 1 knot, the polar diagrams are not completely filled out.
        time = start_time + datetime.timedelta(hours=distance/max(boat_speed, Config.motoring_speed))
        route_segment = {'id': i, 'start_lat_lon': (start_lat, start_lng), 'finish_lat_lon': (finish_lat, finish_lng), 'distance': distance, 'wind_speed': wind_speed,
                         'wind_degree': wind_degree, 'course_bearing':course_bearing, 'boat_speed':boat_speed, 'time':time}
        #(route_segment)
        route_segments.append(route_segment)
        start_time = time
    return route_segments[-1]['time']


def found_goal(isochrone, finish_lng, finish_lat):
    # https://automating-gis-processes.github.io/CSC18/lessons/L4/point-in-polygon.html
    # Create Point objects
    p1 = Point(finish_lat, finish_lng)
    # Create a Polygon
    poly = Polygon(isochrone)
    return p1.within(poly)


def calculate_true_wind_angle(heading, wind_degree):
    '''
    :param heading: This is the course the route is define by
    :param wind_degree: This is the compass heading in degrees of the wind
    :return: The shortest true wind angle
    '''
    result = (heading - wind_degree)
    if result > 180:
        result -= 360
    elif result < -180:
        result += 360
    return abs(result)


def isochrone_optimal_route(start, finish, max_steps=2):
    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(proj_dir)
    ds = xarray.open_dataset(netcdf_dir + all_netcdfs[0])

    start_node = Node(lat=start['lat'], lng=start['lng'], time=0, parent=None, heading=None, dist_start=0, dist_finish=0, true_wind_angle=0, start_heading=0, dist_traveled=0)
    finish_node = Node(lat=finish['lat'], lng=finish['lng'], time=0, parent=None, heading=None, dist_start=0, dist_finish=0, true_wind_angle=0, start_heading=0, dist_traveled=0)
    isochrones_nodes = [[start_node]]
    isochrones_lat_lng = []

    # Hours of travel for each step
    hours_of_travel = 3
    # TODO correct how this is done. Currently skipping lots of data.

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
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=heading, dist=distance)
                    azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)
                    azimuth1, azimuth2, dist_start = globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat, lons2=lng)
                    node = Node(lat=lat, lng=lng, time=0, parent=start_node, heading=heading, dist_start=dist_start, dist_finish=dist_finish, true_wind_angle=true_wind_angle, start_heading=azimuth2, dist_traveled=distance)
                    next_isochrone[heading] = node

            else:
                child_points = PriorityQueue()

                for heading in [parent_node.heading + deg for deg in range(-90, 91, 1)]:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=heading, dist=distance)
                    azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)
                    azimuth1, azimuth2, dist_start = globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat, lons2=lng)
                    node = Node(lat=lat, lng=lng, time=0, parent=start_node, heading=heading, dist_start=dist_start, dist_finish=dist_finish, true_wind_angle=true_wind_angle, start_heading=azimuth2, dist_traveled=distance)
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
                        speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                        distance = speed * 1852 * hours_of_travel
                        # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                        lng, lat, back_azimuth = globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=chosen_node.heading + tack,
                                                           dist=distance)
                        azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat,
                                                                    lons2=lng)
                        azimuth1, azimuth2, dist_start = globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat,
                                                                   lons2=lng)
                        node = Node(lat=lat, lng=lng, time=0, parent=parent_node, heading=chosen_node.heading + tack, dist_start=distance,
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
        _, current_node.heading, _ = globe.inv(lats1=current_node.lat, lons1=current_node.lng, lats2=start.lat, lons2=start.lng)
        lat_lng.append((lat, lng))
    return isochrone_list, lat_lng


