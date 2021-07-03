import numpy as np
import glob, os, time, dask, requests, xarray, datetime

def create_wind_speed_and_degree_json(directory, grib_file):
    '''Takes a grib file and converts to a json file'''
    ds = xarray.open_dataset(directory + grib_file + '.grib2', engine='cfgrib')
    ds['speed'] = (('latitude', 'longitude'), np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
    ds['degree'] = (('latitude', 'longitude'), 180 + np.rad2deg(np.arctan2(ds['v10'], ds['u10'])))
    result = ds.to_dataframe()[['speed','degree']].to_json(orient='table', indent=4)
    with open('./static/data/json/' + grib_file + '.json', 'w') as outfile:
        outfile.write(result)

def get_grib(degrees, left_lon=0, right_lon=360, top_lat=90, bottom_lat=-90, YYYYMMDD='', verbose=False):
    '''
    Gets u-10 and v-10 wind grib data from NOAA.
    https://www.nco.ncep.noaa.gov/pmb/products/gfs/
    :param resolution:
    :return:
    '''
    grib_directory = 'static/data/gribs/'

    DEG = {.25:'0p25', .5:'0p50', 1: '1p00'}
    # CC is the model cycle runtime (i.e. 00, 06, 12, 18) just using the first one as this doesn't really matter for simulation purposes
    CC = '00'
    # FFF is the forecast hour of product from 000 - 384
    FFF = ['000', '012', '024','036']
    
    # YYYYMMDD is the Year, Month and Day
    if len(YYYYMMDD) == 0:
        YYYYMMDD = str(datetime.datetime.utcnow().date()).replace('-','')

    for i in range(len(FFF)):
        url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{}.pl?file=gfs.t00z.pgrb2.1p00.f{}' \
              '&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon={}&rightlon={}&toplat={}&bottomlat={}&dir=%2Fgfs.{}%2F00%2Fatmos'.format(DEG[degrees], FFF[i], left_lon, right_lon, top_lat, bottom_lat, YYYYMMDD)
        if verbose:
            print(url)

        file_name = YYYYMMDD + '.' + DEG[degrees] + '.' + FFF[i] + '.grib2'

        r = requests.get(url, allow_redirects=True)
        open(grib_directory + file_name, 'wb').write(r.content)

        #data = xarray.open_dataset(grib_directory + file_name, engine='cfgrib')
        #print(data.u10)
        time.sleep(1)

#get_grib(degrees=1, right_lon=-90)

grib_directory = './static/data/gribs/'
os.chdir(grib_directory)
all_gribs = [grib_directory + file for file in glob.glob('*.grib2')]
os.chdir('/home/richard/PycharmProjects/mweatherrouter')
ds = xarray.open_mfdataset(all_gribs, concat_dim='time', combine='nested', engine='cfgrib')
ds['speed'] = (('time', 'latitude', 'longitude'), np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
ds['degree'] = (('time', 'latitude', 'longitude'), 180 + np.rad2deg(np.arctan2(ds['v10'], ds['u10'])))
