# This Python file uses the following encoding: utf-8
from Utilities import *

from CMeasurePoint import CMeasurePoint
from PySide2.QtCore import Signal, Slot, QThread, QObject, QTimer
from CCheckRangePoint import CCheckRangePoint
from CConfigFile import get_config_file, get_config_ranges
from CDevicesDriver import get_devices_driver
from CRangeStatusLayout import CRangeStatusLayout
from threading import get_ident
from enum import Enum, unique


# Enum for the states of state machine
class CMeasSt(Enum):
    wait = 0
    init_list = 1
    init_range = 2
    wait_measures = 3
    measures_finished = 4
    measures_abort = 5

def dbg_print(*args,**kwargs):
    pass
    # print(*args,**kwargs)

class CMeasuresTab(QThread):
    """ This class add attributes to manage the measures panel """

    # This signal is emited to display messages 
    # argument: message, color, font
    sig_info_message = Signal(object, object, object)


    def __init__(self, _parent=None):
        """ parent is the Mainwindow Widget  """
        super(CMeasuresTab, self).__init__()
        # The ranges list 
        self.vRangesLayout = createVLayerForScroll(_parent.scrollMeasRange)
        # The measures list
        self.vMeasureLayout = createVLayerForScroll(_parent.scrollMeasures)
        self.list_measures = list() # Empty as none are selected
        self.list_ranges = list()
        self.list_ranges_selected = list()
        self.running = False    
        self.phmi = _parent
        # Attributes to drive the state machine
        self.timer = QTimer()
        self.state = CMeasSt.wait   # Wait for Start button
        self.old_state = None # For debug
        self.cur_range_indx = 0
        self.cur_range = None

        # Read our ranges data and fill ranges comboBox       
        self.cfg_ranges = get_config_ranges()
        for range, range_data in self.cfg_ranges.items():
            # Check for 'active' key if exist
            if 'active' in range_data and range_data['active']:
                meas_range_view = CRangeStatusLayout(range, range_data, self.phmi)    # Create the object
                self.vRangesLayout.addLayout(meas_range_view.hLayout)
                self.list_ranges.append(meas_range_view)
        self.phmi.pBtSMeasSelectAll.clicked.connect(self.select_all_range)
        self.phmi.pBtMeasUnselectAll.clicked.connect(self.unselec_all_range)
        self.phmi.pBtRunMeasures.clicked.connect(self.pbt_start_stop_cliqued)
        self.timer.timeout.connect(self.timer_state_machine)
        self.timer.start(500)   # Check state machine every 500mS



    def select_all_range(self):
        for range_view in self.list_ranges:
            range_view.cBoxSel.setChecked(True)


    def unselec_all_range(self):
        for range_view in self.list_ranges:
            range_view.cBoxSel.setChecked(False)

    # Called when Start / Stop is cliqued: laught the state machine
    def pbt_start_stop_cliqued(self):
        if self.state == CMeasSt.wait:
            self.state = CMeasSt.init_list
        else:
            self.state = CMeasSt.measures_abort
            pass
    
    def timer_state_machine(self):
        """ This function is cycliquely called in the main thread. 
        It permits to update Main GUI in the main thread, but 
        without blocking the system. We use a state machine to do 
        the job 
         """
        if self.old_state != self.state:
            dbg_print("State change to {}".format(self.state) )
            self.old_state = self.state
         
        if self.state == CMeasSt.wait:  # Normal standby state            
            return

        if self.state == CMeasSt.measures_abort:
            dbg_print("State ====>   measures_abort")
            self.sig_info_message.emit( 
                    "Mesures interrompues par l'utilisateur", q_red_color, NORMAL_FONT)
            self.phmi.pBtRunMeasures.setText("START MESURES")
            self.list_ranges_selected.clear()
            self.state = CMeasSt.wait
            if self.phmi.cBoxMultithread.isChecked():
                dbg_print("State ====>   wait thread terminate  - measures_abort")
                self.terminate()
                self.wait() 
            return

        # First step after "start": build the list of ranges to check
        if self.state == CMeasSt.init_list:
            self.list_ranges_selected.clear()
            self.phmi.pBtRunMeasures.setText("STOP MESURES")
            for range_view in self.list_ranges: # Build the list of the range to check
                if range_view.cBoxSel.isChecked():
                    range_view.cal_status = None
                    self.list_ranges_selected.append(range_view)
            self.cur_range_indx = 0
            self.state = CMeasSt.init_range
            nb_range = len(self.list_ranges_selected)
            strinfo = "\nRelevé de {} gamme{}".format(
                nb_range, 's' if nb_range > 1 else '')
            self.sig_info_message.emit(strinfo, q_green_color, NORMAL_FONT)
            return

        if self.state == CMeasSt.init_range:
            dbg_print("State ====>   init_range")
            self.cur_range = self.list_ranges_selected[self.cur_range_indx]
            self.cur_range_indx += 1
            self.select_a_range(self.cur_range.range_name)
            strinfo = "Gamme {}.".format(self.cur_range.range_name)
            self.sig_info_message.emit(strinfo, q_green_color, NORMAL_FONT)
            self.state = CMeasSt.wait_measures
            if self.phmi.cBoxMultithread.isChecked():
                self.start()      # Start the run method in another thread
            else:
                self.run()        # For debuging, we could run in the main thread
            return

        if self.state == CMeasSt.wait_measures:
            dbg_print("State ====>   wait_measures")
            return  # We wait until check_point_list() change to the next state

        if self.state == CMeasSt.measures_finished:
            # The run() method as finished to check the measures points. 
            # It drive the state here
            dbg_print("State ====>   measures_finished")
            if self.cur_range_indx >= len(self.list_ranges_selected):
                self.state = CMeasSt.wait   # All ranges was tested
                self.phmi.pBtRunMeasures.setText("START MESURES")
                strinfo = "Fin des relevés\n"
                self.sig_info_message.emit(strinfo, q_green_color, NORMAL_FONT)
                dbg_print("State ====>   goto wait")
            else:
                dbg_print("State ====>   goto init_range")
                self.state = CMeasSt.init_range # Go on next range
            return


    def  select_a_range(self, selected_range):
        """ Called when the range  is chosen. Call the configuration for the range,
        load and display the measure points to check  """
        
        self.cfg_selected = self.cfg_ranges[selected_range]  # Shortcut to the data
        # Erase the previous selected measures
        self.list_measures.clear()  
        # Delete previous measure point widgets
        clearLayout(self.vMeasureLayout)

        if self.cfg_selected['active'] == True:   # Only if the range selected is enabled
            # Create a list of all point and a layout with there values
            print(selected_range)
            devices = get_devices_driver()
            devices.go_config(selected_range)
            #   --- old for combo -- self.phmi.pBtGo.setEnabled(True)
            # show the measure point of this range only if this game is enabled
            for measure in self.cfg_selected['points']:
                current_measure = CMeasurePoint(measure)
                self.list_measures.append(current_measure)   # Append the measures points
                self.vMeasureLayout.addLayout(current_measure.hiew)    # Add his viewer widget  

    def reset(self):
        """ Reset the mesasure point status """
        for a_point in self.list_measures:
            a_point.check = None
            a_point.update_indicator_color()

    def check_point_list(self, range_name):
        """ Check the list of points for one range """
        range_status = True
        self.reset()
        ddriver = get_devices_driver()
        range_data = get_config_ranges()[range_name]
        checker = CCheckRangePoint(range_data)
        for a_point in self.list_measures:
            if self.state != CMeasSt.wait_measures:
                break  # If the user stop the process, break the loop
            val_send = float(a_point.check_value)
            print("check the a_point {}".format(val_send))
            txt_info = "relevé valeur {}".format(a_point.check_value)
            self.sig_info_message.emit( txt_info, q_green_color, INFO_FONT)
            nb_try = 3
            while nb_try:
                val_read = ddriver.check_value(a_point.check_value)
                (check_ok, min, max) = checker.check_val(val_send, val_read)
                a_point.check = check_ok
                a_point.read_value = val_read   # Normaly force the calling of 
                print( "check {:0.4f} < {:0.4f}  < {:0.4f}  : {}".format(max, val_read, min, a_point.check))
                if  a_point.check: # end if the measure is good
                    break
                nb_try -= 1 # Try another time
            a_point.update_indicator_color()
            if a_point.check == False:
                range_status = False
        return range_status


    def run(self):
        """ Thread run overload method. Call check_point_list() for cur_range  """
        dbg_print ("Running thread measure list")
        range_ok = self.check_point_list(self.cur_range.range_name)
        self.cur_range.cal_status = range_ok  # Show result for the range
        dbg_print("Fin check_point_list()")
        self.state = CMeasSt.measures_finished
        dbg_print("Terminate")
        #self.terminate()       

