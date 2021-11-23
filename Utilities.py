# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
from PySide2.QtWidgets import QApplication
from PySide2 import QtWidgets

from PySide2.QtGui import QColor
q_red_color = QColor('red') 
q_green_color = QColor('green') 
q_black_color = QColor('black') 



def clearLayout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.layout():
            clearLayout(child)
        if child.widget():
            child.widget().deleteLater()

