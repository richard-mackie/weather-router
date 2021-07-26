from pyproj import Geod

class Config(object):
    extents = { 'lat': 52.56928286558243, 'lng': -95.88867187500001 }, { 'lat': 17.26672782352052, 'lng': -177.09960937500003 }

    # Minimum boat speed. Simulates boat speed when there is no wind.
    motoring_speed = 0

    # Optimal route timeout
    timeout = 17

    # Directory References
    netcdf_dir = './static/data/netcdf/'
    grib_dir = './static/data/gribs/'
    json_dir = './static/data/json/'
    proj_dir = '/home/richard/PycharmProjects/mweatherrouter'
    polar_diagram = './static/data/boat_polars/polar'

    # Used for geodesic calculations such as distances and headings
    globe = Geod(ellps='clrk66')  # Use Clarke 1866 ellipsoid.