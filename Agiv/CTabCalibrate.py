# This Python file uses the following encoding: utf-8

#from PySide2 import QtWidget
from PySide2 import QtCore

import os, sys,pathlib

from .CDevicesDriver import get_devices_driver
from .Utilities import *
#from CDevicesDriver import CDevicesDriver
from .CConfigFile import get_config_file, get_config_ranges
from PySide2.QtCore import Signal, Slot, QThread, QObject
from .CRangeStatusLayout import CRangeStatusLayout
from .CCheckRangePoint import CCheckRangePoint
from .CLogger import get_logger

from .GivUtilities import lock_giv
from .CDBManager import get_database
from .XlsReportGenerator import set_xls_flg_last_day_only, set_xls_flg_last_meas_only 
from .CCalibrateTab import *


class CTabCalibrate(QThread):
    """ This class add items to manage the calibration tab (panel) 
    It is provided to extend the Main Window Application,
    and use the self.config and self.devices initialised by MainWindow
    As MainWindow inherit of us, self contains all attributes of MainWindow
    """
    # This signal is emited to display messages 
    # argument: message, color, font
    sig_info_message = Signal(object, object, object)
    sig_register_range = Signal(object)
    sig_register_value = Signal(object,object,object)
    # Signal for CmeasuresTab to run the measure process after calibration
    sig_run_measure = Signal(object)


    def __init__(self, parent =None):
        super(CTabCalibrate, self).__init__(parent)        # Init QThread
        self.phmi = parent
        self.vCalibrateLayout = None  # Initialised later with the scrolling zone
        self.vCalibrateLayout = createVLayerForScroll(self.phmi.scrollCalibrate)
        self.cal_range_list = []
        self.running = False
        self.run_measures = False
        
        # Hide Lock button: Lock is automatic if all the ranges are ok
        self.phmi.pBtLockGiv.setVisible(False)  

        # Read our ranges data and fill ranges layer      
        self.cfg_ranges = get_config_ranges()
        for range, range_data in self.cfg_ranges.items():
            # Check for 'active' and 'calibrate' key if exist
            if 'active' in range_data and range_data['active']:
                if 'calibrate' in range_data and range_data['calibrate']:
                    cal_view = CRangeStatusLayout(range, range_data, self.phmi)    # Create the object
                    self.vCalibrateLayout.addLayout(cal_view.hLayout)
                    # cal_values is the two point of calibration and methods to calibrate
                    cal_values = CCalibrationValues( range, range_data, self)
                    cal_values.sig_CCalibVal_Message.connect(parent.Qmessages_print)
                    # We append in the list the Hlayer and the associated calibration points
                    self.cal_range_list.append((cal_view, cal_values))


        self.phmi.pBtSelectAll.clicked.connect(self.select_all_range)
        self.phmi.pBtUnselectAll.clicked.connect(self.unselec_all_range)
        self.phmi.pBtRunCalibration.clicked.connect(self.pBt_run_clicked)
        self.phmi.pBtLockGiv.clicked.connect(self.lock_giv)
        self.select_all_range()

        # Repport format checkbox connetion and initialisation to actual value
        self.phmi.cBoxLastDate.toggled.connect(self.cBoxLastDateToggled)
        self.cBoxLastDateToggled() # Set value to actual state
        self.phmi.cBoxLastSequence.toggled.connect(self.cBoxLastSequenceToggled)
        self.cBoxLastSequenceToggled()
        self.phmi.cBoxRunMeasures.toggled.connect(self.cBoxRunMeasuresToggled)
        self.cBoxRunMeasuresToggled()
    
    def cBoxRunMeasuresToggled(self):
        self.run_measures = self.phmi.cBoxRunMeasures.isChecked()

    def cBoxLastDateToggled(self):
        set_xls_flg_last_day_only(not self.phmi.cBoxLastDate.isChecked())

    def cBoxLastSequenceToggled(self):
        set_xls_flg_last_meas_only(not self.phmi.cBoxLastSequence.isChecked())

    """ Button Select All """
    def select_all_range(self):
        for (cal_view, cal_values) in self.cal_range_list:
            cal_view.cBoxSel.setChecked(True)

    """ Button Unselect All """
    def unselec_all_range(self):
        for (cal_view, cal_values) in self.cal_range_list:
            cal_view.cBoxSel.setChecked(False)    

    """ Button Start Adjust """
    def pBt_run_clicked(self):
        if not self.running:        # Can start or stop the process 
            self.running = True     # Here we start 
            self.phmi.pBtRunCalibration.setText("ARRET AJUSTAGE")
            print ("\n\n ------------- Debut calibration  -----------------")
            db = get_database()
            db.register_now_cal_date()  # Add this date to DB
            if self.phmi.cBoxMultithread.isChecked():
                self.start()      # Start the run method in another thread
            else:
                self.run()        # For debuging, we could run in the main thread
        else:
            self.terminate()        # Here we stop 
            self.wait()
            self.sig_info_message.emit("Ajustage interrompu par l'utilisateur", q_red_color, None)
            self.end_of_calibration()

    def end_of_calibration(self):
        all_ok = True
        an_error = False
        self.running = False
        self.phmi.pBtRunCalibration.setText("LANCER AJUSTAGE")
        # Check all calibrations status
        for (cal_view, cal_values) in self.cal_range_list:
            if cal_view.cal_status != True:
                all_ok = False  # Not all calibration are ok
            if cal_view.cal_status == False:
                an_error = True # At least a calibration not passed
        print("All ok: {}".format(all_ok))
        if all_ok:
            self.sig_info_message.emit("Ajustage terminé ok. Verouillage du GIV",
                    q_orange_color, None)
            self.lock_giv()
        if not an_error:
            # Here, we look for running the measures after the calibration
            if self.run_measures:
                # Appelle le signal slot_run_measure_after_calibration()
                #self.slot_run_measure_after_calibration.emit("Fin calibration") # Continue en effectuant un relevé de mesures
                self.sig_run_measure.emit("Fin calibration") # Continue en effectuant un relevé de mesures
            else:
                play_success() # If no measure required, advertise success
        else: # Averti si echec
            play_echec()

  

    def lock_giv(self):
        giv_scpi = get_devices_driver().scpi_giv4
        rx = lock_giv(giv_scpi)
        print(rx)


    def run(self):
        """ Thread run overload method """
        # First, Raz calibration status
        for (cal_view, cal_values) in self.cal_range_list:
            if cal_view.cBoxSel.isChecked():
                cal_view.cal_status = None

        for (cal_view, cal_values) in self.cal_range_list:
            if cal_view.cBoxSel.isChecked():
                # Check if there is correction parameters or not
                # depuis cette modif, plantage CDevicesDrivers:147
                cal_can_write = not 'none' in \
                    cal_values.range_data['correction'].lower() 

                if cal_can_write and self.phmi.cBoxWriteCal.isChecked():
                    txt_info = "Calibration '{}'".format(cal_view.range_name)
                    self.sig_info_message.emit(txt_info, q_green_color, NORMAL_FONT)
                    cal_values.message = None  # Raz error messages
                    cal_values.exec_calibration()
                else:
                    txt_info = "Controle '{}'".format(cal_values.range_name)
                    self.sig_info_message.emit(txt_info, q_green_color, NORMAL_FONT)
                    cal_values.check_calibration()
                # At the end, decide if the status is ok or not
                cal_view.cal_status = cal_values.res[0] and cal_values.res[1]

        self.sig_info_message.emit( "Fin process de calibration", q_green_color, NORMAL_FONT)
        self.end_of_calibration()
