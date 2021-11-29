# This Python file uses the following encoding: utf-8
import time

from PySide2.QtCore import QEventLoop, QObject, Signal, Slot, \
                            QThread, QCoreApplication, QEventLoop
from random import randrange
from Utilities import *
from CDevicesDriver import CDevicesDriver #check_value

from GlobalVar import run_thread

#class CCheck_measures_list(threading.Thread):
class CCheck_measures_list(QThread):
    """ This class could check each measure point in list_mes_pt with using
        yaml_data file to get command to send to the devices 
    """
    sigAddText = Signal(object, object)
    txt_info = ""

    @staticmethod
    def calc_val_limits (check_valu, percent, resolution):
        """ Return the min and max tolered values for the check_value """
        val_percent = check_valu / 100.0 * percent 
        val_min = check_valu - val_percent - resolution
        val_max = check_valu + val_percent + resolution
        return(val_min, val_max)

    @staticmethod   
    def check_read_val(read_val, check_value, percent, resolution):
        """ Check if the read_val for check_value is conform to the tolerances """
        (min,max) = CCheck_measures_list.calc_val_limits(check_value, percent, resolution)
        if read_val< min:
            return (False, min, max)
        elif read_val > max:
            return (False, min, max)
        else:
            return (True, min, max)


    def __init__(self, list_mes_pt, yaml_data, device_driver, parent=None) :
        super(CCheck_measures_list, self).__init__(parent)
        self.list_mes_pt = list_mes_pt
        self.gamme_yaml_data = yaml_data
        self.device_driver = device_driver

    def reset(self):
        for a_point in self.list_mes_pt:
            a_point.check = None
            a_point.update_indicator_color()

    def run(self):
        global txt_info
        global run_thread
        print ("Running thread measure list")
        print ( self.list_mes_pt)
        self.reset()
        tol_percent = float(self.gamme_yaml_data['tolerance'][0])
        tol_digit = float(self.gamme_yaml_data['tolerance'][1])
        for a_point in self.list_mes_pt:
            val_send = float(a_point.check_value)
            print("check the a_point {}".format(val_send))
            txt_info = "check the point {}".format(a_point.check_value)
            self.sigAddText.emit(q_green_color, txt_info)
            nb_try = 3
            while run_thread and nb_try:
                print("run_thread: {}".format(run_thread))
                # QEventLoop.processEvents(QEventLoop.AllEvents)    # Check for quit signal
                val_read = self.device_driver.check_value(a_point.check_value)
                (check_ok, min, max) = self.check_read_val(val_read, val_send, tol_percent, tol_digit)
                a_point.check = check_ok
                a_point.read_value = val_read
                print( "check {:0.4f} < {:0.4f}  < {:0.4f}  : {}".format(max, val_read, min, a_point.check))
                if  a_point.check: # end if the measure is good
                    break
                nb_try -= 1 # Try another time
            #a_point.check = True if randrange(0,10) >= 3 else False
            a_point.update_indicator_color()
            #self.outWidget.setTextColor(black_color)
            #self.outWidget.append("check the point {}".format(a_point.check_value))
            #self.outWidget.setTextColor( green_color if a_point.check == True else red_color)
            #self.outWidget.show()
            #color = q_red_color if a_point.check==False else q_green_color
            #print("Send command", self.gamme_yaml_data['giv4'] )
            # time.sleep(0.5)
            pass

