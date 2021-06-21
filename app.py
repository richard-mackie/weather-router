from flask import Flask, url_for, render_template

app = Flask(__name__)

@app.route('/')
def basemap():
    return render_template('basemap.html')

if __name__ == '__main__':
    app.run()
