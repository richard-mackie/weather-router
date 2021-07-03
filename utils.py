import numpy as np
import xarray
import datetime
import requests

def create_wind_speed_and_degree_json(directory, grib_file):
    '''Takes a grib file and converts to a json file'''
    ds = xarray.open_dataset(directory + grib_file + '.grib2', engine='cfgrib')
    ds['speed'] = (('latitude', 'longitude'), np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
    ds['degree'] = (('latitude', 'longitude'), 180 + np.rad2deg(np.arctan2(ds['v10'], ds['u10'])))
    result = ds.to_dataframe()[['speed','degree']].to_json(orient='table', indent=4)
    with open('./static/data/json/' + grib_file + '.json', 'w') as outfile:
        outfile.write(result)

def get_grib(resolution):
    url_bas0 = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl?file=gfs.t00z.pgrb2.1p00.anl&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.20210702%2F00%2Fatmos'
    url_bas1 = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p50.pl?file=gfs.t00z.pgrb2full.0p50.f000&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.20210702%2F00%2Fatmos'
    url_bas2 = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p50.pl?file=gfs.t06z.pgrb2full.0p50.f000&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.20210702%2F06%2Fatmos'
    degrees = {.5:'0p50', 1: '1p00'}
    #print('https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{}.pl?file=gfs.t06z.pgrb2full.0p50.f000&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.20210702%2F06%2Fatmos'.format(degrees[resolution]))
    get_grib(.5)

date_list = [(datetime.datetime.utcnow() - datetime.timedelta(days=i)) for i in range(7)]
last_seven_days = [str(day.date()).replace('-','') for day in date_list]

#grib_directory = 'static/data/gribs/'
#url = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl?file=gfs.t00z.pgrb2.1p00.f000&lev_10_m_above_ground=on&var_UGRD=on&var_VGRD=on&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs.20210702%2F00%2Fatmos'
#r = requests.get(url, allow_redirects=True)
#open(grib_directory + last_seven_days[0] + '.grib2', 'wb').write(r.content)

#print(datetime.datetime.utcnow().time())