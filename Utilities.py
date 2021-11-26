# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
from PySide2.QtWidgets import QApplication, QWidget,QVBoxLayout

from PySide2.QtGui import QColor
q_red_color = QColor('red') 
q_green_color = QColor('green') 
q_black_color = QColor('black') 



def createVLayerForScroll(qScroller):
    """ Create a scrollable QWidget that contains QVBoxLayout 
    As a the QScrollArea can only contains a QWidget, we create this
    widget, and attach a verticall Layout to this. 
    The fucntion return the vertical Layer to fill 
    """
    scrollContent = QWidget()   # Le widget qui va etre scrollé
    vLayout = QVBoxLayout()     # vLayou pour empiler verticalement
    scrollContent.setLayout(vLayout)    #  Ajoute un vLayout dans le content a scroller
    qScroller.setWidget(scrollContent)  # La ça va gerer le scrolling du widget
    qScroller.show()
    return vLayout


# trouver quoi faire si qwidget
def clearLayout(layout):
    """ Erase the widget and the layout contained in the Layou """
    while layout.count():
        child = layout.takeAt(0)
        if child.layout():
            clearLayout(child)
        if child.widget():
            child.widget().deleteLater()

