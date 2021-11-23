# This Python file uses the following encoding: utf-8

from PySide2.QtWidgets import QApplication
from PySide2 import QtWidgets
from PySide2.QtGui import QPalette

import sys
import yaml
# Our classes 
from CMeasure import CMeasure
from CCheckMeasure import CCheck_measures_list
from CSerialScpiConnexion import CSerialScpiConnexion
from CDevicesDriver import CDevicesDriver
from MainWindow import Ui_MainWindow
from Utilities import *

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """ Cette classe herite de UI_MainWindow qui represente la boite de dialogue 
    principale
    """
    def __init__(self, config_file_name):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.QTextConsole.show()    # To display initialisation errors 
        self.list_measures = list() # Empty as none are selected
        self.checkThread = None     # Thread used to check the measure points 
        self.cfg_selected = None    # shortcut to config info of the selected range
        self.config  = None         # The config loaded from the yaml file
        self.devices = None         # The classe witch drive the SCPI lines
        
        # Loading all config info from YAML file
        self.config  = None
        with open(config_file_name, "r") as stream:
            try:
                self.config  = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        self.label_Titre.setText(self.config['Titre'])

        # Read our ranges data and fill ranges comboBox       
        self.cfg_ranges = self.config['Ranges']
        for game, game_data in self.cfg_ranges.items():
            self.comboRangeSelection.addItem(game)  

        self.comboRangeSelection.currentTextChanged.connect(self.range_choosed)
        self.QPshBtGo.setEnabled(False)     # Waiting for a enabled range selected
        self.QPshBtGo.clicked.connect(self.start_check_measures) 
        self.pBtQuit.clicked.connect(self.quit_application)

    def  range_choosed(self, selected_range):
        """ Called when the game is chosen. display points of the range """
        self.cfg_selected = self.cfg_ranges[selected_range]  # Shortcut to the data
        # Erase the previous selected measures
        self.list_measures.clear()  
        # Delete previous measure point widgets
        clearLayout(self.vMeasuresLayout)

        if self.cfg_selected['active'] == True:   # Only if the range selected is enabled
            # Create a list of all point and a layout with there values
            print(selected_range)
            self.devices.go_config(selected_range)
            self.QPshBtGo.setEnabled(True)
            # show the measure point of this range only if this game is enabled
            for measure in self.cfg_selected['points']:
                current_measure = CMeasure(measure)
                self.list_measures.append(current_measure)   # Append the measures points
                self.vMeasuresLayout.addLayout(current_measure.hiew)    # Add his viewer widget  
        else:
            self.QPshBtGo.setEnabled(False)
            print('selected range "{}" is disabled'.format(selected_range))

    def start_check_measures(self):
        """ Called when Test button is pressed. Run the mesure checking for
        all the points in another thread
        """
        # Pas possible on est deja dedans
        # print("Start measure for {}".format(self.cfg_selected))
        self.checkThread = CCheck_measures_list(
                                self.list_measures, self.cfg_selected, self.devices)
        self.checkThread.sigAddText.connect(self.uppdate_Qmessages)
        self.checkThread.start()

    def show_request_in_Qmessage(self, tx, rx, color):
        if color is not None:
            self.QTextConsole.setTextColor(color)
        mystr = "TX >" + tx + "RX >" + rx # Append add a '\n' to the appended text
        self.QTextConsole.append(mystr)


    # We uppdate the QTextConsole with the messages emited in the measure thread
    def uppdate_Qmessages(self, color, message):
        if color is not None:
            self.QTextConsole.setTextColor(color)
        self.QTextConsole.append(message)

    def display_error(self, str_err=None):
        """ Print red message in large charaters on the TextConsole """
        if str_err is not None:
            palette = self.QTextConsole.palette()
            color = palette.color(QPalette.WindowText) # Get actual color
            self.QTextConsole.setTextColor(q_red_color)
            self.QTextConsole.setFontPointSize(18.0)
            self.QTextConsole.append(str_err)
            self.QTextConsole.setFontPointSize(10)
            self.QTextConsole.setTextColor(color)   # Restore the color
            self.QTextConsole.setFontPointSize(10.0)
        
    def disable_MainWindow_with_error(self, str_err=None):
        """ This function used to disable the HMI if the bench initialisation fail """
        self.display_error(str_err)
        self.comboRangeSelection.setEnabled(False)  # Continue working is forbiden

    def quit_application(self):
        AppMainWindow.devices.stop()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication([])
    AppMainWindow = MainWindow("benchconfig.yaml")

    # Connect all the devices with serial port and SCPI protocol
    # We connect the devices here, in order to show the device communication in the 
    # QTextConsole dialog
    try:
        AppMainWindow.devices = CDevicesDriver(AppMainWindow.config, 
                AppMainWindow, AppMainWindow.show_request_in_Qmessage)
    except ConnectionError as exc:
        # Stop if there is an error at the initialisation
        AppMainWindow.disable_MainWindow_with_error(str(exc))  
            # Only display the error message in case of protocol problem  
        AppMainWindow.devices.sig_communication_error.connect(AppMainWindow.display_error)
    
    AppMainWindow.QTextConsole.append("Starting")
    AppMainWindow.show()
    exit = app.exec_()    
    sys.exit(exit)

