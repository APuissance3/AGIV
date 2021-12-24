# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
from PySide2.QtWidgets import QApplication, QWidget,QVBoxLayout, QMessageBox

from PySide2.QtGui import QColor

INFO_FONT = 12.0
NORMAL_FONT = 14.0
BIG_FONT = 18.0
SMALL_FONT = 10.0


q_red_color = QColor('red') 
q_green_color = QColor('green') 
q_black_color = QColor('black') 

def msg_dialog_Error(strmessage, strmess2=None, strmess3=None):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(strmessage+'\n')
    if strmess2 is not None:
        msg.setInformativeText(strmess2)
    if strmess3 is not None:
        msg.setDetailedText(strmess3)
    msg.setWindowTitle("Erreur Banc de test AGIV")
    msg.setStandardButtons(QMessageBox.Ok)
    ret = msg.exec_()



def str2float(str):
    """ try to convert string, without error """
    ret = 0.0
    try:
        ret = float(str)
    except ValueError  as ex:
        print("Echec float convertion: str='{}' Execp:{}".format(str, ex.__str__))
    return ret

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

