'''
Copyright (C) 2021 Richard Mackie

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
 any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

from pyproj import Geod
import os

class Config(object):
    # Prints some useful debugging messages to Terminal
    # Make sure to change the app.js plot for optimal route!!!
    debug = False

    # Optimal route timeout
    timeout = 25

    # This is the mapping extent NorthEast Corner, SouthWest Corner
    extents = { 'lat': 52.56928286558243, 'lng': -95.88867187500001 }, { 'lat': 17.26672782352052, 'lng': -177.09960937500003 }

    # Minimum boat speed. Simulates boat speed when there is no wind.
    motoring_speed = .0001

    # Directory References
    netcdf_dir = './static/data/netcdf/'
    grib_dir = './static/data/gribs/'
    json_dir = './static/data/json/'
    proj_dir = os.path.dirname(os.path.abspath(__file__))
    polar_diagram = './static/data/boat_polars/volvo65.txt'

    # Used for geodesic calculations such as distances and headings
    globe = Geod(ellps='clrk66')  # Use Clarke 1866 ellipsoid.