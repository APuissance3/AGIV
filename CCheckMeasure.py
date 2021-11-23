# This Python file uses the following encoding: utf-8
import time

from PySide2.QtCore import QObject, Signal, Slot, QThread
from random import randrange
from Utilities import *
from CDevicesDriver import CDevicesDriver #check_value

#class CCheck_measures_list(threading.Thread):
class CCheck_measures_list(QThread):
    """ This class could check each measure point in list_mes_pt with using
        yaml_data file to get command to send to the devices 
    """
    sigAddText = Signal(object, object)
    txt_info = ""

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
        print ("Running thread measure list")
        print ( self.list_mes_pt)
        self.reset()
        tolerance = float(self.gamme_yaml_data['tolerance'])
        for a_point in self.list_mes_pt:
            val_send = float(a_point.check_value)
            print("check the a_point {}".format(val_send))
            txt_info = "check the point {}".format(a_point.check_value)
            self.sigAddText.emit(q_green_color, txt_info)
            nb_try = 3
            while nb_try:
                val_read = self.device_driver.check_value(a_point.check_value)
                a_point.check = True if ( 
                        (val_read > val_send - tolerance)
                        and (val_read < val_send + tolerance)) \
                    else False
                print( "check {} < {}  < {}  : {}".format(val_send - tolerance, val_read, val_send - tolerance, a_point.check))
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

