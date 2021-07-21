from flask import Flask, url_for, render_template, jsonify, request, redirect, make_response
import utils, json
from config import Config

app = Flask(__name__)

# Raw GRIBS obtained from NOAA
grib_directory = './static/data/gribs/'
# Converted GRIBS for display on leaflet with windbarb plugin
json_directory = './static/data/json/'
jsons = utils.get_jsons()

@app.route('/', methods = ['GET'])
def index():
    file = open(json_directory + jsons[0], 'r')
    return render_template('index.html', data=json.load(file), extents=Config.extents)

@app.route('/process_user_route', methods=['GET','POST'])
def process():
    routes = request.get_json()
    time = utils.get_wind_speed_and_degree_for_routes(routes=routes)
    string_time = '{} days {} hours {} minutes'.format(time.days, time.seconds//3600, (time.seconds//60) % 60)
    res = make_response(jsonify({'time':string_time}), 200)
    return res

@app.route('/calculate_optimal_route', methods=['GET','POST'])
def router():
    routes = request.get_json()
    start = routes[0][0]
    finish = routes[0][-1]
    optimal_route = utils.optimal_route(start, finish, max_steps=3)
    #optimal_route = utils.optimal_route_numpy(start, finish)
    res = make_response(jsonify(optimal_route), 200)
    return res

if __name__ == '__main__':
    app.run(use_reloader = True, debug=True)


