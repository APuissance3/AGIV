# This Python file uses the following encoding: utf-8
""" This module define the CSerialDevice class that provide methods to drive the 3 devices of 
AGIV bench. 


Module non utilisé pour le moment. C'est encore CDevicesDriver qui fait le job


"""

from PySide2 import QtCore
from PySide2.QtGui import QColor
from .CSerialScpiConnexion import *
import re
from .Utilities import *
import time

color_cyan = QColor(51,175,255)
color_bluepurple = QColor(57,51,255)
color_red_purple = QColor(209,51,255)



class CScpiDevice(QtCore.QObject):
    """ This object controls the various equipments used by the bench with SCPI protocol. 
    It builds and interprets the frames to position the equipments 
    in the configuration required for the measurement requested. 
    The constitution of the frames is based on the informations gived 
    in the configuration file.
    """
    sig_communication_error = Signal(object, object, object)
    flg_simulate = False

    def __init__(self, cfg_file, cfg_name, idn_name, timeout, simu,  
                    print_funct=None, print_color=q_black_color, pw=None):
        """ cfg_file:   config file with data sutch as time-out or communication 
                        characteristics.
            cfg_name:   name in the config file (eg. 'aoip' or 'giv4' or 'relays')
            idn_name:   response value to IDN. (eg. 'AGIV', 'CALYS', 'GIV4')
            print_func: slot function to display dialogs with devices we wait for 
                        print(message, color, font)
            pw:         instance of parent window, used for debug commands and buttons
        """
        super(CScpiDevice, self).__init__() # Call QtCore.QObject __init__
        self.str_error = None
        self.cfg_file = cfg_file
        self.cfg_name = cfg_name
        self.idn_name = idn_name
        self.timeout = timeout
        self.simu = simu
        self.pw = pw                # parent window
        self.scpicom = None         # The serial com port used for communication
        self.range = None           # The actual selected range
        self.range_data = None

    def connect(self):
        try:
            self.scpicom = CSerialScpiConnexion(self.idn_name, self.color, self.timeout, self.flg_simulate)
            if self.print_funct is not None:
                self.sig_communication_error.connect(self.print_funct)
                self.scpi.sigRequestComplete.connect(self.print_funct)
                self.scpi.sigRequestComplete.emit(
                        'IDN {} found on {}\n{}'.format(self.idn_name, 
                        self.scpi.device_port.name,
                        self.scpi.id_string), self.color, SMALL_FONT)
        except ConnectionError:
            self.str_error = f"Pas de connexion avec {self.idn_name}"

        # Go device to remote mode
        self.scpicom.send_request("*CLS;:REM;:SYST:ERR?")

    def unconnect(self):
        # Go device to local mode
        self.scpicom.send_request("*CLS;:LOC;:SYST:ERR?")



