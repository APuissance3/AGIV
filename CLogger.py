# This Python file uses the following encoding: utf-8
import datetime as dt

class CLogger():
    """ 
    This class is used to log the differents actions executed with a giv 
    It append line to log file 
    """

    def __init__(self, filename=None):
        self.filename = filename

    def log_change_name(self, filename):
        self.filename = filename

    def log_operation(self, strope):
        """ Indicate the operation with the date and time """
        if self.filename is None:
            return
        d_now = dt.datetime.now()
        str_now = d_now.strftime("%Y/%m/%d %H:%M:%S")
        with open(self.filename,'a') as myfile:
            myfile.write('\n' + str_now + '\n> ' +strope + '\n')

    def logdata(self, *args):
        if self.filename is None:
            return
        with open(self.filename,'a') as myfile:
            for param in args:
                myfile.write(param)
     
