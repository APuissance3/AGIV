# This Python file uses the following encoding: utf-8
import os

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

ICON_BLUE_LED = ":/icons/blue-led-on.png"

class CMeasure(object):
    """ This class represent a set of measure point with the passed/ not passed 
    information
    """
    def __init__(self, point_value):
        self.check = None
        self.value = point_value
        self.read_value = 0.0
        # Le ">"  indique une justification à droite
        self.check_value = "{:> 8.4}".format(point_value)
        self.hiew = QHBoxLayout()
        self.vled = QCheckBox(self.check_value)
        self.vled.setGeometry(100,100,600,400)
        self.update_indicator_color()
        self.hiew.addWidget(self.vled)
        self.lbl_read_val= QLineEdit()
        self.lbl_read_val.setFixedWidth(100)
        self.lbl_read_val.setAlignment(Qt.AlignCenter)
        self.lbl_read_val.setText("-----")
        self.hiew.addWidget(self.lbl_read_val)
        #self.hiew.addWidget(self.vvalue)
        #self.vbutton= QPushButton("Ajuster")
        #self.hiew.addWidget(self.vbutton)

    def __set_attr__(self, attribute, new_val):
        """ Force the update of the widget if we change the read value """
        print("__set_attr__ : '" + attribute +"'")
        if attribute == 'read_value':
            self.read_value = new_val
            mystr = "  {8.4}".format(self.read_value)
            self.lbl_read_val.setText(mystr)



    def update_indicator_color(self):
        if self.check == True:
            self.vled.setStyleSheet("QCheckBox::indicator {background-color : lightgreen;}")
        elif self.check == False:
            self.vled.setStyleSheet("QCheckBox::indicator {background-color : red;}")
        else:
            self.vled.setStyleSheet("QCheckBox::indicator {background-color : darkGray;}")

 
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"OneMeasure")

