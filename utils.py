import numpy as np
import xarray

def create_wind_speed_and_degree_json(directory, grib_file):
    '''Takes a grib file and converts to a json file'''
    ds = xarray.open_dataset(directory + grib_file, engine='cfgrib')
    ds['speed'] = (('latitude', 'longitude'), np.sqrt(np.square(ds['u10']) + np.square(ds['v10'])))
    ds['degree'] = (('latitude', 'longitude'), 180 + np.rad2deg(np.arctan2(ds['v10'], ds['u10'])))

    result = ds.to_dataframe()[['speed','degree']].to_json(orient='table', indent=4)

    with open('./static/data/json/' + grib_file + '.json', 'w') as outfile:
        outfile.write(result)


grib_directory = 'static/data/gribs/'
grib_file = 'gfs.t12z.pgrb2.1p00.f000'

create_wind_speed_and_degree_json(grib_directory, grib_file)