# This Python file uses the following encoding: utf-8
# to convert ui file: 
# pyside2-uic MainWindow.ui -o MainWindow.py

from PySide2.QtWidgets import QApplication, QMessageBox
from PySide2 import QtWidgets
from PySide2 import QtCore
import os
import sys
from pathlib import Path

# Our classes 
from .CCalibrateTab import CCalibrateTab
from .CMeasuresTab import CMeasuresTab
from .CDevicesDriver import CDevicesDriver, create_devices_driver, get_devices_driver
from .CConfigFile import CConfigFile, create_config_file_instance, get_config_file
from .MainWindow import Ui_MainWindow
from .Utilities import *
from .GivUtilities import *
from .CDBManager import  initialise_database
from .CLogger import create_logger, get_logger


global AppMW

def get_main_window():
    """ return AppMW for module that needs access to AppMW QWidgets"""
    return AppMW

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

        self.cm_tab = CMeasuresTab(self)
        self.cc_tab = CCalibrateTab(self)

        self.cm_tab.sig_info_message.connect(self.Qmessages_print)
        self.cc_tab.sig_info_message.connect(self.Qmessages_print)

        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, False) 
        self.setFixedSize(self.size()) # Disable resizing
        
        # Connecting information message from other tthread to the QTextConsole
        self.cBoxAdvanced.stateChanged.connect(self.change_advanced_mode)


    def init_log_name(self, str):
        log = get_logger()
        log.log_change_name('log_'+str+'.txt')
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
        else:
            self.cBoxMultithread.hide()
            # self.cBoxWriteCal.setChecked(True)
            self.cBoxWriteCal.setEnabled(False)
            self.cBoxRazCalib.setEnabled(False)
            self.cBoxRazCalib.setChecked(True)

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

def msg_dialog_unlock():
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Question)
    msg.setText("Le GIV est verouillé. On le déverouille pour l'ajustage ?")
    msg.setWindowTitle("Déverouillage")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    ret = msg.exec_()
    return (ret == QMessageBox.Yes)



def start_module_application():
    home = str(Path.home())
    agiv_dir = os.path.join(home,'Agiv')
    try:
        os.mkdir(agiv_dir)
    except Exception as ex:
        pass
    try:
        os.chdir(agiv_dir)
    except Exception as ex:
        print("Impossible de s'executer dans le repertoire Agiv: {}".format(ex))

    app = QApplication([])

    cfg_object = create_config_file_instance()   # Read config file and create an instance
    if cfg_object.config == None: # There is an error in config file
        msg_dialog_Error("Chargement du fichier de configuration impossible.",
            "Vérifier la présence et la cohérence de benchconfig.yaml",
            cfg_object.strerr)
        
        sys.exit(1)

    db = initialise_database("AP3reports_rec")

    log = create_logger()

    AppMW = MainWindow()
    AppMW.setWindowTitle("A Puissance 3 - AGIV")


    #Enable for Debug by default
    AppMW.cBoxAdvanced.setChecked(False)

    #Enable or disable advanced Tab function og advanced flag in the config file
    options= cfg_object.config['Options']
    enable_avanced = options['advanced']
    AppMW.tabWidget.setTabEnabled(2, enable_avanced)
    if not enable_avanced:
        AppMW.cBoxAdvanced.setChecked(False)
    AppMW.change_advanced_mode()


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
    if d_drv.str_error is not None:
        # Stop if there is an error at the initialisation
        AppMW.disable_MainWindow_with_error(d_drv.str_error) 
        d_drv.send_stop_remote() 
        if d_drv.scpi_giv4 == None:
            msg_dialog_Error("GIV4 non trouvé. Vous devez le brancher avant de lancer"
                " le banc.")
        else:
             msg_dialog_Error(d_drv.str_error)
        #  pour lesz test exit(1)

    # Get Calibrator datas and register it into DB
    if d_drv.scpi_aoip is not None:
        aoip_data = d_drv.get_aoip_datas()
        db.register_Aoip_in_DB(aoip_data)

    # Get GIV4 S/N and Set log file according to giv identifiant
    giv_id = get_giv_id(d_drv.scpi_giv4)
    db.register_giv(giv_id)  # The next records link with this GIV
    (giv_date, db_giv_date) = get_giv_caldate(d_drv.scpi_giv4)
    db.register_giv_last_cal_date(db_giv_date) # Register the Lock date
    AppMW.lEIdentifiant.textChanged.connect(AppMW.init_log_name)  
    AppMW.lEIdentifiant.setText("GIV4_Ref_{}".format(giv_id))
    AppMW.lE_DateCalib.setText(giv_date)

    # Check if GIV is looked. If Yes, ask to unlock
    giv_lock = is_giv_locked(d_drv.scpi_giv4)
    
    # For debug, we unlock systematiquely
    if False and giv_lock:
        unlock_giv(d_drv.scpi_giv4)
        giv_lock = False

    if giv_lock:    # If GIV is locked, ask for unlock
        res  = msg_dialog_unlock()
        if res:
            unlock_giv(d_drv.scpi_giv4)
        else: # If we keep locked, disable calibration writing capabilitie 
           AppMW.cBoxWriteCal.setChecked(False)
           AppMW.cBoxWriteCal.setEnabled(False)


    exit = app.exec_() 
    d_drv.send_stop_remote() 

    sys.exit(exit)

if __name__ == "__main__":
    start_module_application()