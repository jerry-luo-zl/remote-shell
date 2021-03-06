
# -*- coding: utf-8 -*-
 
 
import pythoncom
import pyHook
import time
 
 
def onKeyboardEvent(event): 
    "处理键盘事件"   
    fobj.writelines('-' * 20 + 'Keyboard Begin' + '-' * 20 + '\n')
    fobj.writelines("Current Time:%s\n" % time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime()))
    fobj.writelines("MessageName:%s\n" % str(event.MessageName))
    fobj.writelines("Message:%d\n" % event.Message)
    fobj.writelines("Time:%d\n" % event.Time)
    fobj.writelines("Window:%s\n" % str(event.Window))
    fobj.writelines("WindowName:%s\n" % str(event.WindowName))
    fobj.writelines("Ascii_code: %d\n" % event.Ascii)
    fobj.writelines("Ascii_char:%s\n" % chr(event.Ascii))
    fobj.writelines("Key:%s\n" % str(event.Key))
    fobj.writelines('-' * 20 + 'Keyboard End' + '-' * 20 + '\n')
    return True
 
if __name__ == "__main__": 
    '''
    Function:操作SQLITE3数据库函数
    Input：NONE
    Output: NONE
    author: socrates
    blog:http://blog.csdn.net/dyx1024
    date:2012-03-1
    '''  
    #打开日志文件
    file_name = "F:\\hook_log.txt"
    fobj = open(file_name,  'w')       
    #创建hook句柄
    hm = pyHook.HookManager()
    #监控键盘
    hm.KeyDown = onKeyboardEvent
    hm.HookKeyboard()
    #循环获取消息
    pythoncom.PumpMessages()
    #关闭日志文件
    fobj.close() 