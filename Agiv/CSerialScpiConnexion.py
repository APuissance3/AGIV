# This Python file uses the following encoding: utf-8
from PySide2.QtCore import QObject, Signal
import time
import serial, serial.tools.list_ports

from Utilities import SMALL_FONT


class CSimulatedPort():
    def __init__(self) -> None:
        self.name = "SIMPORT"
        self.simulated = True

    def close(self):
        pass





class CSerialScpiConnexion(QObject):
    """ Class that represent a connection with the requested device.
    Pass the id string requested to the constructor, and the object 
    created get a serial port with the device if it is finded.
    If not, device_port keep to None value 
    Last modif: add simulate flag
    """

    # This signal is emited when a request/response is completed
    # argument: message, color, font
    sigRequestComplete = Signal(object, object, object)
    #sigTest= QtCore.pyqtSignal()


    list_com_ports = None   # Free Com port list 
    last_time = time.perf_counter()

    @classmethod
    def find_COM_devices(cls):
        """ Utilitie function to get the list of all COM ports """
        myports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
        #print(myports)
        usb_port_list = [p[0] for p in myports]
        print("Find ports: {}".format(usb_port_list))
        return usb_port_list
    
    @classmethod
    def initialise_com_ports(cls):
        if cls.list_com_ports == None:
            cls.list_com_ports = cls.find_COM_devices()

    @classmethod
    def get_dt(cls):
        """ return the elapsed time since last call """
        new_t = time.perf_counter()
        dt =( new_t - cls.last_time) # result in ms
        cls.last_time = new_t
        str = "{:07.3F}s-".format(dt)
        return dt,str


    def __init__(self, id_name, color=None,  time_out=None, simulate=False, parent=None):
        super(CSerialScpiConnexion, self).__init__(parent)
        self.initialise_com_ports() # Buil com port list if it is not make yet
        self.id_string = None
        self.device_port = None
        self.simulate = simulate
        self.color = color       # Optional color passed to display the exchange in a terminal
        self.time_out = time_out if time_out is not None else 0.5
        if not self.simulate:
            self.try_connect(id_name)
            self.rx = None
            # self.tx = None
            if self.device_port == None:
                txt = "Can't find the requested device with id = '{}'".format(id_name)
                raise ConnectionError(txt )
            self.get_dt()    # Initialise 
        else:
            self.rx= id_name
            self.device_port = CSimulatedPort()

    def __del__(self):
        if self.device_port is not None:
            self.device_port.close()
            self.list_com_ports.append(self.device_port)
            self.device_port = None


    def send_request(self, str_tx, _sleep=None):
        """ Send a request to the device, and wait for the response.
        Send a signal with the exchange at the the end of a success exchange """

        (dt,st1) = self.get_dt()
        msg_tx = st1 + " TX>" + str_tx
        print(msg_tx)
        str_tx += '\n'      # Add the term character to the command

        if self.simulate:   #  We doesnt send and wait
            msg_rx = st1 + " RX> "
            self.sigRequestComplete.emit(msg_tx + '\n' + msg_rx, self.color, SMALL_FONT)
            return ""

        self.device_port.flush()
        self.device_port.write(str_tx.encode())  # encode is required to convert str to byte[]
        sleep = _sleep if _sleep is not None else 0.0  # Use provided sleep if given 
        if (sleep > 0.0):
            time.sleep(sleep)
            (dt,st2) = self.get_dt()
            print(st2 + "end wait")
        else:
            print("        -no wait")
        str_rx= str(self.device_port.readline()).replace("\\r","").replace("\\n","") \
                                                .replace("'","").replace("b","")
        (dt,st) = self.get_dt()
        # if we receive a response, emit the signal RequestComplete
        if len(str_rx) > 0:
            pass
        # self.tx = str_tx
        msg_rx = st + " RX> "+ str_rx
        self.sigRequestComplete.emit(msg_tx + '\n' + msg_rx, self.color, SMALL_FONT)
        print(msg_rx)
        return str_rx

    def try_connect(self, id_name):
        """ Request the identification string on all the awailable comports 
        to etablish the connection with the requested device """
        for s_port in self.list_com_ports:
            self.device_port = serial.Serial( 
                port = s_port,
                baudrate = 115200,      # N,8,1 by default 
                timeout = self.time_out
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
                self.sigRequestComplete.emit(
                        " Receive IDN on {} port: {}".format(s_port, rx), self.color, SMALL_FONT)
                break       # we are connected with the required device

