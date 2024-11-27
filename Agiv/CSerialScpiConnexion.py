# This Python file uses the following encoding: utf-8
""" This module define the CSerialScpiConnexion class.
It permits to find modifications on detected COM ports, 
open a port at the specifier parameters, 
and can send a request and wait response to a connected device
11/2024 V3.2 change: Debug message only if COM ports list change
"""

from PySide2.QtCore import QObject, Signal
import time
import serial, serial.tools.list_ports

from .Utilities import SMALL_FONT


class CSimulatedPort():
    def __init__(self) -> None:
        self.name = "SIMPORT"
        self.simulated = True

    def close(self):
        pass


def read_float(device, msgtx=None):
    rx = device.send_request(msgtx) # Get measure
    rx = rx.split(',')[0]   # Keep first element of the AOIP response (eg: '9.999, mA')
    return rx



class CSerialScpiConnexion(QObject):
    """ Class that represent a connection with the requested device.
    Pass the id string requested to the constructor, and the object 
    created get a serial port with the device if it is finded.
    If not, device_port keep to None value 
    Last modif: add simulate flag
    Add baudrate definition, exclude bluetooth comports 
    """

    # This signal is emited when a request/response is completed
    # argument: message, color, font
    sigRequestComplete = Signal(object, object, object)
    #sigTest= QtCore.pyqtSignal()


    list_com_ports = None   # Com port list
    list_used_com = []      # Used port list
    last_time = time.perf_counter()

    @classmethod
    def initialise_com_ports(cls):
        list_com_find = cls.find_COM_devices()
        if cls.list_com_ports== None or cls.list_com_ports != list_com_find: # there is a change in connected COM ports
            print(f"New finded ports: {list_com_find}")
            cls.list_com_ports = list_com_find
    

    @classmethod
    def register_used_port(cls, port_name):
        cls.list_used_com.append(port_name)

    @classmethod
    def is_used_port(cls, port_name):
        return port_name in cls.list_used_com

    @classmethod
    def find_COM_devices(cls):
        """ Utilitie function to get the list of all COM ports.
            We exclude BLUETOOTH serial COM port that can freeze 
            the script when sending a frame 
        """
        usb_port_list = []
        myports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
        #print(myports)
        for p in myports:
            comport = p[0]
            description = p[1].lower()
            if not 'bluetooth' in description: #Exlude Bluetooth Comport
                usb_port_list.append(comport)
        #print(f"Find ports: {usb_port_list}")
        return usb_port_list


    @classmethod
    def get_dt(cls):
        """ return the elapsed time since last call """
        new_t = time.perf_counter()
        dt =( new_t - cls.last_time) # result in ms
        cls.last_time = new_t
        str = "{:07.3F}s-".format(dt)
        return dt,str

    @classmethod
    def update_awailable_ports(cls):
        # Check for COM port, return true if a used com port disapear from awailables ports
        removed = False
        cls.initialise_com_ports()
        for com in cls.list_used_com:
            if not com in cls.list_com_ports:
                cls.list_used_com.remove(com)
                removed = True
        return removed


    def __init__(self, id_name, color=None,  time_out=0.5, simulate=False, baudrate=115200, parent=None ):
        super(CSerialScpiConnexion, self).__init__(parent)
        #self.initialise_com_ports() # Buil com port list if it is not make yet
        self.id_string = None   # Full id string receved
        self.id_name = id_name  # id name we try to find in id_string
        self.device_port = None
        self.strerr = None
        self.flg_simulate = simulate
        self.color = color       # Optional color passed to display the exchange in a terminal
        self.time_out = time_out
        self.baudrate = baudrate
        self.default_tx = None

        if not self.flg_simulate:
            self.try_connect()
            self.rx = None
            self.get_dt()    # Initialise 
        else:
            self.rx= id_name
            self.device_port = CSimulatedPort()

    def __del__(self):
        if self.device_port is not None:
            try:
                self.device_port.close()
            except Exception:
                pass
            self.list_com_ports.append(self.device_port)
            self.device_port = None




    def send_request(self, str_tx, _sleep=None):
        """ Send a request to the device, and wait for the response.
        Send a signal with the exchange at the the end of a success exchange """
        str_rx = ""

        if self.device_port == None:
            return str_rx
        
        (dt,st1) = self.get_dt()
        msg_tx = st1 + " TX>" + str_tx
        print(msg_tx)
        str_tx += '\n'      # Add the term character to the command

        if self.flg_simulate:   #  We doesnt send and wait
            msg_rx = st1 + " RX> "
            self.sigRequestComplete.emit(msg_tx + '\n' + msg_rx, self.color, SMALL_FONT)
            return ""

        try:
            self.device_port.flush()
            self.device_port.write(str_tx.encode())  # encode is required to convert str to byte[]
        except Exception:
            pass
        sleep = _sleep if _sleep is not None else 0.0  # Use provided sleep if given 
        if (sleep > 0.0):
            time.sleep(sleep)
            (dt,st2) = self.get_dt()
            print(st2 + "end wait")
        else:
            print("        -no wait")
        try:
            str_rx= str(self.device_port.readline()).replace("\\r","").replace("\\n","") \
                                                .replace("'","").replace("b","")
        except:
            pass
        (dt,st) = self.get_dt()
        # if we receive a response, emit the signal RequestComplete
        if len(str_rx) > 0:
            pass
        # self.tx = str_tx
        msg_rx = st + " RX> "+ str_rx
        self.sigRequestComplete.emit(msg_tx + '\n' + msg_rx, self.color, SMALL_FONT)
        print(msg_rx)
        return str_rx

    def try_connect(self):
        """ Request the identification string on all the awailable comports 
        to etablish the connection with the requested device """
        #self.list_com_ports = self.find_COM_devices()
        self.update_awailable_ports()

        for s_port in CSerialScpiConnexion.list_com_ports:
            if s_port in CSerialScpiConnexion.list_used_com:
                continue
            self.device_port = serial.Serial( 
                port = s_port,
                baudrate = self.baudrate,
                timeout = self.time_out
            )
            # If the port is already open, we ca'nt use it 
            if not self.device_port.is_open:
                self.device_port.open()
            print (f"Check {s_port} @ {self.baudrate} for {self.id_name}: ")
            rx = self.send_request("*IDN?")
            if len(rx) > 0:
                pass
            if self.id_name not in rx:   # This is not the requested value
                try:
                    self.device_port.close()
                except Exception:
                    pass
                self.device_port = None
            else:
                self.id_string = rx    # Note complete ID string
                # Remove this port from the free com port list
                #self.list_com_ports.remove(s_port) 
                self.register_used_port(s_port)
                self.sigRequestComplete.emit(
                        " Receive IDN on {} port: {}".format(s_port, rx), self.color, SMALL_FONT)
                return       # we are connected with the required device

