# This Python file uses the following encoding: utf-8
# to convert ui file: 
# pyside2-uic MainWindow.ui -o MainWindow.py
# Note: Résolution machine virtuelle: 1364 x 671
# Evolution du 22/01/2024 (retourche requette dans CDBManager)
# Note: Point d'entré du module: main() en fin de fichier, qui appelle start_module_application()

# V2.1 du 28/05/2024:
# Modification syntaxe du fichier Bench_config pour pouvoir lire les mesures moyennées du Calys




from PySide2.QtWidgets import QApplication, QMessageBox
from PySide2 import QtWidgets
from PySide2 import QtCore
import os, sys
from pathlib import Path

# Our classes 
from .MainWindow import Ui_MainWindow
from .CTabAvanced import CTabAvanced
from .CTabCalibrate import CTabCalibrate
from .CTabMeasures import CTabMeasures
from .CDevicesDriver import CDevicesDriver, create_devices_driver, get_devices_driver
from .CConfigFile import CConfigFile, create_config_file_instance, get_config_file
from .Utilities import *
from .GivUtilities import *
from .CDBManager import  initialise_database
from .CLogger import create_logger, get_logger
from .XlsReportGenerator import set_xls_flg_last_day_only, set_xls_flg_last_meas_only 


class MainWindow(QtWidgets.QMainWindow, 
                #Ui_MainWindow, CMeasuresTab, CCalibrateTab):
                Ui_MainWindow):
    """ Cette classe herite de UI_MainWindow qui represente la boite de dialogue 
    principale
    CMeasureTab and CCalibrateTab contains items to manage the measure and calibration panels
    """

    # This signal could be used by the childreen thread to display messages in main display
    #sig_Uppdate_Qmessages = Signal(object, object)


    def __init__(self):
        super(MainWindow, self).__init__()

        self.setupUi(self)
        self.QTextConsole.setFontPointSize(NORMAL_FONT)
        self.QTextConsole.show()    # To display initialisation errors 
        self.config  = get_config_file()   # The config loaded from the yaml file
 
        self.label_Titre.setText(self.config['Titre'])

        self.cm_tab = CTabMeasures(self)
        self.cc_tab = CTabCalibrate(self)    
        self.ctab_avanced = CTabAvanced(self)

        self.cm_tab.sig_info_message.connect(self.Qmessages_print) # Connect signals info_message to our print function
        self.cc_tab.sig_info_message.connect(self.Qmessages_print)

        self.cc_tab.sig_run_measure.connect(self.cm_tab.slot_run_measure_after_calibration) # Start measure process after calibration

        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, False) 
        self.setFixedSize(self.size()) # Disable resizing
        
        # Connecting information message from other tthread to the QTextConsole
        self.cBoxAdvanced.stateChanged.connect(self.change_advanced_mode)

    def init_log_name(self, str):
        log = get_logger()
        logfilename = get_Agiv_dir(get_config_file()["Options"]) + '\\' + 'log_'+ str + '.txt'
        log.log_change_name(logfilename)
        #xls_file.set_filename('Report_'+str+'.xlsx')


    def Qmessages_print(self, message, 
            color=QColor('black') , font=NORMAL_FONT):
        if color is not None:
            self.QTextConsole.setTextColor(color)
        if font is not None:
            self.QTextConsole.setFontPointSize(font)
        self.QTextConsole.append(message)

    def Qmessage_sscpi_print(self, message, color=None, font=INFO_FONT):
        if not self.cBoxAdvanced.isChecked():
            return
        self.Qmessages_print(message, color, font)



    def display_error(self, str_err=None):
        """ Print red message in large charaters on the TextConsole """
        if str_err is not None:
            self.Qmessages_print(str_err, q_red_color, BIG_FONT)

    def disable_MainWindow_with_error(self, str_err=None):
        """ This function used to disable the HMI if the bench initialisation fail """
        self.display_error(str_err)

    def change_advanced_mode(self):
        if self.cBoxAdvanced.isChecked():
            self.cBoxMultithread.show()
            self.cBoxWriteCal.setEnabled(True)
            self.cBoxRazCalib.setEnabled(True)
            self.cm_tab.unselec_all_range()
            self.cc_tab.unselec_all_range()
        else:
            self.cBoxMultithread.hide()
            # self.cBoxWriteCal.setChecked(True)
            self.cBoxWriteCal.setEnabled(False)
            self.cBoxRazCalib.setEnabled(False)
            self.cBoxRazCalib.setChecked(True)
            self.ZeroiseCalib.hide()

        self.cBoxMultithread.setChecked(False)  # Force monotache (le mutithread ne fonctionne pas avec les nouvelles modifications)



    def force_unlock_giv(self):
        self.Qmessages_print("Déverrouillage du GIV par l'utilisateur", q_orange_color)
        d_drv= get_devices_driver()
        unlock_giv(d_drv.scpi_giv4)

    def force_lock_giv(self):
        if msg_dialog_confirm("Etes-vous sur de vouloir verouiller la calibration du  GIV ?",
             "Verouillage") == True:
            self.Qmessages_print("Verrouillage du GIV par l'utilisateur", q_orange_color)
            d_drv= get_devices_driver()
            lock_giv(d_drv.scpi_giv4)


# --------  End of MainWindow definition -----------------------


def apply_style(app, style_fname):
   if style_fname is not None:
        StyleFile =  QtCore.QFile(style_fname)
        if not StyleFile.open( QtCore.QFile.ReadOnly | QtCore.QFile.Text):
            print( "Error opening "+ style_fname)
            return
        qss = QtCore.QTextStream(StyleFile)
        #setup stylesheet
        app.setStyleSheet(qss.readAll())


bench_version = "A Puissance 3 - AGIV V3.3 ELA 12/2024"

def print_start_options():
    print(f"AGIV_BENCH version: {bench_version}")
    print ("options:")
    print ("-cfg=<filename>  : choose specific configuration file (benchconfig.yaml by default)")
    print ("-adv             : enable advanced box")
    print ("-safe            : disable advanced box and advanced tab")

def check_start_options():
    """ Check arguments to choose config file and overide config options """
    cfg = None
    adv = False
    safe = False
    argv = sys.argv
    for option in argv:
        if "?" in option:
            print_start_options()
        if "-cfg=" in option:
            cfg = option[5:]
        if "-adv" in option:
            adv = True
        if "-safe" in option:
            save = True
    return(cfg,adv,safe)

def start_module_application():

    print("Start module application")
    app = QApplication([])
    (optcfg, optadv, optsafe) = check_start_options()
    cfg_object = create_config_file_instance(optcfg)   # Read config file and create an instance
    if cfg_object.config == None: # There is an error in config file
        msg_dialog_Error("Chargement du fichier de configuration impossible.",
            "Vérifier la présence et la cohérence de benchconfig.yaml",
            cfg_object.strerr)
        sys.exit(1)

    db = initialise_database("etalonnage")

    AppMW = MainWindow()
    AppMW.setWindowTitle(bench_version)
    set_main_window(AppMW)

    #Enable for Debug by default
    #AppMW.cBoxAdvanced.setChecked(False)

    #Enable or disable advanced Tab function og advanced flag in the config file
    options= cfg_object.config['Options']
    enable_avanced_tab = options['advanced_tab']
    enable_avanced_box = options['advanced_box']
    # starting arguments overide config file
    if optsafe:
        enable_avanced_tab= False
        enable_avanced_box= False
    elif optadv:
        enable_avanced_tab= True
        enable_avanced_box= True

    if not enable_avanced_tab:
        AppMW.cBoxAdvanced.setChecked(False)

    AppMW.tabWidget.setTabEnabled(2, enable_avanced_tab)
    AppMW.cBoxAdvanced.setChecked(enable_avanced_box)
    AppMW.change_advanced_mode()

    # Tente de modifier le chemin des rapports si disque réseau disponible
    repport_dir = get_Agiv_dir(options)   # Chemin local par defaut
    try:
        os.mkdir(repport_dir)
        print(f"Sauvegardes des rapports sous {repport_dir}")
    except Exception as ex:
        pass

    log = create_logger() # The log name will be set with init_log_name()


    
    # For debug, only one thred
    #AppMW.cBoxMultithread.setChecked(False)

    #  Apply stylesheet file to the MainWindow 
    path = os.path.abspath(__file__)
    fullname = os.path.join(os.path.dirname(path), "Qt_Style.qrc") 
   
    apply_style(AppMW, fullname )

    # Connect Signal to DB: The DB usage is only in one thread
    # so we use signals to register values in main thread
    AppMW.cm_tab.sig_register_range.connect(db.register_range)
    AppMW.cm_tab.sig_register_value.connect(db.register_measure)
    AppMW.cc_tab.sig_register_range.connect(db.register_range)
    AppMW.cc_tab.sig_register_value.connect(db.register_ajustments)
    
    # Lock and unlock buttons on advanced panel
    AppMW.pBtAdvLockGiv.clicked.connect(AppMW.force_lock_giv)
    AppMW.pBtAdvUnlockGiv.clicked.connect(AppMW.force_unlock_giv)


    #AppMW.QTextConsole.append("Starting")
    AppMW.show()

    # Connect all the devices with serial port and SCPI protocol
    d_drv = None
    d_drv = create_devices_driver(
            cfg_object.config, AppMW.Qmessage_sscpi_print, AppMW)
    err = d_drv.scpi_relays.strerr
    if err:
        AppMW.display_error(err)
        msg_dialog_Error(err)

    err = d_drv.scpi_aoip.strerr
    if err:
        AppMW.display_error(err)
        msg_dialog_Error(err)

    # Register devices for debug commands
    AppMW.ctab_avanced.register_device("relay_device", d_drv.scpi_relays)
    AppMW.ctab_avanced.register_device("aoip_device", d_drv.scpi_aoip)
    AppMW.ctab_avanced.register_device("giv4_device", d_drv.scpi_giv4)

    # Get Calibrator datas and register it into DB
    if d_drv.scpi_aoip.device_port is not None:
        aoip_data = d_drv.get_aoip_datas()
        db.register_Aoip_in_DB(aoip_data)

    # Get GIV4 S/N and Set log file according to giv identifiant
    # The GIV conection is now detected by a timer when a new COM port appeart
    # in CDevicesDriver

    exit = app.exec_() 
    d_drv.send_stop_remote() 

    sys.exit(exit)

if __name__ == "__main__" or __name__ =='Agiv.MainApplication':
    print("arguments:", sys.argv)
    start_module_application()