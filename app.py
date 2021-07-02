import flask
from flask import Flask, url_for, render_template, jsonify
import utils, json

app = Flask(__name__)

@app.route('/')
def test2():
    grib_directory = 'static/data/gribs/'
    grib_file = 'gfs.t12z.pgrb2.1p00.f000'
    data = utils.create_wind_speed_and_degree_json(grib_directory, grib_file)

    file = open('/home/richard/PycharmProjects/mweatherrouter/static/data/json/gfs.t12z.pgrb2.1p00.f000.json', 'r')
    jfile = json.load(file)
    return render_template('json_points_my_example.html', data=jfile)

@app.route('/love')
def markers():
    return render_template('index.html')

#https://stackoverflow.com/questions/11178426/how-can-i-pass-data-from-flask-to-javascript-in-a-template
#https://stackoverflow.com/questions/11178426/how-can-i-pass-data-from-flask-to-javascript-in-a-template
#https://stackoverflow.com/questions/36167086/separating-html-and-javascript-in-flask/36167179

@app.route('/test')
def test():
    grib_directory = 'static/data/gribs/'
    grib_file = 'gfs.t12z.pgrb2.1p00.f000'
    data = utils.create_wind_speed_and_degree_json(grib_directory, grib_file)

    file = open('/home/richard/PycharmProjects/mweatherrouter/static/data/json/gfs.t12z.pgrb2.1p00.f000.json', 'r')
    jfile = json.load(file)
    return render_template('pass_json_test.html', data=jfile)

@app.route('/test1')
def test1():
    data = ['a', 'b', 'c','d']
    return render_template('settings1.html', data=data, length = len(data))

if __name__ == '__main__':
    app.run(use_reloader = True, debug=True)
