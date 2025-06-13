from inspect import getframeinfo, stack
from datetime import datetime
import os
import sys

class Logger:
    def __init__(self, parent):
        self.log_level  = parent.log_level

    def log_message(self, msg='', log_type = ''):
        if log_type == '':
            log_type = 'info'
            index   = 1
        else:
            index   = 2
            
        msg         = str(msg)
        log_type    = str(log_type).lower()

        if(
            self.log_level != 'debug' and log_type == 'debug' or
            self.log_level == 'warning' and ( log_type == 'info' or log_type == 'debug') or
            self.log_level == 'error' and log_type != 'error'
        ):
            return

        try:
            date        = datetime.strftime(datetime.now(), '%d-%m-%Y %H:%M:%S')
            caller      = getframeinfo(stack()[index][0])
            location    = f'{os.path.basename(caller.filename)}:{caller.lineno} -'.ljust(25)

            if msg == '':
                log_msg = "\n\n"
            else:
                colors = {
                    'info':     '\033[32m',
                    'warning':  '\033[33m',
                    'error':    '\033[31m'
                }

                endc        = '\033[0m'

                if log_type != 'debug':
                    # Add colors
                    msg     = f"{colors[log_type]}{msg}{endc}"

                log_msg     = f'{date} - {location} {log_type.ljust(7)} - {msg}'

            print(log_msg)
                
        except Exception as e:
            print(f"Logger.py - Error - {str(e)} on line {sys.exc_info()[-1].tb_lineno}") 

    def debug(self, msg):
        self.log_message(msg, 'debug')

    def info(self, msg):
        self.log_message(msg, 'info')

    def warning(self, msg):
        self.log_message(msg, 'warning')

    def error(self, msg):
        self.log_message(msg, 'error')