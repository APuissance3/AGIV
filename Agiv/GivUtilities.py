# This Python file uses the following encoding: utf-8
""" This module contains utilities function for working with Giv  """
from datetime import datetime, timedelta

REF_DATE = datetime.fromisoformat('2020-01-01')

_giv_id = ''
def get_giv_id(giv_scpi=None):
    global _giv_id
    if True or _giv_id == None:
        cmd = ":SYST:LOCK:CODE?"
        rx = "SIM_000.100"
        if giv_scpi is not None:
            rx = giv_scpi.send_request(cmd).replace(' ','')
            _giv_id = rx
    return(_giv_id)

def get_last_giv_id():
    return(_giv_id)

def reset_last_giv_id():
    global _giv_id
    _giv_id =''

def is_giv_locked(giv_scpi):
    ret = False
    if giv_scpi.device_port is not None:
        ret = True
        cmd = ":SYST:LOCK?"
        rx = giv_scpi.send_request(cmd)
        # If 'UNlocked' return False
        if len(rx)>0 and 'UN' in rx: ret= False
    else:
        ret = False
    return (ret)

def get_giv_caldate(giv_scpi):
    cmd = ":SYST:ADJ:DATE?"
    rx=""
    txt_date ='01/01/2000'
    fr_date = ''
    db_date = ''
    if giv_scpi is not None:
        rx = giv_scpi.send_request(cmd)
        if len(rx) > 0:
            nb_days = int(rx.replace(' ',''))
            adj_date = REF_DATE + timedelta (days=nb_days)
            fr_date = adj_date.strftime('%d/%m/%Y')
            db_date =  adj_date.strftime('%Y-%m-%d')
    return (fr_date, db_date)
    
def unlock_giv(giv_scpi):
    if giv_scpi is None:
        return "UNLOCK"
    cde = get_giv_id(giv_scpi).replace(' ','').replace('.','')
    cde = int(cde)%1000000
    cde ^= 0x5448
    cde += 0x4C4E
    fcde = float(cde)/1000.0
    cmd = ":SYST:LOCK:CODE {};:SYST:LOCK?".format(fcde)
    rx = giv_scpi.send_request(cmd)
    return rx

def lock_giv(giv_scpi):
    adj_date = datetime.now() - REF_DATE
    nday = adj_date.days
    print (nday)
    cmd = ":SYST:ADJ:DATE {};:SYST:LOCK:CODE 0;:SYST:LOCK?".format(nday)
    rx = giv_scpi.send_request(cmd)
    return rx
