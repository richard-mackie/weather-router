import flask
from flask import Flask, url_for, render_template, jsonify
import utils, json, os, glob

app = Flask(__name__)

grib_directory = './static/data/gribs/'
json_directory = './static/data/json/'
jsons = utils.get_jsons()

@app.route('/')
def test():
    file = open(json_directory + jsons[0], 'r')
    return render_template('json_points_my_example.html', data=json.load(file))

#https://stackoverflow.com/questions/11178426/how-can-i-pass-data-from-flask-to-javascript-in-a-template
#https://stackoverflow.com/questions/36167086/separating-html-and-javascript-in-flask/36167179
@app.route('/test')
def test1():
    grib_directory = 'static/data/gribs/'
    grib_file = '20210702'
    data = utils.create_wind_spd_deg_jsons_from_all_gribs(grib_directory, grib_file)

    file = open('/home/richard/PycharmProjects/mweatherrouter/static/data/json/gfs.t12z.pgrb2.1p00.f000.json', 'r')
    jfile = json.load(file)

    return render_template('pass_json_test.html', data=jfile)

if __name__ == '__main__':
    app.run(use_reloader = True, debug=True)


