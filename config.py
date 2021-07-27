from pyproj import Geod

class Config(object):
    # Prints some useful debugging messages to Terminal
    # Make sure to change the app.js plot for optimal route!!!
    debug = True

    # Optimal route timeout
    timeout = 15

    # This is the mapping extent NorthEast Corner, SouthWest Corner
    extents = { 'lat': 52.56928286558243, 'lng': -95.88867187500001 }, { 'lat': 17.26672782352052, 'lng': -177.09960937500003 }

    # Minimum boat speed. Simulates boat speed when there is no wind.
    motoring_speed = 1

    # Directory References
    netcdf_dir = './static/data/netcdf/'
    grib_dir = './static/data/gribs/'
    json_dir = './static/data/json/'
    proj_dir = '/home/richard/PycharmProjects/mweatherrouter'
    polar_diagram = './static/data/boat_polars/volvo65'

    # Used for geodesic calculations such as distances and headings
    globe = Geod(ellps='clrk66')  # Use Clarke 1866 ellipsoid.