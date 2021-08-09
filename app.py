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


import datetime
from flask import Flask, render_template, jsonify, request, make_response
import astar
import utils, json
from config import Config

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    # Load converted json file for display on leaflet with windbarb plugin
    file = open(Config.json_dir + utils.get_jsons()[0], 'r')
    return render_template('index.html', data=json.load(file), extents=Config.extents, timeout=Config.timeout)


@app.route('/process_user_route', methods=['GET', 'POST'])
def process():
    routes = request.get_json()
    route_time = utils.get_route_time(routes=routes)
    string_time = '{} days {} hours {} minutes'.format(route_time.days, route_time.seconds // 3600,
                                                       (route_time.seconds // 60) % 60)
    res = make_response(jsonify({'route_time': string_time}), 200)
    return res


@app.route('/calculate_optimal_route', methods=['GET', 'POST'])
def router():
    routes = request.get_json()
    start = routes[-1][0]
    finish = routes[-1][-1]
    optimal_route, route_time = astar.astar_optimal_route(start, finish)
    if isinstance(route_time, datetime.timedelta):
        route_time = '{} days {} hours {} minutes'.format(route_time.days, route_time.seconds // 3600,
                                                          (route_time.seconds // 60) % 60)
    else:
        route_time = 'Not Found'
    res = make_response(jsonify({'route': optimal_route, 'route_time': route_time}), 200)
    return res


if __name__ == '__main__':
    app.run()

