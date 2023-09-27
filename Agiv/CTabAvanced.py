# This Python file uses the following encoding: utf-8
from PySide2 import QtCore
from PySide2.QtCore import Signal, Slot, QThread, QObject
from .Utilities import *

CMD_BOX_FILE = "AgivDebugCmd.txt"


""" Gestion des QObjets du Tab Advanced (Debug et emission de commandes manuelles notament) """
class CTabAvanced(QObject):

    def __init__(self, parent=None, relay_device=None, aoip_device=None, giv4_device=None):
        super(CTabAvanced, self).__init__()
        self.pw = parent        
        self.relay_device = relay_device
        self.aoip_device = aoip_device
        self.giv4_device = giv4_device

        self.pw.pBtSendRly.clicked.connect(self.send_debug_rly)
        self.pw.pBtSendAoip.clicked.connect(self.send_debug_aoip)
        self.pw.pBtSendGiv.clicked.connect(self.send_debug_giv)
        self.init_combo_debug()
    
    """ Permet d'enregister les devices après l'init de l'IHM """
    def register_device(self, attr_device_name, attr_device_obj):
        setattr(self, attr_device_name, attr_device_obj)

    def send_debug_rly(self):
        str = self.pw.cBoxDbgSendCmd.currentText()
        rx = self.relay_device.send_request(str)

    def send_debug_aoip(self):
        str = self.pw.cBoxDbgSendCmd.currentText()
        rx = self.aoip_device.send_request(str)
        if rx and len(rx) > 0:
            self.add_debug_cmd(str)

    def send_debug_giv(self):
        str = self.pw.cBoxDbgSendCmd.currentText()
        rx = self.giv4_device.send_request(str)
        if rx and len(rx) > 0:
            self.add_debug_cmd(str)

    def init_combo_debug(self):
        dbg_cmd_file = get_Agiv_dir() + '//' + CMD_BOX_FILE
        try:
            with open(dbg_cmd_file,'r') as myfile:
                self.pw.cBoxDbgSendCmd.clear()
                txt = myfile.readline().replace('\n','')
                while txt:
                    print ("cmd: '"+ txt + "'")
                    self.pw.cBoxDbgSendCmd.addItem(txt)
                    txt = myfile.readline().replace('\n','')
        except Exception as ex:
            pass

    """ Ajoute la commande au fichier de debug """
    def add_debug_cmd(self, cmd):
        dbg_cmd_file = get_Agiv_dir() + '//' + CMD_BOX_FILE
        newcmd = True
        try:
            with open(dbg_cmd_file,'r') as myfile:
                txt = myfile.readline().replace('\n','')
                while txt:
                    if txt == cmd:
                        newcmd = False
                    txt = myfile.readline().replace('\n','')
        except Exception as ex:
            pass
        if newcmd:  # Ajoute commande si pas deja presente
            with open(dbg_cmd_file,'a') as myfile:
                myfile.write(cmd+'\n')
                #self.pw.cBoxDbgSendCmd.addItem(cmd)
            #print("cmd {} added".format(cmd))

