# This Python file uses the following encoding: utf-8
""" This module define the CDevicesDriver class that can drive the 3 devices of 
AGIV bench. It could create an instance of this classe, that can be used by the others 
modules to drive the bench. The function get_devices_driver() permits to acces it
as a global variable
"""

from PySide2 import QtCore
from PySide2.QtGui import QColor
from CSerialScpiConnexion import *
import re
#import os       # file i/o for debug combobox
from Utilities import *
import time

color_cyan = QColor(51,175,255)
color_bluepurple = QColor(57,51,255)
color_red_purple = QColor(209,51,255)


CMD_BOX_FILE = "AgivDebugCmd.txt"


# The devices driver used by others modules 
d_driver = None

def create_devices_driver(cfg_file, print_funct, main_window=None):
    """ Create the device driver instance that can be used in another modules """
    global d_driver
    d_driver = CDevicesDriver(cfg_file, print_funct, main_window)
    return d_driver

def get_devices_driver():
    """ Return the instance of the device driver """
    return d_driver



class CDevicesDriver(QtCore.QObject):
    """ This object controls the various equipments used by the bench. 
    It builds and interprets the frames to position the equipments 
    in the configuration required for the measurement requested. 
    The constitution of the frames is based on the informations gived 
    in the configuration file.
    """
    sig_communication_error = Signal(object, object, object)

    flg_simulate = True

    def __init__(self, cfg_file, print_funct=None, pw=None):
        """ cfg_file:   config file with data sutch as time-out or communication 
                        characteristics.
            print_func: slot function to display dialogs with devices we wait for 
                        print(message, color, font)
            pw:         instance of parent window, used for debug commands and buttons
        """
        super(CDevicesDriver, self).__init__()
        self.str_error = None
        self.cfg_file = cfg_file
        self.scpi_relays = None
        self.scpi_aoip = None
        self.scpi_giv4 = None
        self.range = None           # The actual selected range
        self.range_data = None
        self.pw = pw

        self.init_combo_debug()

        devices_properties_list =\
        [
            ('scpi_relays',',AGIV', color_cyan, 'avec le banc AGIV', None),
            ('scpi_aoip',',CALYS', color_bluepurple, 'avec le CALYS', 2.0),
            ('scpi_giv4', ',GIV4', color_red_purple, 'avec le GIV4', None)
        ]
        for (attrib, idn, color, msg, timeout) in devices_properties_list:
            try:
                scpi = CSerialScpiConnexion(idn, color, timeout, self.flg_simulate)
                setattr(self, attrib, scpi) # Store the device
                if print_funct is not None:
                    self.sig_communication_error.connect(print_funct)
                    scpi.sigRequestComplete.connect(print_funct)
                    scpi.sigRequestComplete.emit(
                            'IDN {} found on {}\n{}'.format(idn, 
                            scpi.device_port.name,
                            scpi.id_string), color, SMALL_FONT)
            except ConnectionError:
                self.str_error = "Pas de connexion " + msg
                #raise ConnectionError(self.str_error)
        if self.flg_simulate:
            self.scpi_giv4 = None   # The other function could work with that

        # Go device to remote mode
        if self.scpi_aoip:
            self.scpi_aoip.send_request("*CLS;:REM;:SYST:ERR?")       # AOIP go in REMote mode
        if self.scpi_giv4:
            self.scpi_giv4.send_request("*CLS;:REM;:SYST:ERR?") 

        # Connect debuging tools 
        self.route_debug_widgets()

    def send_stop_remote(self):
        self.save_combo_debug()
        """ Called at the end of the applicatiion """
        if self.scpi_aoip:
            self.scpi_aoip.send_request('*CLS;:LOC;:SYST:ERR?')  # Switch to local mode
        if self.scpi_relays:
            self.scpi_relays.send_request(':REL 0; :REL?')  # Switch off all the relays
        if self.scpi_giv4:
            self.scpi_giv4.send_request('*CLS;:LOC;:SYST:ERR?')

    def send_giv_cmde_mode(self, cmde):
        retry = 2
        tx = cmde + ";:MODE?"
        match = re.search(r"MODE (.*?);", tx)
        req_mode = match.group(1)
        while self.scpi_giv4:   # Don't try if the connection is none
            retry -= 1
            rx = self.scpi_giv4.send_request(tx)
            if self.flg_simulate:
                return # Abord responce checking
            if req_mode in rx:    # It's ok is response contains the requested mode
                break
            elif retry == 0:
                raise ConnectionError("Echec de la commande Giv4\n'{}'".format(cmde))


    def send_aoip_range_cmde(self, cmde, wait_time=2.0):
        """ Send a new range selection for AOIP 
        This new algorithm request ERR until receve "No error"
        """
        if self.scpi_aoip is None:
            return

        retry = 3
        tx ="*CLS;"+ cmde + ";:ERR?"
        rx = self.scpi_aoip.send_request(tx, wait_time)
        if self.flg_simulate:
            return # Abort responce checking

        while True:  # Don't try if the connection is none
            if "No error" in rx:    # Ok
                break
            elif retry == 0:
                raise ConnectionError("Echec de la commande AOIP\n'{}'".format(cmde))
            rx = self.scpi_aoip.send_request("*SYS:ERR?", wait_time)
            retry -= 1

    def send_aoip_cmde(self, cmde, wait_time=0.5):
        """ Send a source command. same as self.send_aoip_range_cmde() 
        but with a shortest waiting time. 
        """
        self.send_aoip_range_cmde(cmde, wait_time)


    def check_value(self, val):
        aoip_meas_cmd = self.cfg_file['Commands']['aoip_mes']   # Measure command for Aoip
        # General default command or specific command for the actual range 
        aoip_out_cmd = self.range_data['aoip_out'] \
                if 'aoip_out' in self.range_data \
                else self.cfg_file['Commands']['aoip_out']
        # General waiting time before aoip measurement, of specific for the selected range
        aoip_wait_time = self.range_data['aoip_meas_time'] \
                if 'aoip_meas_time' in self.range_data \
                else self.cfg_file['Commands']['aoip_meas_time']
        # Giv output command, measure command, and waiting time for measurement
        giv_wait_time = self.cfg_file['Commands']['giv_meas_time']
        giv_meas_cmd = self.cfg_file['Commands']['giv_mes']
        giv_out_cmd = self.cfg_file['Commands']['giv_out']
        # direction of the measure: on Giv or on Aoip
        measure_on = self.range_data['measure_on']
        rx=''

        # Output on GIV, measure on Aoip ---------------
        if 'aoip' in measure_on:
            if self.scpi_giv4:
                self.scpi_giv4.send_request(giv_out_cmd.format(val))
            if self.flg_simulate:
                return float(val)+0.001
            # For the AOIP, we repeat the answer until we have a response
            retry = 3
            while retry > 0 and len(rx) == 0: # retry until we have a response 
                retry -= 1
                time.sleep(aoip_wait_time)  # Wait for measure stabilisation
                print("Wait {:03.1f}s for stabilisation".format(aoip_wait_time) )
                rx = self.scpi_aoip.send_request(aoip_meas_cmd) # Get measure
            rx = rx.split(',')[0]   # Keep first element of the AOIP response (eg: '9.999, mA')

        #  Output on Aoip mesure on Giv  -------------------
        elif 'giv' in measure_on:
            self.send_aoip_cmde(aoip_out_cmd.format(val)) 
            time.sleep(giv_wait_time)
            print("Wait {:03.1f}s for stabilisation".format(aoip_wait_time) )
            if self.scpi_giv4:
               rx = self.scpi_giv4.send_request(giv_meas_cmd)
            if self.flg_simulate:
                return float(val)+0.001

        try:
            read_val = float(rx.replace(' ',''))   
        except ValueError:
            self.sig_communication_error.emits(
                '!Valeur lue: "{}" incorrecte.\n'.format(rx)
                + 'Echec de calibration', q_red_color, BIG_FONT)
            read_val = 999.9

        return read_val



    def buzz(self, tps_laps):
        tps = time() + tps_laps
        while time() < tps:
            self.scpi_relays.send_request(":REL 5;REL?")
            self.scpi_relays.send_request(":REL 10;REL?")
        self.scpi_relays.send_request(":REL 0;REL?")
            

    def set_bench_relays(self):
        if self.flg_simulate:
            return
        relay_cmd = 0   # Binary code send to the bench
        relay_cfg = self.range_data['relays']   # The string with hex code to add
        for rly in relay_cfg:
            relay_cmd += rly
        rx = self.scpi_relays.send_request(":REL {};REL?".format(relay_cmd))
        if int(rx) != relay_cmd:
            raise ConnectionError("Echec de la Commande des relais.")


    def go_config(self, str_range):
        """ Send frames to position the bench in str_game configuration """
        self.range = str_range   # Note the atual range
        self.range_data = self.cfg_file['Ranges'][str_range]
        aoip_wait_range = self.cfg_file['Commands']['aoip_range_sel_time']

        try:
            # Send commands to the 3 devices
            self.set_bench_relays()
            cmde = self.range_data['aoip']
            self.send_aoip_range_cmde(cmde, aoip_wait_range)
            if 'aoip2' in self.range_data:  # if there are two commands
                cmde = self.range_data['aoip2']
                self.send_aoip_range_cmde(cmde, aoip_wait_range)
            cmde = self.range_data['giv4']
            self.send_giv_cmde_mode(cmde)
        except ConnectionError as ex:
            self.str_error = str(ex)
            #raise(ConnectionError())
            self.sig_communication_error.emit(self.str_error, q_red_color, BIG_FONT)
 
    def save_combo_debug(self):
        with open(CMD_BOX_FILE,'w') as myfile:
            for i in range (self.pw.cBoxDbgSendCmd.count()):
                txt = self.pw.cBoxDbgSendCmd.itemText(i)
                myfile.write(txt+'\n')

    def init_combo_debug(self):
        with open(CMD_BOX_FILE,'r') as myfile:
            self.pw.cBoxDbgSendCmd.clear()
            txt = myfile.readline().replace('\n','')
            while txt:
                print ("cmd: '"+ txt + "'")
                self.pw.cBoxDbgSendCmd.addItem(txt)
                txt = myfile.readline().replace('\n','')

    def send_debug_rly(self):
        str = self.pw.cBoxDbgSendCmd.currentText()
        self.scpi_relays.send_request(str)

    def send_debug_aoip(self):
        str = self.pw.cBoxDbgSendCmd.currentText()
        self.scpi_aoip.send_request(str)

    def send_debug_giv(self):
        str = self.pw.cBoxDbgSendCmd.currentText()
        self.scpi_giv4.send_request(str)

    def route_debug_widgets(self):
        self.pw.pBtSendRly.clicked.connect(self.send_debug_rly)
        self.pw.pBtSendAoip.clicked.connect(self.send_debug_aoip)
        self.pw.pBtSendGiv.clicked.connect(self.send_debug_giv)
