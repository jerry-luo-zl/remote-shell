from urllib import parse

from flask import Flask, render_template
from flask import request
import urllib.parse

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/lzl/')
def test():
    return 'fuck!'

@app.route('/test/')
@app.route('/test/<name>')
def show_template(name=None):
    return render_template('test.html', name=name)


@app.route('/hello', methods=['POST'])
def send_commands():
    info = request.json
    command = input("input command:")
    return command


@app.route('/report', methods=['POST'])
def print_output():

    print(urllib.parse.unquote(str(request.get_data())).replace('+', ' '))
    return "valid"


if __name__ == '__main__':
    app.run(host='localhost', port=8080)
