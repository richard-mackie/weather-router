import numpy as np
import glob, os, time, requests, xarray, datetime
from config import Config

# Create the boat polar diagram for get_boat_speed_numpy function
polar_diagram = np.genfromtxt(Config.polar_diagram, delimiter=';')
# replace the nans with - inf
polar_diagram = np.nan_to_num(polar_diagram, nan=-np.inf)
# sort according to the first column, wind angle
polar_diagram = polar_diagram[np.argsort(polar_diagram[:, 0])]

def create_wind_spd_deg_jsons_from_all_gribs(input_dir=Config.grib_dir, output_dir=Config.json_dir, verbose=False):
    '''Takes a grib file and converts to a json file'''
    os.chdir(input_dir)
    all_gribs = [file for file in glob.glob('*.grib2')]
    os.chdir(Config.proj_dir)
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
            ds.to_netcdf(Config.netcdf_dir + filename.replace('grib2', 'nc'))
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
        open(Config.grib_dir + file_name, 'wb').write(r.content)
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
    os.chdir(Config.json_dir)
    jsons = [file for file in glob.glob('*.json')]
    jsons.sort()
    os.chdir(Config.proj_dir)

    # If there are no jsons then check to see if there are any gribs available to convert, if not then get some
    if len(jsons) == 0:
        os.chdir(Config.grib_dir)
        gribs = [file for file in glob.glob('*.grib2')]
        gribs.sort()
        os.chdir(Config.proj_dir)
        if len(gribs) == 0:
            get_gribs(degrees=1)
        create_wind_spd_deg_jsons_from_all_gribs()
        os.chdir(Config.json_dir)
        jsons = [file for file in glob.glob('*.json')]
        jsons.sort()
        os.chdir(Config.proj_dir)
    return jsons


def get_boat_speed(true_wind_angle, wind_speed, np_polars=polar_diagram):
    # get the wind degree column
    degree = np_polars[:,0]
    # subract the wind angle so we can sort to the the closest .1 errs on the side of the a wider angle
    row_index = np.argmin(abs(degree - true_wind_angle - .1))
    col_index = np.argmin(abs(np_polars[0] - wind_speed))
    return np_polars[row_index][col_index]


def get_route_time(routes):
    # This holds the wind degree and speed
    wind_data = get_most_recent_netcdf()
    route = routes[0]
    route_segments = []
    start_time = datetime.timedelta(minutes=0, seconds=0)

    for i in range(len(route) - 1):
        start_lat = route[i]['lat']
        start_lng = route[i]['lng']
        finish_lat = route[i + 1]['lat']
        finish_lng = route[i + 1]['lng']

        # https://pyproj4.github.io/pyproj/stable/api/geod.html
        azimuth1, azimuth2, distance = Config.globe.inv(start_lng, start_lat, finish_lng, finish_lat)
        # Convert distance(meters) to nautical miles
        distance *= 0.000539957

        heading = azimuth2 + 180

        wind_speed = wind_data.sel(latitude=start_lat, longitude=start_lng, method='nearest')['speed'].values.item()
        wind_degree = wind_data.sel(latitude=start_lat, longitude=start_lng, method='nearest')['degree'].values.item()

        true_wind_angle = calculate_true_wind_angle(heading, wind_degree)
        boat_speed = get_boat_speed(true_wind_angle, wind_speed)

        # This gives us a minimum boat speed of 1 knot, the polar diagrams are not completely filled out.
        time = start_time + datetime.timedelta(hours=distance/max(boat_speed, Config.motoring_speed))
        route_segment = {'id': i,
                         'start_lat_lon': (start_lat, start_lng),
                         'finish_lat_lon': (finish_lat, finish_lng),
                         'distance': distance,
                         'wind_speed': wind_speed,
                         'wind_degree': wind_degree,
                         'heading':heading,
                         'boat_speed':boat_speed,
                         'time':time}
        route_segments.append(route_segment)
        start_time = time
    return route_segments[-1]['time']


def calculate_true_wind_angle(heading, wind_degree):
    '''
    This returns the true
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


def get_most_recent_netcdf():
    # TODO actually get the most recent netcdt currently returning the first
    os.chdir(Config.netcdf_dir)
    all_netcdfs = [file for file in glob.glob('*.nc')]
    os.chdir(Config.proj_dir)
    dataset = xarray.open_dataset(Config.netcdf_dir + all_netcdfs[0])
    return dataset
