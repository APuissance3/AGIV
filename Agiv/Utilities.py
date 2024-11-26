# This Python file uses the following encoding: utf-8

# if __name__ == "__main__":
#     pass
from PySide2.QtWidgets import QApplication, QWidget,QVBoxLayout, QMessageBox

from PySide2.QtGui import QColor
import os
from pathlib import Path
import winsound as ws


INFO_FONT = 12.0
NORMAL_FONT = 14.0
BIG_FONT = 18.0
SMALL_FONT = 10.0


q_red_color = QColor('red') 
q_green_color = QColor('green') 
q_black_color = QColor('black') 
q_orange_color = QColor(0xF76E04)

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

def msg_dialog_confirm(strmessage, title):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Question)
    msg.setText(strmessage)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    ret = msg.exec_()
    return (ret == QMessageBox.Yes)

def msg_dialog_info(strmessage, title):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(strmessage)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QMessageBox.Ok)
    ret = msg.exec_()


""" Retourne le chemin Agiv dans le home (soit %userprofile%/Agiv sous Windows) 
    ou  celui indiqué dans la liste option
"""
def get_Agiv_dir(cfg_options=None):
    if cfg_options != None and 'reports_directory' in cfg_options:
        agiv_dir = cfg_options['reports_directory']
    else:
        home = str(Path.home())
        agiv_dir = os.path.join(home,'Agiv')
    return agiv_dir

def play_success():
    return
    ws.PlaySound("./Agiv/sounds/success.wav", ws.SND_FILENAME)

def play_echec():
    return
    ws.PlaySound("./Agiv/sounds/echec.wav", ws.SND_FILENAME)
    pass


""" Les fonctions ci-dessous permettent l'acces aux windget a partir de la mainWindow """
global AppMW

 # Fonction appellée par MainApplication pour passer l'info de la fenetre principale
def set_main_window(win):
    global AppMW
    AppMW = win

def get_main_window():
    """ return AppMW for module that needs access to AppMW QWidgets"""
    return AppMW

"""" Utile pour avoir l'etat de la checkbox overwrite au moment des calculs """
def get_overwrite_cBox():
    flg_overwrite = True if get_main_window().cBoxRazCalib.isChecked() else False
    return flg_overwrite

"""" Utile pour avoir l'etat de la checkbox overwrite au moment des calculs """
def get_zeroize_cBox():
    flg_overwrite = True if get_main_window().ZeroiseCalib.isChecked() else False
    return flg_overwrite


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

