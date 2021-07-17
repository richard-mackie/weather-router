import numpy as np
import glob, os, time, requests, xarray, datetime, math
import pandas as pd
from pyproj import Geod
from shapely.geometry import Point, Polygon
from scipy.ndimage.filters import gaussian_filter
import heapq

# Directory References
netcdf_dir = './static/data/netcdf/'
grib_dir = './static/data/gribs/'
json_dir = './static/data/json/'

# Used for geodesic calculations
globe = Geod(ellps='clrk66')  # Use Clarke 1866 ellipsoid.

class Node:
    def __init__(self, lat, lng, time, parent, heading):
        self.lat = lat
        self.lng = lng
        self.time = datetime.timedelta(seconds=time).seconds
        self.parent = parent
        self.heading = heading

def create_wind_spd_deg_jsons_from_all_gribs(input_dir=grib_dir, output_dir=json_dir, verbose=False):
    '''Takes a grib file and converts to a json file'''
    os.chdir(input_dir)
    all_gribs = [file for file in glob.glob('*.grib2')]
    os.chdir('/home/richard/PycharmProjects/mweatherrouter')
    if len(all_gribs) == 0 and verbose:
        print('There are no gribs in the input directory.')
    else:
        for filename in all_gribs:
            ds = xarray.open_dataset(input_dir + filename, engine='cfgrib')
            # TODO drop areas outside of map
            ds = ds.assign(speed=np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
            #ds = ds.where((ds.latitude >= 25.5) & (ds.latitude <= 26), drop=True)
            # https://www.eol.ucar.edu/content/wind-direction-quick-reference
            # https://en.wikipedia.org/wiki/Atan2
            #ds = ds.assign(degree=(180/np.pi) * np.arctan2(-ds['u10'], -ds['v10']))
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
        time.sleep(1)
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
    os.chdir('/home/richard/PycharmProjects/mweatherrouter')

    # If there are no jsons then check to see if there are any gribs available to convert, if not then get some
    if len(jsons) == 0:
        os.chdir(grib_dir)
        gribs = [file for file in glob.glob('*.grib2')]
        gribs.sort()
        os.chdir('/home/richard/PycharmProjects/mweatherrouter')
        if len(gribs) == 0:
            get_gribs(degrees=1)
        create_wind_spd_deg_jsons_from_all_gribs()
        os.chdir(json_dir)
        jsons = [file for file in glob.glob('*.json')]
        jsons.sort()
        os.chdir('/home/richard/PycharmProjects/mweatherrouter')
    return jsons

def get_wind_speed_and_degree_for_routes(routes):
    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir('/home/richard/PycharmProjects/mweatherrouter')
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

        wind_speed = ds.sel(latitude=start_lat, longitude=start_lng + 360, method='nearest')['speed'].values.item()
        wind_degree = ds.sel(latitude=start_lat, longitude=start_lng + 360, method='nearest')['degree'].values.item()

        true_wind_angle = calculate_true_wind_angle(course_bearing, wind_degree)
        boat_speed = get_boat_speed(true_wind_angle, wind_speed)

        # This gives us a mininum boat speed of 1 knot, the polar diagrams are not completely filled out.
        time = start_time + datetime.timedelta(hours=distance/max(boat_speed, 1))
        route_segment = {'id': i, 'start_lat_lon': (start_lat, start_lng), 'finish_lat_lon': (finish_lat, finish_lng), 'distance': distance, 'wind_speed': wind_speed,
                         'wind_degree': wind_degree, 'course_bearing':course_bearing, 'boat_speed':boat_speed, 'time':time}
        #(route_segment)
        route_segments.append(route_segment)
        start_time = time
    return route_segments[-1]['time']

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

def get_boat_speed(true_wind_angle, wind_speed):
    df = pd.read_csv('./static/data/boat_polars/express37', header=0, sep=';')
    df.set_index('twa/tws')
    # This selects the row of the correct wind angle
    polar_angle = df.iloc[abs(df['twa/tws'] - true_wind_angle).idxmin()]
    # This selects the correct wind speed in the chosen row, +1 is to offset the index column
    polar_speed = abs(polar_angle.values[1:] - wind_speed).argmin() + 1
    return polar_angle.iloc[polar_speed]

def optimal_route(start, finish, max_steps=15):
    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir('/home/richard/PycharmProjects/mweatherrouter')
    ds = xarray.open_dataset(netcdf_dir + all_netcdfs[0])
    start = Node(lat=start['lat'], lng=start['lng'], time=0, parent=None, heading=None)
    isochrone_nodes = [[start]]
    isochrones_lats_lngs = []

    # Hours of travel for each step
    hours_of_travel = 1

    # Calculate all the potential positions the boat could be in one time step
    for step in range(max_steps):
        next_isochrone = []
        print('STEP:', step)

        # For every point in the last isochrone look for the children
        for point in isochrone_nodes[-1]:
            child_points = PriorityQueue()
            wind_speed = ds.sel(latitude=point.lat, longitude=point.lng + 360, method='nearest')['speed'].values.item()
            wind_degree = ds.sel(latitude=point.lat, longitude=point.lng + 360, method='nearest')['degree'].values.item()

            if step == 0:
                headings = [deg for deg in range(0, 361, 1)]
                for heading in headings:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = get_boat_speed(true_wind_angle, wind_speed)
                    travel_distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    new_location = globe.fwd(lons=point.lng, lats=point.lat, az=heading, dist=travel_distance)
                    new_node = Node(lat=new_location[1], lng=new_location[0], time=0, parent=start, heading=heading)
                    next_isochrone.append(new_node)

            else:
                headings = [deg + point.heading for deg in range(-45, 46, 10)]
                #print(point.heading, headings)
                for heading in headings:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = get_boat_speed(true_wind_angle, wind_speed)
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    travel_distance = speed * 1852 * hours_of_travel
                    new_lon, new_lat, bew_back_azimuth = globe.fwd(lons=point.lng, lats=point.lat, az=heading, dist=travel_distance)
                    new_node = Node(lat=new_lat, lng=new_lon, time=0, parent=point, heading=heading)
                    # Rank the children by how far away they go from the origin
                    azimuth1, azimuth2, distance_to_origin = globe.inv(lats1=start.lat, lons1=start.lng, lats2=new_node.lat, lons2=new_node.lng)
                    child_points.push((-distance_to_origin, heading, new_node))
                    #print('point:', (distance, heading, new_node), 'start:', start.lng, start.lat, 'point:', point.lng, point.lat)

                # Take the top headings
                next_isochrone.append(child_points.pop()[-1])

        node_list = [node for node in next_isochrone]
        node_list.sort(key=lambda x: x.heading)
        isochrone_nodes.append(node_list)

        polyline = smooth_to_contour(node_list)

        if found_goal(polyline, finish_lat=finish['lat'], finish_lng=finish['lng']):
            print('WE MADE IT!!!!!')
            isochrones_lats_lngs.append(polyline)
            return isochrones_lats_lngs

        isochrones_lats_lngs.append(polyline)

    return isochrones_lats_lngs


def found_goal(isochrone, finish_lng, finish_lat):
    # https://automating-gis-processes.github.io/CSC18/lessons/L4/point-in-polygon.html
    # Create Point objects
    p1 = Point(finish_lat, finish_lng)

    # Create a Polygon
    poly = Polygon(isochrone)
    return p1.within(poly)

def smooth_to_contour(isochrone):
    lats = []
    lngs = []
    [(lats.append(node.lat), lngs.append(node.lng)) for node in isochrone]
    lats1 = gaussian_filter(lats, sigma=7, mode=['wrap'])
    lngs1 = gaussian_filter(lngs, sigma=7, mode=['wrap'])
    latlngs = list(zip(lats1, lngs1))
    return latlngs

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



