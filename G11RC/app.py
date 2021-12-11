from time import sleep
from urllib import parse
from flask_cors import CORS, cross_origin
from flask import Flask, render_template, make_response, jsonify
from flask import request
import urllib.parse

from G11RC import config

app = Flask(__name__)



@app.route('/lzl/')
def test():
    return 'demo!'

@app.route('/test/')
@app.route('/test/<name>')
def show_template(name=None):
    #info = request.json
    return render_template('test.html', name=name)


@app.route('/hello', methods=['POST'])
@cross_origin()
def send_commands():
    info = request.json
    #print(info)
    #command = info["command"]

    f = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\test.txt')
    command = f.read()
    f.close()
    f2 = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\test.txt', 'w')
    command = command.replace('\n', '').replace('\r', '')
    for ch in command:
        print("%x " % ord(ch), end='')
   # command.replace('\n', '')
    print("debug1:"+command, end='')
    f2.close()

    return command


@app.route('/fronttest', methods=['POST'])
@cross_origin()
def handle_req():
    if request.method == 'POST':
        if request.form.to_dict() != {}:
            form = request.form.to_dict()
            print("form:" + str(request.form.to_dict()))
            pid = form['pid']
            command = 'taskkill /f /PID '+pid
            print("now command is " + command)
            f = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\test.txt', 'w')
            f.write(command)
            f.close()
        else:
            info = request.json
            command = info["command"]
            if command == "del":
                command = command + ' ' + info['path']
            print("now command is " + command)
            f = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\test.txt', 'w')
            f.write(command)
            f.close()
    return "200"


@app.route('/report', methods=['POST', 'GET'])
def store_output():
    command = request.json['cmd']
    print(command)
    tmp = command.split(' ')
    command_output = urllib.parse.unquote(str(request.json['output'])).replace('+', ' ')
    if tmp[0] == 'dir':
        print("dir!")
        file_info = {}
        file_entries = []
        command_output = urllib.parse.unquote(str(request.json['output'])).replace('+', ' ')
        print(command_output)
        sections = command_output.split('\n')
        file_info['path'] = sections[3]
        sections = sections[5:-3]
        for section in sections:
            print(section)
            tmp = section.split(' ')
            while '' in tmp:
                tmp.remove('')
            file_entry = {'LastWriteDate': tmp[0], 'LastWriteTime': tmp[1]}
            if tmp[2] == '<DIR>':
                file_entry.update({'Type': tmp[2], 'Length': '', 'Name': tmp[3]})
            else:
                file_entry.update({'Type': '<FILE>', 'Length': tmp[2], 'Name': tmp[3]})
            file_entries.append(file_entry)
        file_info['files'] = file_entries
        print("write dir success")
        f = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\dir_buffer.txt', 'w+')
        f.write(str(file_info)+'\n')
        f.close()
    else:
        #tmp = command_output.split('\n')
        #Eprint(tmp)
        command_output = command_output.replace('\n', '')
        f = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\output.txt', 'a')
        f.write(command_output+'\n')
        f.close()
    return ""


@cross_origin()
@app.route('/upload', methods=['POST'])
def upload_handler():
    f = request.files['uploaded']
    print("filename:" + f.filename)
    path = config.buf + f.filename
    f.save(path)

    return ""


@app.route('/index', methods=['POST', 'GET'])
def console_output():
    f_command_output =  open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\output.txt', 'r')

    command_output = f_command_output.read()

    #print(command_output)
    f_command_output.close()

    f_dir_output = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\buffers\\dir_buffer.txt', 'r')
    file_info = f_dir_output.read()
    file_entries=[]
    filepath=""

    if file_info != '':
        file_info = eval(file_info)
        file_entries = file_info['files']
        filepath = file_info['path']
        #print(file_entries)
        #print(filepath)

    f_dir_output.close()

    return render_template('test.html', filepath=filepath,  file_entries=file_entries, command_output=command_output)




if __name__ == '__main__':
    app.run(host='localhost', port=8080)
