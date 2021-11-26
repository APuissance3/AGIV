# This Python file uses the following encoding: utf-8
#from PyQt5 import QtCore
from PySide2 import QtCore
from PySide2.QtCore import QObject
from CSerialScpiConnexion import *

from Utilities import *
from PySide2.QtGui import QColor

color_cyan = QColor(51,175,255)
color_bluepurple = QColor(57,51,255)
color_red_purple = QColor(209,51,255)

class CDevicesDriver(QtCore.QObject):
    """ This object controls the various equipments used by the bench. 
    It builds and interprets the frames to position the equipments 
    in the configuration required for the measurement requested. 
    The constitution of the frames is based on the informations gived 
    in the configuration file.
    """
    sig_communication_error = Signal(object)

    def __init__(self, cfg_file, parent_windows=None, display_function_connector = None):
        super(CDevicesDriver, self).__init__()
        self.str_error = ""
        self.cfg_file = cfg_file
        self.scpi_relays = None
        self.scpi_aoip = None
        self.scpi_giv4 = None
        self.range = None           # The actual selected range
        self.range_data = None
        self.pw = parent_windows    # optionnal. Provided for debug widget

        # Check connetion with all devices
        try:
            self.scpi_relays = CSerialScpiConnexion(",AGIV", color_cyan)
            if display_function_connector:
                self.scpi_relays.sigRequestComplete.connect(display_function_connector)
                # Force the display of the ID exchange
                self.scpi_relays.sigRequestComplete.emit(
                    'IDN found on {}\n'.format(self.scpi_relays.device_port.name), 
                    self.scpi_relays.id_string, self.scpi_relays.color)
        except ConnectionError:
            self.str_error = "Pas de connexion avec le banc AGIV" #"Can't find AGIV bench"
            #raise ConnectionError(self.str_error)
        try:
            self.scpi_aoip = CSerialScpiConnexion(",CALYS", color_bluepurple)
            if display_function_connector:
                self.scpi_aoip.sigRequestComplete.connect(display_function_connector)
                # Force the display of the ID exchange
                self.scpi_aoip.sigRequestComplete.emit(
                    'IDN found on {}\n'.format(self.scpi_aoip.device_port.name), 
                    self.scpi_aoip.id_string, self.scpi_aoip.color)
        except ConnectionError:
            self.str_error = "Pas de connexion avec l'AOIP."  # "Can't find AOIP device"
            #raise ConnectionError(self.str_error)
        try:
            self.scpi_giv4 = CSerialScpiConnexion(",GIV4", color_red_purple)
            if display_function_connector:
                self.scpi_giv4.sigRequestComplete.connect(display_function_connector)
                # Force the display of the ID exchange
                self.scpi_giv4.sigRequestComplete.emit(
                    'IDN found on {}\n'.format(self.scpi_giv4.device_port.name), 
                    self.scpi_giv4.id_string, self.scpi_giv4.color)
        except ConnectionError:
            self.str_error = "Pas de connexion avec le GIV4."
            #raise ConnectionError(self.str_error)

        self.route_debug_widgets()
        # Go device to remote mode
        if self.scpi_aoip:
            self.scpi_aoip.send_request(":REM")       # AOIP go in REMote mode
        if self.scpi_giv4:
            self.scpi_giv4.send_request(":REM") 

    def stop(self):
        """ Called at the end of the applicatiion """
        if self.scpi_aoip:
            self.scpi_aoip.send_request('LOC')  # Switch to local mode
        if self.scpi_relays:
            self.scpi_relays.send_request(':REL 0')  # Switch off all the relays
        if self.scpi_giv4:
            self.scpi_giv4.send_request('LOC')

    def send_giv_cmde(self, cmde):
        retry = 2
        tx = cmde + ";:MODE?"
        while self.scpi_giv4:   # Don't try if the connection is none
            retry -= 1
            rx = self.scpi_giv4.send_request(tx)
            if rx in cmde:    # Ok
                break
            elif retry == 0:
                raise ConnectionError("Echec de la commande Giv4\n'{}'".format(cmde))

    def send_aoip_range_cmde(self, cmde, wait_time=2.0):
        """ Send a new range selection for AOIP """
        retry = 2
        tx ="*CLS;"+ cmde + ";:ERR?"
        while self.scpi_aoip:  # Don't try if the connection is none
            retry -= 1
            rx = self.scpi_aoip.send_request(tx, wait_time)
            if "No error" in rx:    # Ok
                break
            elif retry == 0:
                raise ConnectionError("Echec de la commande AOIP\n'{}'".format(cmde))

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
        if 'aoip' in measure_on:
            # Output on GIV, measure on Aoip
            if self.scpi_giv4:
                self.scpi_giv4.send_request(giv_out_cmd.format(val))
            time.sleep(aoip_wait_time)  # Wait for measure stabilisation
            rx = self.scpi_aoip.send_request(aoip_meas_cmd) # Get measure
            #rx = self.send_aoip_cmde(aoip_meas_cmd) 
            rx = rx.split(',')[0]   # Keep first element of the AOIP response (eg: '9.999, mA')
        elif 'giv' in measure_on:
            # Output on Aoip mesure on Giv
            self.send_aoip_cmde(aoip_out_cmd.format(val)) 
            time.sleep(giv_wait_time)
            if self.scpi_giv4:
               rx = self.scpi_giv4.send_request(giv_meas_cmd)
        try:
            read_val = float(rx)   
        except ValueError:
            read_val = 0

        return read_val





    def set_bench_relays(self):
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
            self.send_giv_cmde(cmde)
        except ConnectionError as ex:
            self.str_error = str(ex)
            self.sig_communication_error.emit(self.str_error)
        

    def send_debug_rly(self):
        str = self.pw.dbgSendEdit.text()
        self.scpi_relays.send_request(str)

    def send_debug_aoip(self):
        str = self.pw.dbgSendEdit.text()
        self.scpi_aoip.send_request(str)

    def send_debug_giv(self):
        str = self.pw.dbgSendEdit.text()
        self.scpi_giv4.send_request(str)

    def route_debug_widgets(self):
        self.pw.pBtSendRly.clicked.connect(self.send_debug_rly)
        self.pw.pBtSendAoip.clicked.connect(self.send_debug_aoip)
        self.pw.pBtSendGiv.clicked.connect(self.send_debug_giv)
