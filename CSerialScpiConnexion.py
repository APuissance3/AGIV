# This Python file uses the following encoding: utf-8
#from PySide2.QtGui import QColor
#from PyQt5 import QtCore
from PySide2.QtCore import QObject, Signal
import time
import serial, serial.tools.list_ports





class CSerialScpiConnexion(QObject):
    """ Class that represent a connection with the requested device.
    Pass the id string requested to the constructor, and the object 
    created get a serial port with the device if it is finded.
    If not, device_port keep to None value """

    # This signal is emited when a request/response is completed
    sigRequestComplete = Signal(object, object, object)
    #sigTest= QtCore.pyqtSignal()

    list_com_ports = None   # Free Com port list 

    @classmethod
    def find_USB_device(cls):
        """ Utilitie function to get the list of all usb ports """
        myports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
        print(myports)
        usb_port_list = [p[0] for p in myports]
        print("Find ports: {}".format(usb_port_list))
        return usb_port_list
    
    @classmethod
    def initialise_com_ports(cls):
        if cls.list_com_ports == None:
            cls.list_com_ports = cls.find_USB_device()


    def __init__(self, id_name, color=None,  sleep=0.5, parent=None):
        super(CSerialScpiConnexion, self).__init__(parent)
        self.initialise_com_ports() # Buil com port list if it is not make yet
        self.id_string = None
        self.device_port = None
        self.color = color       # Optional color passed to display the exchange in a terminal
        self.sleep = sleep
        self.try_connect(id_name)
        self.rx = None
        self.tx = None
        if self.device_port == None:
            txt = "Can't find the requested device with id = '{}'".format(id_name)
            raise ConnectionError(txt )

    def __del__(self):
        if self.device_port is not None:
            self.device_port.close()
            self.list_com_ports.append(self.device_port)
            self.device_port = None


    def send_request(self, str_tx, _sleep=None):
        """ Send a request to the device, and wait for the response.
        Send a signal with the exchange at the the end of a success exchange """
        self.device_port.flush()
        str_tx += '\n'      # Add the term character to the command
        self.device_port.write(str_tx.encode())  # encode is required to convert str to byte[]
        sleep = _sleep if _sleep is not None else self.sleep  # Use provided sleep if given 
        time.sleep(sleep)
        str_rx = ''
        while self.device_port.inWaiting() > 0:
            str_rx += str(self.device_port.readline()).replace("\\r","").replace("\\n","").replace("'","").replace("b","")
            time.sleep(0.001)
        # if we receive a response, emit the signal RequestComplete
        if len(str_rx) > 0:
            pass
        self.tx = str_tx
        self.sigRequestComplete.emit(str_tx, str_rx , self.color)
        print("received ", str_rx)
        return str_rx

    def try_connect(self, id_name):
        """ Request the identification string on all the awailable comports 
        to etablish the connection with the requested device """
        for s_port in self.list_com_ports:
            self.device_port = serial.Serial( 
                port = s_port,
                baudrate = 115200,      # N,8,1 by default 
                timeout = 0.5
            )
            if not self.device_port.is_open:
                 self.device_port.open()
            rx = self.send_request("*idn?")
            if id_name not in rx:   # This is not the requested alue
                self.device_port.close()
                self.device_port = None
            else:
                self.id_string = rx    # Note complete ID string
                # Remove this port from the free com port list
                self.list_com_ports.remove(s_port) 
                self.sigRequestComplete.emit("*IDN on {} port.".format(s_port), rx , self.color)
                break       # we are connected with the required device

