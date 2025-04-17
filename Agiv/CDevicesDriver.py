# This Python file uses the following encoding: utf-8
""" This module define the CDevicesDriver class that can drive the 3 devices of 
AGIV bench. It could create an instance of this classe, that can be used by the others 
modules to drive the bench. The function get_devices_driver() permits to acces it
as a global variable
10/2024 V3 change: use config file to define the scpi devices properties
11/2024 V3.2 change: register GIV if connected at start time
12/2024 V3.3 change: Possibility to cut the measurement wire automatically or manually with a prompt
"""

from PySide2 import QtCore
from PySide2.QtCore import QTimer
from PySide2.QtGui import QColor
from .CSerialScpiConnexion import *
import re
#import os       # file i/o for debug combobox
from .Utilities import *
from .GivUtilities import *
from .CDBManager import get_database
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

def msg_dialog_unlock():
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Question)
    msg.setText("Le GIV est verouillé. On le déverouille pour l'ajustage ?")
    msg.setWindowTitle("Déverouillage")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    ret = msg.exec_()
    return (ret == QMessageBox.Yes)


class CDevicesDriver(QtCore.QObject):
    """ This object controls the various equipments used by the bench. 
    It builds and interprets the frames to position the equipments 
    in the configuration required for the measurement requested. 
    The constitution of the frames is based on the informations gived 
    in the configuration file.
    """
    sig_communication_error = Signal(object, object, object)

    flg_simulate = False

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
        devices= cfg_file['Devices']
        for (attrib, list_params) in devices.items():
            (idn, strcolor, msg, timeout, baudrate) = list_params
            color = globals()[strcolor]  # Get constant value from this name
            self.get_serial_scpi_connection(attrib, idn, color, msg, timeout, baudrate, print_funct)
        #self.init_combo_debug()

        if self.flg_simulate:
            self.scpi_giv4 = None   # The other function could work with that

        # Go device to remote mode
        if self.scpi_aoip.device_port != None:
            self.send_remote(self.scpi_aoip)       # AOIP go in REMote mode

        if self.scpi_giv4.device_port != None:  # We just found GIV connected at start time
            self.register_new_giv()
            self.check_for_giv_lock()
        # Connect debuging tools 
        #self.route_debug_widgets()

    def get_serial_scpi_connection(self, attrib, idn, color, msg, timeout, baudrate, print_funct):
        scpi = CSerialScpiConnexion(idn, color, timeout, self.flg_simulate, baudrate)
        setattr(self, attrib, scpi) # Store the device in scpi_xxxx 
        scpi_dev = getattr(self,attrib)
        if print_funct is not None:
            self.sig_communication_error.connect(print_funct)
            scpi_dev.sigRequestComplete.connect(print_funct)
            if scpi_dev.device_port != None:
                scpi_dev.sigRequestComplete.emit(
                        'IDN {} found on {}\n{}'.format(idn, 
                        scpi.device_port.name,
                        scpi.id_string), color, SMALL_FONT)
                scpi_dev.strerr = None
            else:
                scpi_dev.strerr = f"Pas de connexion {msg}."
        return scpi
        

    def register_new_giv(self):
        old_giv_id = get_last_giv_id()
        try:
            giv_id = get_giv_id(self.scpi_giv4)
        except:
            return  # No Giv connected Do nothing
        # if the giv_id is changed, register nex Id
        if (giv_id != '' and old_giv_id != giv_id):
            # Get GIV4 S/N and Set log file according to giv identifiant
            #giv_id = get_giv_id(d_drv.scpi_giv4)
            #self.scpi_giv4.send_remote()
            self.send_remote(self.scpi_giv4)
            db = get_database()
            db.register_giv(giv_id)  # The next records link with this GIV
            (giv_date, db_giv_date) = get_giv_caldate(self.scpi_giv4)
            db.register_giv_last_cal_date(db_giv_date, giv_id) # Register the Lock date
            self.pw.lEIdentifiant.textChanged.connect(self.pw.init_log_name)  
            self.pw.lE_DateCalib.setStyleSheet("color: black")
            self.pw.lEIdentifiant.setText(f"{giv_id}")
            self.pw.lE_DateCalib.setText(giv_date)


    def check_for_giv_lock(self):
        # Check if GIV is looked. If Yes, ask to unlock
        giv_lock = is_giv_locked(self.scpi_giv4)
        
        # For debug, we unlock systematiquely
        debug = False
        if debug and giv_lock:
            unlock_giv(self.scpi_giv4)
            giv_lock = False
        if giv_lock:    # If GIV is locked, ask for unlock
            res  = msg_dialog_unlock()
            if res:
                unlock_giv(self.scpi_giv4)
                self.pw.cBoxWriteCal.setChecked(True)   # Show writing capability
            else: # If we keep locked, disable calibration writing capabilitie on HMI
                self.pw.cBoxWriteCal.setChecked(False)

    """ Function to check if the giv is connected or not """
    def check_for_giv(self, print_slot = None):
        if self.scpi_giv4.device_port is None:
            self.scpi_giv4.try_connect()
            # If we find giv on a new port, register it
            if self.scpi_giv4.device_port is not None:
                self.register_new_giv()
                self.check_for_giv_lock()
        else:
            # Check all ports, return true if a used port disapear
            removed = CSerialScpiConnexion.update_awailable_ports()
            if removed:
                self.scpi_giv4.try_connect()  # Check if GIV is still here  
                if self.scpi_giv4.device_port is None:
                    self.pw.lE_DateCalib.setStyleSheet("color: red")
                    self.pw.lE_DateCalib.setText("Giv débranché")
                    reset_last_giv_id()
                    pass 

    def send_remote(self, scpi):
        """ Send remote to the gived scpi """
        cmd= '*CLS;:REM;:SYST:ERR?'
        if scpi==self.scpi_giv4 and self.scpi_giv4:
            self.scpi_giv4.send_request(cmd)
        if scpi==self.scpi_aoip:
            if self.cfg_file['Commands']['aoip_rem']:       # if specific command in config ?
                cmd=self.cfg_file['Commands']['aoip_rem']
            self.scpi_aoip.send_request(cmd)  # Switch to remote mode


    def send_stop_remote(self):
        #self.save_combo_debug()
        """ Called at the end of the applicatiion 
        Send local for all scpi
        """
        cmd= '*CLS;:LOC;:SYST:ERR?'
        if self.scpi_relays:
            self.scpi_relays.send_request(':REL 0; :REL?')  # Switch off all the relays
        if self.scpi_giv4:
            self.scpi_giv4.send_request(cmd)
        if self.scpi_aoip:
            if self.cfg_file['Commands']['aoip_loc']:
                cmd=self.cfg_file['Commands']['aoip_loc']
            self.scpi_aoip.send_request(cmd)  # Switch to local mode

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
        """
        if self.scpi_aoip is None:
            return
        tx = cmde   # cmd must request a confirmation
        if not "*CLS;" in cmde:     # if report not asked, add it to support old protocol
            tx ="*CLS;"+ cmde + ";:ERR?"
        rx = self.scpi_aoip.send_request(tx, wait_time)
        if len(rx)>0 and rx[0] != '0':
            raise ConnectionError("Echec de la commande AOIP\n'{}'".format(cmde))



    def old_send_aoip_range_cmde(self, cmde, wait_time=2.0):
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
            if "No error" in rx or ( "PJ" in self.scpi_aoip.id_string ):    # Ok
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


    """ Pose pour debrancher le fil 3W pendant un certain temps pour assurer la stabilité du couple Calys / Giv """
    def manualcheck_stability(self):
        ok = False
        self.set_bench_relay_3W_disconect()
        self.pw.MsgMThreadDialog( "Est ce que la tension AC sur les bornes COM/V+\n"
                            "est inférieure à 5 mV ?  (YES /NO)\n",
                            "Vérification stabilité")
    """
        while not ok:
            self.set_bench_relay_3W_disconect()
            MsgMThreadDialog()
            ok = msg_dialog_confirm( "Est ce que la tension AC sur les bornes COM/V+\n"
                            "est inférieure à 5 mV ?  (YES /NO)\n",
                            "Vérification stabilité")
    """

    def check_value(self, val, wait_stab = None):
        measure_on = ''
        flg_new_syntax = False
        set_get = []
        rx=''
        read_val = 0.0

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

        # New 05/2024 for Resistor measure by U/I calculation
        read_multiplicator = self.range_data['read_multiplicator'] \
                if 'read_multiplicator' in self.range_data \
                else 1.0

        # Old version: direction of the measure: on Giv or on Aoip
        if 'measure_on' in self.range_data:
            measure_on = self.range_data['measure_on']

        # Nouvelle version d'acces au check_value. Ajouté pour plus de souplesse, notament pour la relecture du GIV
        if  'dialog' in self.range_data :
            flg_new_syntax = True
            set_get = self.range_data['dialog']   # Si dialog, on prend les instructions dans l'ordre du Yaml

        if ('set_val' in self.range_data and 'get_val' in self.range_data):
            flg_new_syntax = True
            set_get = [self.range_data['set_val'], self.range_data['get_val']] # List of set and get instructions

        if flg_new_syntax:    
            for device in set_get:
                feature = device[0].lower()
                scpidev = self.scpi_giv4 if 'GIV4' in device[1] else self.scpi_aoip                
                sendmsg = device[2].replace('{v}',f'{val}') # send message with value insertion
                ackget = device[3].replace('{v}',f'{val}')  # request message with value insertion if necessary
                wait_time = giv_wait_time if scpidev == self.scpi_giv4 else aoip_wait_time
                if len(device)>4:
                    wait_time = device[4]   # Force wait time if it is specified
                retry_ack = 2  if scpidev == self.scpi_giv4 else 4
                rx=''

                if 'set' in feature or 'send' in feature:    # Set reference: we wait only for the acknoledge
                    if scpidev.flg_simulate:
                        continue   # No check for response if simulated

                    while retry_ack>0 and len(rx)==0 and scpidev!=None:  # Don't try if the connection is none
                        retry_ack -= 1
                        rx = scpidev.send_request(sendmsg, 0.5) # 0.5s time-out for response
                        if ackget in rx:    # Ok
                            break
                    
                elif 'get' in feature:  # here, the response contains the measured value
                    if scpidev.flg_simulate:
                        read_val = float(val)+0.001 # simulate a correct value
                        continue   # No check for response if simulated
                    while retry_ack>0 and len(rx)==0 and scpidev!=None:  # Don't try if the connection is none
                        time.sleep(wait_time)  # Wait for measure stabilisation
                        #QTimer.singleShot(wait_time)
                        print(f"Wait {wait_time:03.1f}s for stabilisation")
                        rx = scpidev.send_request(sendmsg, 0.5) # 0.5s time-out for response
                        retry_ack -= 1
                        if len(ackget)>0 and ackget in rx:    # If response required, check that Ok
                            break
                        rx = rx.split(';')[0]  # For AOIP,  keep only the value (eg: '9.999, mA; 'no error')
                        rx = rx.split(',')[0]  # For AOIP,  keep only the value (eg: '9.999, mA')

                if retry_ack == 0:
                    raise ConnectionError(f"Echec de la commande {scpidev.id_string}\n'{sendmsg}'")

        # Version originale: mesure sur GIV->AOIP ou sur AOIP->GIV
        else: 
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
                    if wait_stab is not None and wait_stab == 'question': # Attente validation par l'operateur
                        self.manualcheck_stability()
                    if wait_stab is not None and wait_stab == 'auto': # Debranche rebranche relais seul avant la mesure
                        self.set_bench_relay_3W_disconect()
                    print("Wait {:03.1f}s for stabilisation".format(aoip_wait_time) )
                    time.sleep(aoip_wait_time)  # Wait for measure stabilisation
                    #QTimer.singleShot(aoip_wait_time, None)
                    rx = self.scpi_aoip.send_request(aoip_meas_cmd) # Get measure
                rx = rx.split(',')[0]   # Keep first element of the AOIP response (eg: '9.999, mA')

            #  Output on Aoip mesure on Giv  -------------------
            elif 'giv' in measure_on:
                self.send_aoip_cmde(aoip_out_cmd.format(val)) 
                print("Wait {:03.1f}s for stabilisation".format(giv_wait_time) )
                time.sleep(giv_wait_time)
                #QTimer.singleShot(giv_wait_time)
                if self.scpi_giv4:
                    rx = self.scpi_giv4.send_request(giv_meas_cmd)
                if self.flg_simulate:
                    return float(val)+0.001

        try:
            read_val = float(rx.replace(' ',''))   if len(rx)>0 else 0.0
            read_val *= read_multiplicator  # If a multiplicator is applied
        except ValueError:
            self.sig_communication_error.emit(
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
            
    """ Do not use, PB avec le timer et les thread """
    def set_bench_relay_3W_disconect(self):
        self.wait = True
        (relay_3w, time_3w) = self.range_data['relay_3w']
        rx = self.scpi_relays.send_request(":REL?")
        if len(rx)>0:
            val = int (rx) ^ int(relay_3w)
            self.set_bench_relays(val)  # Open 3W circuit
            # Tentative multithread
            #time.sleep(time_3w)         # wait time
            #self.set_bench_relays()     #restore 3W circuit


    def set_bench_relays(self, value = None ):
        if self.flg_simulate:
            return
        if value:
            relay_cmd = value
        else:
            relay_cmd = 0   # Binary code send to the bench
            relay_cfg = self.range_data['relays']   # The string with hex code to add
            for rly in relay_cfg:
                relay_cmd += rly
        rx = self.scpi_relays.send_request(f":REL {relay_cmd};REL?")
        if len(rx)<=0 or int(rx) != relay_cmd:
            raise ConnectionError("Echec de la Commande des relais.")


    def go_config(self, str_range):
        """ Send frames to position the bench in str_game configuration """
        self.range = str_range   # Note the atual range
        self.range_data = self.cfg_file['Ranges'][str_range]
        aoip_wait_range = self.cfg_file['Commands']['aoip_range_sel_time']

        try:
            # Send commands to the 3 devices
            cmde = self.range_data['giv4']
            self.send_giv_cmde_mode(cmde)
            self.set_bench_relays()
            cmde = self.range_data['aoip']
            self.send_aoip_range_cmde(cmde, aoip_wait_range)
            if 'aoip2' in self.range_data:  # if there are two commands
                cmde = self.range_data['aoip2']
                self.send_aoip_range_cmde(cmde, aoip_wait_range)
        except ConnectionError as ex:
            self.str_error = str(ex)
            #raise(ConnectionError())
            self.sig_communication_error.emit(self.str_error, q_red_color, BIG_FONT)
 

    def get_aoip_datas(self):
        dev_name = ''
        dev_sn = ''
        dev_adj_date = ''
        dev_adj_rep= ''
        if self.scpi_aoip is not None:
            rx = self.scpi_aoip.send_request('*IDN?')
            if rx and len(rx)>0:
                datas = rx.split(',')
                dev_name = datas[1] + '(' + datas[0] + ')'
                dev_sn = datas[2]
            rx = self.scpi_aoip.send_request('CAL:DATE?;:CAL:REP?')
            if rx and len(rx)>0:
                datas = re.split(',|;',rx)
                dev_adj_date = datas[0] + '-' + datas[1] + '-' + datas[2]
                dev_adj_rep = datas[3]
        return(dev_name, dev_sn, dev_adj_date, dev_adj_rep)
    