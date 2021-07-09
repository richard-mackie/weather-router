import flask
from flask import Flask, url_for, render_template, jsonify, request
import utils, json, os, glob

app = Flask(__name__)

grib_directory = './static/data/gribs/'
json_directory = './static/data/json/'
jsons = utils.get_jsons()

@app.route('/', methods = ['GET','POST'])
def test():
    file = open(json_directory + jsons[0], 'r')
    if request.method == 'POST':
        routes = {}
        line = request.get_json()
        for i in range(len(line)):
            routes[i] = line[i]
        utils.get_wind_speed_and_degree_for_routes(routes=routes)
    return render_template('basemap.html', data=json.load(file))

#https://stackoverflow.com/questions/11178426/how-can-i-pass-data-from-flask-to-javascript-in-a-template
#https://stackoverflow.com/questions/36167086/separating-html-and-javascript-in-flask/36167179
if __name__ == '__main__':
    app.run(use_reloader = True, debug=True)


