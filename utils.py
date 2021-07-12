import numpy as np
import glob, os, time, requests, xarray, datetime, math
import pandas as pd

def create_wind_spd_deg_jsons_from_all_gribs(input_dir='./static/data/gribs/', output_dir='./static/data/json/', verbose=False):
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
            ds.to_netcdf('./static/data/netcdf/' + filename.replace('grib2', 'nc'))
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
    grib_directory = 'static/data/gribs/'
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
        open(grib_directory + file_name, 'wb').write(r.content)
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
    grib_directory = './static/data/gribs/'
    json_directory = './static/data/json/'
    # Get the JSONs to serve up for the wind
    os.chdir(json_directory)
    jsons = [file for file in glob.glob('*.json')]
    jsons.sort()
    os.chdir('/home/richard/PycharmProjects/mweatherrouter')

    # If there are no jsons then check to see if there are any gribs available to convert, if not then get some
    if len(jsons) == 0:
        os.chdir(grib_directory)
        gribs = [file for file in glob.glob('*.grib2')]
        gribs.sort()
        os.chdir('/home/richard/PycharmProjects/mweatherrouter')
        if len(gribs) == 0:
            get_gribs(degrees=1)
        create_wind_spd_deg_jsons_from_all_gribs()
        os.chdir(json_directory)
        jsons = [file for file in glob.glob('*.json')]
        jsons.sort()
        os.chdir('/home/richard/PycharmProjects/mweatherrouter')
    return jsons

def get_wind_speed_and_degree_for_routes(routes):
    # TODO remove hard coded reference
    ds = xarray.open_dataset('./static/data/netcdf/20210709.1p00.000.nc')
    from haversine import haversine, Unit
    route = routes.pop()
    route_segments = []
    for i in range(len(route) - 1):
        # Need to convert the leaflet coordinate system back to gfs system
        # TODO create a single cordinate system
        start_lat = route[i]['lat']
        start_lng = route[i]['lng'] + 360
        finish_lat = route[i + 1]['lat']
        finish_lng = route[i + 1]['lng'] + 360
        distance = haversine((start_lat, start_lng), (finish_lat, finish_lng), unit=Unit.NAUTICAL_MILES)
        wind_speed = ds.sel(latitude=start_lat, longitude=start_lng, method='nearest')['speed'].values.item()
        wind_degree = ds.sel(latitude=start_lat, longitude=start_lng, method='nearest')['degree'].values.item()
        course_bearing = calculate_initial_compass_bearing((start_lat, start_lng), (finish_lat, finish_lng))
        true_wind_angle = calculate_true_wind_angle(course_bearing, wind_degree)
        boat_speed = None
        time = None
        route_segment = {'id': i, 'start': (start_lat, start_lng), 'finish': (finish_lat, finish_lng), 'distance': distance, 'wind_speed': wind_speed,
                         'wind_degree': wind_degree, 'course_bearing':course_bearing}
        print(route_segment)

def calculate_initial_compass_bearing(pointA, pointB):
    """
    Credit: https://gist.github.com/jeromer/2005586
    Calculates the bearing between two points.
    The formulae used is the following:
        θ = atan2(sin(Δlong).cos(lat2),
                  cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float

    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

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
    boat_polar_table = pd.read_csv('./static/data/boat_polars/express37', header=0, sep=';', index_col='twa/tws')

    result = boat_polar_table.iloc[boat_polar_table.index.get_loc(true_wind_angle, method='nearest')]
    return result

