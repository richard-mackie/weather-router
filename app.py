from flask import Flask, url_for, render_template, jsonify, request, redirect, make_response

import astar
import utils, json
from config import Config

app = Flask(__name__)

@app.route('/', methods = ['GET'])
def index():
    # Load converted json file for display on leaflet with windbarb plugin
    file = open(Config.json_dir + utils.get_jsons()[0], 'r')
    return render_template('index.html', data=json.load(file), extents=Config.extents, timeout=Config.timeout)

@app.route('/process_user_route', methods=['GET','POST'])
def process():
    routes = request.get_json()
    route_time = utils.get_wind_speed_and_degree_for_routes(routes=routes)
    string_time = '{} days {} hours {} minutes'.format(route_time.days, route_time.seconds//3600, (route_time.seconds//60) % 60)
    res = make_response(jsonify({'route_time': string_time}), 200)
    return res

@app.route('/calculate_optimal_route', methods=['GET','POST'])
def router():
    routes = request.get_json()
    start = routes[0][0]
    finish = routes[0][-1]
    optimal_route, route_time = astar.astar_optimal_route(start, finish)
    string_time = '{} days {} hours {} minutes'.format(route_time.days, route_time.seconds // 3600, (route_time.seconds // 60) % 60)
    res = make_response(jsonify({'route': optimal_route, 'route_time': string_time}), 200)
    return res

if __name__ == '__main__':
    app.run(use_reloader = True, debug=True)


# TODO publish to the web
