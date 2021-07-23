import numpy as np
import glob, os, time, requests, xarray, datetime, math
import pandas as pd
from pyproj import Geod
from shapely.geometry import Point, Polygon
from scipy.ndimage.filters import gaussian_filter
import heapq
from config import Config

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
    def __init__(self, lat, lng, time, parent, heading, dist_start, dist_finish):
        self.lat = lat
        self.lng = lng
        self.dist_start = dist_start
        self.dist_finish = dist_finish
        self.time = datetime.timedelta(seconds=time).seconds
        self.parent = parent
        self.heading = heading


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


def optimal_route(start, finish, max_steps=15):
    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(proj_dir)
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
            wind_speed = ds.sel(latitude=point.lat, longitude=point.lng, method='nearest')['speed'].values.item()
            wind_degree = ds.sel(latitude=point.lat, longitude=point.lng, method='nearest')['degree'].values.item()

            if step == 0:
                headings = [deg for deg in range(0, 361, 5)]
                for heading in headings:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    travel_distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    new_location = globe.fwd(lons=point.lng, lats=point.lat, az=heading, dist=travel_distance)
                    new_node = Node(lat=new_location[1], lng=new_location[0], time=0, parent=start, heading=heading)
                    next_isochrone.append(new_node)

            else:
                headings = [deg + point.heading for deg in range(-60, 61, 10)]
                for heading in headings:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    travel_distance = speed * 1852 * hours_of_travel
                    new_lon, new_lat, bew_back_azimuth = globe.fwd(lons=point.lng, lats=point.lat, az=heading, dist=travel_distance)
                    new_node = Node(lat=new_lat, lng=new_lon, time=hours_of_travel + point.time, parent=point, heading=heading)
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


def optimal_route_smoothed(start, finish, max_steps=2):
    os.chdir(netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(proj_dir)
    ds = xarray.open_dataset(netcdf_dir + all_netcdfs[0])

    start_node = Node(lat=start['lat'], lng=start['lng'], time=0, parent=None, heading=None, dist_start=0, dist_finish=0)
    finish_node = Node(lat=finish['lat'], lng=finish['lng'], time=0, parent=None, heading=None, dist_start=0, dist_finish=0)
    isochrones_nodes = [[start_node]]
    isochrones_lat_lng = []

    # Hours of travel for each step
    hours_of_travel = 6
    # TODO correct how this is done. Currently skipping lots of data.

    # Calculate all the potential positions the boat could be in one time step
    for step in range(max_steps):
        next_isochrone = []
        print('STEP:', step)

        for parent_node in isochrones_nodes[-1]:
            wind_speed = ds.sel(latitude=parent_node.lat, longitude=parent_node.lng, method='nearest')['speed'].values.item()
            wind_degree = ds.sel(latitude=parent_node.lat, longitude=parent_node.lng, method='nearest')['degree'].values.item()

            if step == 0:
                for heading in [deg for deg in range(0, 181, 1)]:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=heading, dist=distance)
                    azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)
                    next_isochrone.append(Node(lat=lat, lng=lng, time=0, parent=start_node, heading=heading, dist_start=distance, dist_finish=dist_finish))

            else:
                child_points = PriorityQueue()
                for heading in [parent_node.heading + deg for deg in range(-90, 91, 1)]:
                    true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=heading,  dist=distance)
                    #azimuth1, azimuth2, dist_start = globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat, lons2=lng)
                    azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat, lons2=lng)
                    node = Node(lat=lat, lng=lng, time=0, parent=parent_node, heading=heading, dist_start=distance, dist_finish=dist_finish)
                    #child_points1.push((-dist_start, node))
                    # Take the node that goes furthest outward from the parent node
                    child_points.push((-np.tan(heading - parent_node.heading), node))
                chosen_node = child_points.pop()[-1]

                # Do not keep any headings with an angle less than 24 degree, We may however use their opposing tack at -90
                if calculate_true_wind_angle(chosen_node.heading, wind_degree) >= 24:
                    next_isochrone.append(chosen_node)

                # if the true wind angle is less than 45 we should consider tacking. We should then keep both points.
                if 40 <= calculate_true_wind_angle(chosen_node.heading, wind_degree) <= 55:
                    print(parent_node.heading, chosen_node.heading)
                    true_wind_angle = calculate_true_wind_angle(chosen_node.heading - 90, wind_degree)
                    speed = max(get_boat_speed_numpy(true_wind_angle, wind_speed), Config.motoring_speed)
                    distance = speed * 1852 * hours_of_travel
                    # Get the new location for traveling at speed for 1 hour. Polars are in nautical miles. fwd takes meters.
                    lng, lat, back_azimuth = globe.fwd(lons=parent_node.lng, lats=parent_node.lat, az=chosen_node.heading - 90,
                                                       dist=distance)
                    # azimuth1, azimuth2, dist_start = globe.inv(lats1=start_node.lat, lons1=start_node.lng, lats2=lat, lons2=lng)
                    azimuth1, azimuth2, dist_finish = globe.inv(lats1=finish_node.lat, lons1=finish_node.lng, lats2=lat,
                                                                lons2=lng)
                    node = Node(lat=lat, lng=lng, time=0, parent=parent_node, heading=chosen_node.heading - 90, dist_start=distance,
                                dist_finish=dist_finish)
                    next_isochrone.append(node)


        nodes, lat_lngs = create_smoothed_node_isochrones(next_isochrone, start_node)
        isochrones_nodes.append(nodes)
        isochrones_lat_lng.append(lat_lngs)

    return isochrones_lat_lng


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
    lats1 = gaussian_filter(lats, sigma=2, mode=['wrap'])
    lngs1 = gaussian_filter(lngs, sigma=2, mode=['wrap'])
    latlngs = list(zip(lats1, lngs1))
    return latlngs

def create_smoothed_isochrones(isochrone_list, parent, time):
    isochrone_list.sort(key=lambda x: x[2])
    lats, lngs = zip(*[(i[0], i[1]) for i in isochrone_list])
    lats_smoothed = gaussian_filter(lats, sigma=0, mode=['wrap'])
    lngs_smoothed = gaussian_filter(lngs, sigma=0, mode=['wrap'])
    smoothed_isochrone = list(zip(lats_smoothed, lngs_smoothed))
    return [[smoothed_isochrone]]

def create_smoothed_node_isochrones(isochrone_list, start):
    import scipy.ndimage
    # Resample your data grid by a factor of 3 using cubic spline interpolation.
    isochrone_list.sort(key=lambda x: x.heading)
    lats, lngs = zip(*[(node.lat, node.lng) for node in isochrone_list])

    data = scipy.ndimage.zoom(list(zip(lats,lngs)), 3)
    #print(list(zip(lats,lngs)))
    #print(data)

    lats_smoothed = gaussian_filter(lats, sigma=0, mode=['wrap'])
    lngs_smoothed = gaussian_filter(lngs, sigma=0, mode=['wrap'])
    smoothed_lat_lng = list(zip(lats_smoothed, lngs_smoothed))
    lat_lng = []
    for i in range(len(isochrone_list)):
        current_node = isochrone_list[i]
        lat, lng = smoothed_lat_lng[i][0], smoothed_lat_lng[i][1]
        current_node.lat, current_node.lng = lat, lng
        _, current_node.heading, _ = globe.inv(lats1=current_node.lat, lons1=current_node.lng, lats2=start.lat, lons2=start.lng)
        lat_lng.append((lat, lng))
    return isochrone_list, lat_lng

# Course Degrees, Lat, Lon, True Wind Angle, Boat Speed, Distance to Start
#point = np.array([180, 17, -144, 45, 0, 0], dtype=float)
#start = {'lat': 23, 'lng': -150}

#print(get_best_n_children(start, point))
#x = optimal_route_numpy(start, start, 1)
#print(x)

