# This Python file uses the following encoding: utf-8
from PySide2.QtWidgets import QSpacerItem, QCheckBox, QHBoxLayout, QWidget 
from PySide2 import QtCore
from PySide2.QtCore import Signal


class CRangeStatusLayout(object):
    """ 
    This class contains Qt HLayout item to show and select one range 
    It is used by CCalibrateTab which keeps the list of all calibrations.
    """
    sig_range_cliqued = Signal(object)

    def __init__(self, range_name, range_data, parent = None):
        super(CRangeStatusLayout, self).__init__()
        # Create Qt item with Ok/Ko Led, and a checkbox with calibration name 
        self.range_name = range_name
        text = "{:<}".format(range_name)
        lim = "'"+text+"'"
        self.cBoxSel = QCheckBox(text)
        self.cBoxSel.setMinimumSize(320,0)
        self.cBoxStatus = QCheckBox(" --- ")
        self.cBoxStatus.setTristate(True)
        self.cBoxStatus.setStyleSheet(  "QCheckBox::indicator { width: 17px; height: 17px;}"
                                        "QCheckBox::indicator::unchecked {image: url(icons/led-red-on.png);}"
                                        "QCheckBox::indicator::indeterminate {image: url(icons/led-gray.png);}"
                                        "QCheckBox::indicator:checked {image: url(icons/led-green-on.png);}"
        )
        self.hLayout = QHBoxLayout()
        self.hLayout.addWidget(self.cBoxStatus)
        self.hLayout.addWidget(self.cBoxSel)
        self.cal_status = None      # Indicate the calibration status
#        self.cBoxSel.stateChanged.connect(lambda:self.btnstate(self.cBoxSel))
#        self.cBoxSel.stateChanged.connect(self.cBoxCliqued(self.cBoxSel))

    def __setattr__(self, attribute, new_val):
        """ Force the update of the widget if we change the cal_status """
        self.__dict__[attribute] = new_val  # General case
        if attribute == 'cal_status':
            self.update_indicator_color()

    def update_indicator_color(self):
        if self.cal_status == True:
            self.cBoxStatus.setCheckState(QtCore.Qt.CheckState.Checked)
            self.cBoxStatus.setText(" OK ")
        elif self.cal_status == False:
            self.cBoxStatus.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.cBoxStatus.setText(" Ko ")
        else:
            self.cBoxStatus.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
            self.cBoxStatus.setText(" -- ")
        return

    def cBoxCliqued(self, cBox):
        # Emits signal with the range name 
        self.sig_range_cliqued.emit(cBox.text)

