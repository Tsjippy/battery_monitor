from inspect import getframeinfo, stack
from datetime import datetime
import os
import sys

# Change working dir to the folder of the file
os.chdir(os.path.dirname(os.path.realpath(__file__)))
class Logger:
    def __init__(self, level='info'):
        self.log_level  = level
        self.log_file   = 'log.log'
        print(f"Logging to {os.getcwd()}{self.log_file}")

        with open(self.log_file) as f:
            self.log_data = f.readlines()

    def log_message(self, msg='', type = 'info'):
        msg     = str(msg)
        type    = str(type).lower()

        if self.log_level != 'info' and type == 'info':
            return
        
        if self.log_level == 'warning' and type == 'info':
            return
        
        if self.log_level == 'error' and type != 'error':
            return
        
        try:
            date        = datetime.strftime(datetime.now(), '%d-%m-%Y %H:%M')
            caller      = getframeinfo(stack()[1][0])
            location    = f'{os.path.basename(caller.filename)}:{caller.lineno} -'.ljust(25)

            if msg == '':
                log_msg = "\n\n"
            else:
                log_msg     = f'{date} - {location}' + type.ljust(7) + ' - ' + msg

            print(log_msg)

            try:
                self.log_data.append(log_msg + "\n")

                if len(self.log_data > 1000):
                    self.log_data   = self.log_data[1:]

                f   = open(self.log_file, "w", encoding="utf-8")
                f.writelines(self.log_data)
                f.close()
            except PermissionError:
                print(f"No permission to write to {self.log_file}")
                
        except Exception as e:
            print(f"Logger.py - Error - {str(e)} on line {sys.exc_info()[-1].tb_lineno}") 
