import numpy as np
import glob, os, time, requests, xarray, datetime

def create_wind_spd_deg_jsons_from_all_gribs(input_dir='./static/data/gribs/', output_dir='./static/data/json/', verbose=False):
    '''Takes a grib file and converts to a json file'''
    os.chdir(input_dir)
    all_gribs = [file for file in glob.glob('*.grib2')]
    os.chdir('/home/richard/PycharmProjects/mweatherrouter')
    if len(all_gribs) == 0 and verbose:
        print('There are no gribs in the input directory.')
    else:
        for grib in all_gribs:
            ds = xarray.open_dataset(input_dir + grib, engine='cfgrib')
            #ds = ds.where((ds.latitude >= 25) & (ds.latitude <= 35), drop=True) This can filter out points we dont want
            ds['speed'] = (('latitude', 'longitude'), np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
            ds['degree'] = (('latitude', 'longitude'), 180 + np.rad2deg(np.arctan2(ds['v10'], ds['u10'])))
            result = ds.to_dataframe()[['speed','degree']].to_json(orient='table', indent=4)
            with open(output_dir + grib.replace('grib2', 'json'), 'w') as outfile:
                outfile.write(result)

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
    FFF = ['000', '012', '024','036']

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

