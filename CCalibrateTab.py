# This Python file uses the following encoding: utf-8

#from PySide2 import QtWidget
from PySide2 import QtCore

from CDevicesDriver import get_devices_driver
from Utilities import *
#from CDevicesDriver import CDevicesDriver
from CConfigFile import get_config_file, get_config_ranges
from PySide2.QtCore import Signal, Slot, QThread, QObject
from CRangeStatusLayout import CRangeStatusLayout
from CCheckRangePoint import CCheckRangePoint
from GlobalVar import logger
from GivUtilities import lock_giv


# If True: measure Z two time, more long but more shure
# if False: Z adjusted only by calculation of the 2 first measures
z_measured_twice = True     # Z ajustement with one or two measure for Z

class CCalibrationValues(QObject):
    """ 
    This class contains attributes to calculate the optimum gain and offset 
    for a range. It is created only to separate mathematical data and Qt object
    """
    # Same name as child class
    sig_CCalibVal_Message = Signal(object, object, object)
  
    def __init__(self, range_name, range_data, flg_overwrite, parent=None ) -> None:
        super(CCalibrationValues, self).__init__()
        self.range_name = range_name
        self.range_data = range_data
        self.x = range_data['calibration_points']  #  x coordonates of the calibration points
        self.y = [None] * 2     #  y coordonates readed values for x inputs
        self.res = [None] * 2   #  True if the y measure is in tolerance range
        self.dev_b = 0.0        #  calculated offset of the device near 0 point
        self.dev_a = 0.0        #  calculated gain of the device between 2 points
        self.dev_g = 0.0        #  initial device gain set (readed)
        self.dev_z = 0.0        #  initial device offset (readed)
        self.new_g = 0.0        #  calculated g value to send
        self.new_z = 0.0        #  calculated z value to send 
        self.z_factor = 1.0     #  Z correction factor used for the resistors. Defined in range_data
        self.zg_reset = False   # If True, we overwrite z=0, G=1 parameters on Giv before correction
        self.checker = CCheckRangePoint(self.range_data) # Checker object permits to validate if ok or not
        self.devices = None     # DevicesDriver is not set at the MainWindow __init__ 
        # Read optionnal z_factor and z_g_overwrite
        if 'z_factor' in range_data:
            self.z_factor = range_data['z_factor']
        if 'z_g_overwrite' in range_data:
            self.zg_reset = 'z_g_overwrite'
        if flg_overwrite:
            self.zg_reset = True
        self.message = None
        self.error = False

    def cmd_adjust_param(self, param, value=None):
        """ Set Z or G parameter with the value. Check if it is realy writed
        if parameter given with '?' we only read the value and return it
        """
        cmd_adj = self.range_data['correction']
        rx = '0.0'
        if '?' in param:  # Only ask for read value
            tx = '{}{}'.format(cmd_adj, param)
            rx = self.devices.scpi_giv4.send_request(tx)
        else:
            strval = '{:.7f}'.format(value)
            tx = '{}{} {};{}{}?'.format(cmd_adj, param, strval, cmd_adj, param)
            rx = self.devices.scpi_giv4.send_request(tx)
            # Write verification 
            txval = float('{:.6f}'.format(value))   # Giv return only 6 digits 
            if txval < (float(rx) -0.000001) or txval > (float(rx)+0.000001):
                self.message  = "Error: with {}  tx='{}'  -  rx='{}'".format(param, txval, rx)
                logger.logdata(self.message )
                #pass
                #raise ConnectionError("Can't adjust {} calibration parameters "
                #                        .format(param))
        return(float(rx))

    def exec_calibration(self):
        self.check_calibration()
        # if zg_reset we force the parameters G=1 and Z=0
        if self.zg_reset:
            self.sig_CCalibVal_Message.emit("Init reglages G et Z", q_green_color, INFO_FONT )
            self.cmd_adjust_param('Z', 0.0)
            self.dev_z = 0.0
            self.cmd_adjust_param('G', 1.0)
            self.dev_g = 1.0
            self.sig_CCalibVal_Message.emit("Mesure des nouveaux points 0 et FS", q_green_color, INFO_FONT )
            self.y[0] = self.devices.check_value(self.x[0])  # Control the point x0,y0
            self.y[1] = self.devices.check_value(self.x[1])  # Control the point x1,y1
        self.dev_a = (self.y[1] - self.y[0]) / (self.x[1]-self.x[0])
        self.sig_CCalibVal_Message.emit("Ajustage reglage G et Z", q_green_color, INFO_FONT )
        # Check abnormal value
        if self.dev_a > 1.2 or self.dev_a < 0.8:
            self.error = True
            self.message = 'Find abnormal g value: {}'.format(self.new_g)
        else:
            self.new_g = self.dev_g  / self.dev_a
            self.cmd_adjust_param('G', self.new_g)
        self.y[0] = self.devices.check_value(self.x[0])  # Reload y0 with the new G
        self.dev_b = self.y[0] - self.x[0]
        self.new_z = self.dev_z - ((self.y[0] - self.x[0]) / self.z_factor)
        self.cmd_adjust_param('Z', self.new_z)
        self.check_calibration()

    def check_calibration(self):
        self.devices = get_devices_driver() # USed also by the other methods
        #self.message = None
        logger.log_operation('Check range "{}"'.format(self.range_name))
        self.devices.go_config(self.range_name)

        # Adjustement is not awailable for this range
        if not 'none' in self.range_data['correction'].lower():   
            self.sig_CCalibVal_Message.emit("Lecture reglages G et Z", q_green_color, INFO_FONT )
            self.dev_z = self.cmd_adjust_param('Z?')
            self.dev_g = self.cmd_adjust_param('G?')
        else:
            self.dev_z = 0.0 ;  self.dev_g = 1.0
            
        if self.checker is None:
            self.checker = CCheckRangePoint(self.range_data) # Checker object
        self.sig_CCalibVal_Message.emit( "Mesure des points 0 et FS", q_green_color,INFO_FONT )
        for i in range (2): # for 0 and 1
            self.y[i] = self.devices.check_value(self.x[i])  # Control the point on the calibrator device
            (self.res[i], min, max) = self.checker.check_val( self.x[i] , self.y[i])
        if self.y[1]> 2*self.x[1]:  # Prevent AOIP bug 
            self.message = "Mesure incohérente: ajout d'une borne de sécurité"
            print (self.message)
            self.sig_CCalibVal_Message.emit(self.message, q_red_color, BIG_FONT )
            self.y[1] = 2*self.x[1]
        self.report_calibration()

    def report_calibration(self):
        logger.logdata('  X0= {: 9.6f}  X1= {:> 9.6f}\n'.format(self.x[0], self.x[1]))
        logger.logdata('  Y0= {: 9.6f}  Y1= {:> 9.6f}\n'.format(self.y[0], self.y[1]))
        logger.logdata('giv_g=  {: 8.6f} , giv_z=  {:+8.6f}\n'.format(self.dev_g, self.dev_z))
        #logger.logdata('calc_g= {: 8.6f} , calc_z= {:+8.6f}\n'.format(self.dev_a, self.dev_b))
        if self.message is not None:
            logger.logdata(self.message)



class CCalibrateTab(QThread):
    """ This class add items to manage the calibration tab (panel) 
    It is provided to extend the Main Window Application,
    and use the self.config and self.devices initialised by MainWindow
    As MainWindow inherit of us, self contains all attributes of MainWindow
    """
    # This signal is emited to display messages 
    # argument: message, color, font
    sig_info_message = Signal(object, object, object)


    def __init__(self, parent =None):
        super(CCalibrateTab, self).__init__(parent)        # Init QThread
        self.phmi = parent
        self.vCalibrateLayout = None  # Initialised later with the scrolling zone
        self.vCalibrateLayout = createVLayerForScroll(self.phmi.scrollCalibrate)
        self.cal_range_list = []
        self.running = False
        
        # Hide Lock button: Lock is automatic if all the ranges are ok
        self.phmi.pBtLockGiv.setVisible(False)  

        flg_overwrite = True if parent.cBoxRazCalib.isChecked() else False

        # Read our ranges data and fill ranges layer      
        self.cfg_ranges = get_config_ranges()
        for range, range_data in self.cfg_ranges.items():
            # Check for 'active' and 'calibrate' key if exist
            if 'active' in range_data and range_data['active']:
                if 'calibrate' in range_data and range_data['calibrate']:
                    cal_view = CRangeStatusLayout(range, range_data, self.phmi)    # Create the object
                    self.vCalibrateLayout.addLayout(cal_view.hLayout)
                    # cal_values is the two point of calibration and methods to calibrate
                    cal_values = CCalibrationValues( range, range_data, flg_overwrite)
                    cal_values.sig_CCalibVal_Message.connect(parent.Qmessages_print)
                    # We append in the list the Hlayer and the associated calibration points
                    self.cal_range_list.append((cal_view, cal_values))


        self.phmi.pBtSelectAll.clicked.connect(self.select_all_range)
        self.phmi.pBtUnselectAll.clicked.connect(self.unselec_all_range)
        self.phmi.pBtRunCalibration.clicked.connect(self.pBt_run_clicked)
        self.phmi.pBtLockGiv.clicked.connect(self.lock_giv)
        self.select_all_range()


    def select_all_range(self):
        for (cal_view, cal_values) in self.cal_range_list:
            cal_view.cBoxSel.setChecked(True)


    def unselec_all_range(self):
        for (cal_view, cal_values) in self.cal_range_list:
            cal_view.cBoxSel.setChecked(False)    

    def pBt_run_clicked(self):
        if not self.running:
            self.running = True
            self.phmi.pBtRunCalibration.setText("ARRET AJUSTAGE")
            if self.phmi.cBoxMultithread.isChecked():
                self.start()      # Start the run method in another thread
            else:
                self.run()        # For debuging, we could run in the main thread
        else:
            self.terminate()
            self.wait()
            self.sig_info_message.emit("Ajustage interrompu par l'utilisateur", q_red_color, None)
            self.end_of_calibration()

    def end_of_calibration(self):
        all_ok = True
        self.running = False
        self.phmi.pBtRunCalibration.setText("LANCER AJUSTAGE")
        for (cal_view, cal_values) in self.cal_range_list:
            if cal_view.cal_status != True:
                all_ok = False
                break
        print("All ok: {}".format(all_ok))
        if all_ok:
            self.sig_info_message.emit("Ajustage terminé ok. Verouillage du GIV",
                    q_orange_color, None)

  
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
