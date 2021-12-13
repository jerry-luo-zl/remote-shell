from time import sleep
from urllib import parse
from flask_cors import CORS, cross_origin
from flask import Flask, render_template, make_response, jsonify
from flask import request
import urllib.parse

from G11RC import config

app = Flask(__name__)

# 处理客户端寻求指令
@app.route('/hello', methods=['POST'])
@cross_origin()
def send_commands():
    info = request.json

    with open(config.ROOT + 'buffers\\cmd_buf.txt') as f:
        command = f.read()
    with open(config.ROOT + 'buffers\\cmd_buf.txt', 'w') as f:
        pass
    command = command.replace('\n', '').replace('\r', '')

    return command


# 根据服务端UI的点击和操作情况，构造相应的要发往客户端的指令
@app.route('/consturct', methods=['POST'])
@cross_origin()
def consturct_command():
    if (request.files.get('upFile')): # 提交的表单含有文件(download功能)
        f = request.files.get('upFile')
        f.save(config.STATIC+f.filename)
        with open(config.ROOT + 'buffers\\filename.txt', 'w') as fd:
            fd.write(f.filename)

    elif request.form.to_dict() != {}: # 提交普通的表单
        form = request.form.to_dict()
        print("form:" + str(request.form.to_dict()))
        pid = form['pid']
        command = 'kill_proc ' + pid
        print("now command is " + command)
        f = open(config.ROOT + 'buffers\\cmd_buf.txt', 'w')
        f.write(command)
        f.close()
    else:
        info = request.json
        command = info["command"]
        if command == "del":
            command = command + ' ' + info['path']
        print("now command is " + command)
        f = open(config.ROOT + 'buffers\\cmd_buf.txt', 'w')
        f.write(command)
        f.close()
    return ""


# 接收客户端传来的指令执行结果
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
        f = open(config.ROOT + 'buffers\\dir_buffer.txt', 'w+')
        f.write(str(file_info)+'\n')
        f.close()
    else:
        command_output = command_output.replace('\n', '')
        f = open(config.ROOT+'buffers\\output.txt', 'a')
        f.write(command_output+'\n')
        f.close()
    return ""


# 接收客户端上传到服务端的文件
@cross_origin()
@app.route('/upload', methods=['POST'])
def upload_handler():
    f = request.files['uploaded']
    print("filename:" + f.filename)
    path = config.FILE_FROM_CLIENT + f.filename
    f.save(path)

    return ""


# 主界面路由，将功能执行结果在网页上渲染显示
@app.route('/index', methods=['POST', 'GET'])
def console_output():
    f_command_output =  open(config.ROOT + 'buffers\\output.txt', 'r')

    command_output = f_command_output.read()

    f_command_output.close()

    f_dir_output = open(config.ROOT + 'buffers\\dir_buffer.txt', 'r')
    file_info = f_dir_output.read()
    file_entries=[]
    filepath=""

    filename = ""
    with open(config.ROOT + 'buffers\\filename.txt', 'r') as f:
        filename = f.read()

    if file_info != '':
        file_info = eval(file_info)
        file_entries = file_info['files']
        filepath = file_info['path']

    f_dir_output.close()

    return render_template('main.html', filepath=filepath,  file_entries=file_entries,
                           command_output=command_output, filename=filename)




if __name__ == '__main__':
    app.run(host='localhost', port=8080)
