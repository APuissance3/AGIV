# This Python file uses the following encoding: utf-8
import os

from PySide2 import QtCore
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

#ICON_BLUE_LED = ":/icons/blue-led-on.png"

class CMeasurePoint(object):
    """ This class represent a set of measure point with the passed/ not passed 
    information
    """
    def __init__(self, point_value, parent=None):
        super(CMeasurePoint,self).__init__()
        self.check = None
        self.value = point_value
        # Le ">"  indique une justification à droite
        self.check_value = "{:> 7.1F}".format(point_value)
        self.hiew = QHBoxLayout()
        self.vled = QCheckBox(self.check_value)
        self.vled.setTristate(True)
        self.vled.setStyleSheet(  "QCheckBox::indicator { width: 17px; height: 17px;}"
                                    "QCheckBox::indicator::unchecked {image: url(icons/led-red-on.png);}"
                                    "QCheckBox::indicator::indeterminate {image: url(icons/led-gray.png);}"
                                    "QCheckBox::indicator:checked {image: url(icons/led-green-on.png);}"
        )
        self.vled.setGeometry(100,100,600,400)
        self.update_indicator_color()
        self.hiew.addWidget(self.vled)
        self.lbl_read_val= QLineEdit()
        self.lbl_read_val.setFixedWidth(100)
        self.lbl_read_val.setAlignment(Qt.AlignCenter)
        self.hiew.addWidget(self.lbl_read_val)
         # Set value after creating the read_val Widget
        self.read_value = None  

        #self.hiew.addWidget(self.vvalue)
        #self.vbutton= QPushButton("Ajuster")
        #self.hiew.addWidget(self.vbutton)

    def __setattr__(self, attribute, new_val):
        """ Force the update of the widget if we change the read value """
        self.__dict__[attribute] = new_val  # General case
        if attribute == 'read_value':
            mystr = "  {:>+8.4f}".format(new_val) if new_val is not None else "--------"
            self.lbl_read_val.setText(mystr)


    def update_indicator_color(self):
        if self.check == True:
            self.vled.setCheckState(QtCore.Qt.CheckState.Checked)
            #self.vled.setStyleSheet("QCheckBox::indicator {background-color : lightgreen;}")
        elif self.check == False:
            self.vled.setCheckState(QtCore.Qt.CheckState.Unchecked)
            #self.vled.setStyleSheet("QCheckBox::indicator {background-color : red;}")
        else:
            self.vled.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
            #self.vled.setStyleSheet("QCheckBox::indicator {background-color : darkGray;}")

 
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"OneMeasure")

