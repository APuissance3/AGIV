# This Python file uses the following encoding: utf-8
""" 
V3.2: If Z_Factor is set to 0.0, we don't adjust Z, and and instead try to compensate for it at FS point
"""
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

  
    def __init__(self, range_name, range_data, parent=None ) -> None:
        super(CCalibrationValues, self).__init__()
        self.range_name = range_name
        self.range_data = range_data
        self.parent = parent
        self.x = range_data['calibration_points']  #  x coordonates of the calibration points
        # If true, ask for user to check the stability on AC voltmeter
        self.check_stability = range_data['checkstability'] if 'checkstability' in range_data else False 
        self.y = [None] * 2     #  y coordonates readed values for x inputs
        self.res = [None] * 2   #  True if the y measure is in tolerance range
        self.dev_b = 0.0        #  calculated offset of the device near 0 point
        self.dev_a = 0.0        #  calculated gain of the device between 2 points
        self.dev_g = 0.0        #  initial device gain set (readed)
        self.dev_z = 0.0        #  initial device offset (readed)
        self.new_g = 0.0        #  calculated g value to send
        self.new_z = 0.0        #  calculated z value to send 
        self.z_invert = False
        self.z_factor = 1.0     #  Z correction factor used for the resistors. Defined in range_data
        self.zg_reset = False   # If True, we overwrite z=0, G=1 parameters on Giv before correction
        self.checker = CCheckRangePoint(self.range_data) # Checker object permits to validate if ok or not
        self.devices = None     # DevicesDriver is not set at the MainWindow __init__ 
        # Read optionnal z_factor and z_g_overwrite
        if 'z_factor' in range_data:
            self.z_factor = range_data['z_factor']
        if 'z_g_overwrite' in range_data:
            self.zg_reset = bool('z_g_overwrite')
        self.message = None
        self.error = False
        if 'z_invertion' in range_data:
            self.z_invert =  bool('z_invertion')


    def cmd_adjust_param(self, param, value=None):
        """ Set Z or G parameter with the value. Check if it is realy writed
        if parameter given with '?' we only read the value and return it
        """
        logger = get_logger()
        cmd_adj = self.range_data['correction']
        rx = '0.0'
        if '?' in param:  # Only ask for read value
            tx = '{}{}'.format(cmd_adj, param)
            rx = self.devices.scpi_giv4.send_request(tx)
            if len(rx)<= 0: # Evite plantage 
                rx = '0.0'
        else:
            strval = '{:.7f}'.format(value)
            tx = '{}{} {};{}{}?'.format(cmd_adj, param, strval, cmd_adj, param)
            rx = self.devices.scpi_giv4.send_request(tx)
            # Write verification 
            txval = float('{:.6f}'.format(value))   # Giv return only 6 digits 
            if len(rx)<= 0: # Evite plantage 
                rx = '0.0'
            if txval < (float(rx) -0.000001) or txval > (float(rx)+0.000001):
                self.message  = "Error: with {}  tx='{}'  -  rx='{}'".format(param, txval, rx)
                logger.logdata(self.message )
                #pass
                #raise ConnectionError("Can't adjust {} calibration parameters "
                #                        .format(param))
        return(float(rx))


        

    """ Version avec verif manuelle de stabilité fait moins de controle pour éviter trop de perte de temps """
    def exec_calibration_2points_manualcheck(self):
        """ Effectue la calibration en repartant de 0: Init Z=0 ainsi que G=1 si coché """
        logger = get_logger()
        checker = CCheckRangePoint(self.range_data) # Checker object
        print (f"************** Range:  {self.range_name}  *****************")
        # supprimé en manual check  - 
        # self.check_calibration('Lecture initiale') # Lecture des parametres d'ajustement et des points d'étalonnage
        # 4 lignes dessous Fait dans self.check_calibration() en temps normal 
        self.devices = get_devices_driver() 
        logger.log_operation(f'Check range "{self.range_name}"')
        self.devices.go_config(self.range_name)
        self.parent.sig_register_range.emit(self.range_name)

        # On réinitialise Z à 0 dans tous les cas
        self.sig_CCalibVal_Message.emit("Init reglage Z=0.0", q_green_color, INFO_FONT )
        self.cmd_adjust_param('Z', 0)
        self.dev_z = 0.0
        self.sig_CCalibVal_Message.emit("Init reglage G = 1.0", q_green_color, INFO_FONT )
        self.cmd_adjust_param('G', 1.0)
        self.dev_g = 1.0
        self.sig_CCalibVal_Message.emit("Mesure des nouveaux points 0 et FS", q_green_color, INFO_FONT )
        self.y[0] = self.devices.check_value(self.x[0], True)  # Control the point x0,y0
        self.y[1] = self.devices.check_value(self.x[1], True)  # Control the point x1,y1
        self.dev_a = (self.y[1] - self.y[0]) / (self.x[1]-self.x[0])
        self.sig_CCalibVal_Message.emit("Ajustage reglage G ", q_green_color, INFO_FONT )
        self.new_z =0.0
        # Check abnormal value
        if self.dev_a > 1.2 or self.dev_a < 0.8:
            self.error = True
            self.message = 'Find abnormal g value: {}'.format(self.new_g)
        else:
            self.new_g = self.dev_g  / self.dev_a
            self.cmd_adjust_param('G', self.new_g)
            print (f"Set G= {self.new_g}")
            logger.logdata(f'Set G= {self.new_g}\n')
            logger.logdata(f'Keep Z= 0.0\n')
        # Le gain est rectifié, on lit le zéro avec ce nouveau gain
        self.y[0] = self.devices.check_value(self.x[0], True)  # Reload y0 with the new G
        (self.res[0], min, max) = checker.check_val( self.x[0] , self.y[0]) # result for Z
        self.y[1] = self.devices.check_value(self.x[1], True)  # Reload y1 with the new G
        (self.res[1], min, max) = checker.check_val( self.x[1] , self.y[1]) # result for FS
        logger.logdata('Nouvelles valeurs avec correction de G:\n')
        logger.logdata('  Y0= {: 9.6f}  Y1= {:> 9.6f}\n'.format(self.y[0], self.y[1]))
        self.parent.sig_register_value.emit(self.new_z, self.new_g, True) # Register write values
        # supprimé en manual check  - 
        # self.check_calibration("Valeurs finales")
        ok = msg_dialog_info("Débranchez le voltmètre AC\n"
                "si vous avez fini les ajustages 4500R\n",
                "Modification câblage")



    def exec_calibration(self):
        if self.check_stability:
            self.exec_calibration_2points_manualcheck()
        else: 
            self.exec_calibration_2points()


    def exec_calibration_2points(self):
        clear_calib = False  # Verrue pour reset des calibrations
        dbg_xz = 1.0
        dbg_xfs = 1.0
        """ Effectue la calibration en repartant de 0: Init Z=0 ainsi que G=1 si coché """
        logger = get_logger()
        print (f"************** Range:  {self.range_name}  *****************")
        self.check_calibration('Lecture initiale') # Lecture des parametres d'ajustement et des points d'étalonnage
        # Probleme avec le zero: on réinitialise dans tous les cas
        self.sig_CCalibVal_Message.emit("Init reglage Z=0.0", q_green_color, INFO_FONT )
        self.cmd_adjust_param('Z', 0)
        self.dev_z = 0.0

        zeroize = get_zeroize_cBox()
        if zeroize:
            self.sig_CCalibVal_Message.emit("Init reglage G = 1.0", q_green_color, INFO_FONT )
            self.cmd_adjust_param('G', 1.0)
            return


        # if cBox zg_reset we force the parameters G=1 
        self.zg_reset |= get_overwrite_cBox() 

        if self.zg_reset:
            self.sig_CCalibVal_Message.emit("Init reglage G = 1.0", q_green_color, INFO_FONT )
            self.cmd_adjust_param('G', 1.0)
            self.dev_g = 1.0
            self.sig_CCalibVal_Message.emit("Mesure des nouveaux points 0 et FS", q_green_color, INFO_FONT )
            self.y[0] = self.devices.check_value(self.x[0])  # Control the point x0,y0
            self.y[1] = self.devices.check_value(self.x[1])  # Control the point x1,y1
            self.dev_a = (self.y[1] - self.y[0]) / (self.x[1]-self.x[0])
            # If we can't adjust Z, we try to correct it at FS point (we cheat on dev_a value)
            if self.z_factor == 0.0:  # Can't adjust Z
                self.sig_CCalibVal_Message.emit("Ajustage reglage G seulement", q_green_color, INFO_FONT )
                self.dev_a = self.y[1] / self.x[1]
            else:  # In nomal operation mode, we adjust dev_a with the 2 points Z ans FS            
                self.dev_a = (self.y[1] - self.y[0]) / (self.x[1]-self.x[0])
                self.sig_CCalibVal_Message.emit("Ajustage reglage G et Z", q_green_color, INFO_FONT )
            # Check abnormal value
            if self.dev_a > 1.2 or self.dev_a < 0.8:
                self.error = True
                self.message = 'Find abnormal g value: {}'.format(self.new_g)
            else:
                self.new_g = self.dev_g  / self.dev_a
                if clear_calib:    ###  DBG Reset calib usine
                    self.new_g = 1.0 
                self.cmd_adjust_param('G', self.new_g)
                print (f"Set G= {self.new_g}")
                logger.logdata(f'Set G= {self.new_g}\n')

        # Probleme avec l'ajustage d'offset. Dans tous les cas, on repart avec un Z à 0
        #self.cmd_adjust_param('Z', 0.0)
        #self.dev_z = 0.0

        # Le gain est rectifié, on cherche a ajuster le zéro avec ce nouveau gain
        self.y[0] = self.devices.check_value(self.x[0])  # Reload y0 with the new G
        self.y[1] = self.devices.check_value(self.x[1])  # Reload y1 with the new G
        logger.logdata('Nouvelles valeurs avec correction de G:\n')
        logger.logdata('  Y0= {: 9.6f}  Y1= {:> 9.6f}\n'.format(self.y[0], self.y[1]))
        """
        Annulé: le zero s'ajuste exclusivement avec le point 0
        # modification du 08/2023: On ajuste le 0 avec la moyenne des deux points et le nouveau gain
        #self.dev_b = -(((self.y[0] - self.x[0]) + (self.y[1] - self.x[1]))/2)  # Test 31/08: Inversion signe de correction
        """
        """
        # Petit doute: inversion sens de correction du Z   - self.new_z = self.dev_z - (self.dev_b / self.z_factor)
        #self.new_z = -((self.dev_b / -self.z_factor) - self.dev_z)  # Pour les resistances, le Z n'est pas direct
        """
        self.dev_b = -(self.y[0] - self.x[0])

        if self.z_factor != 0.0:  # if z_factor is set to  0.0, don't touch to Z (GIV R03 to R04 can't set it properly)
            self.new_z = (self.dev_b / self.z_factor) - self.dev_z  # Pour les resistances, le Z n'est pas direct
            if clear_calib:    ###  DBG Reset calib usine
                self.new_z = 0.0
            #self.new_z *= dbg_xz
            self.cmd_adjust_param('Z', self.new_z)
            print (f"Set Z= {self.new_z}")
            logger.logdata(f'Set Z ={self.new_z}')
        else: # The Z factor is set to 0, so we dont adjust Z, and we try to adjut Z with G at FS point
            self.new_z = 0.0
            logger.logdata(f'Z not set ')
        self.parent.sig_register_value.emit(self.new_z, self.new_g, True) # Register write values
        self.check_calibration("Valeurs finales")

    def check_calibration(self,msg=''):
        """ Lecture des reglages Z et G et controle des valeurs aux points de reglage """
        logger = get_logger()
        self.devices = get_devices_driver() # Used also by the other methods
        #self.message = None
        logger.log_operation(f'Check range "{self.range_name}" {msg}')
        self.devices.go_config(self.range_name)
        self.parent.sig_register_range.emit(self.range_name)

        # Adjustement is not awailable for this range
        if not 'none' in self.range_data['correction'].lower():   
            self.sig_CCalibVal_Message.emit("Lecture reglages G et Z", q_green_color, INFO_FONT )
            self.dev_z = self.cmd_adjust_param('Z?')
            self.dev_g = self.cmd_adjust_param('G?')
            self.parent.sig_register_value.emit(self.dev_z, self.dev_g, False) # Register read values
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

    def report_calibration(self, message = None):
        logger = get_logger()
        if message != None:
            logger.logdata(message)
        # fs = self.range_data['full_scale']
        logger.logdata('  X0= {: 9.6f}  X1= {:> 9.6f}\n'.format(self.x[0], self.x[1]))
        logger.logdata('  Y0= {: 9.6f}  Y1= {:> 9.6f}\n'.format(self.y[0], self.y[1]))
        logger.logdata('giv_g=  {: 8.6f} , giv_z=  {:+8.6f}\n'.format(self.dev_g, self.dev_z))
        logger.logdata('calc_g= {: 8.6f} , calc_z= {:+8.6f}\n'.format(self.dev_a, self.dev_b))
        if self.message is not None:
            logger.logdata(self.message)



