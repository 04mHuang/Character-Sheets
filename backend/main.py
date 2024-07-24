from flask import Flask, render_template, request
# , redirect, url_for, flash
from waitress import serve

# gc.py needs to be fixed
# from gc import main as gc_main

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

@app.route('/')
@app.route('/index')
def index():
    # return "Character Sheets"
    return render_template('index.html')

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=3000)