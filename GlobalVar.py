# This Python file uses the following encoding: utf-8
""" This file contains the common global variables """
from CLogger import CLogger
#from CXlsReportgenerator import CXlsReportGenerator
#from CDBManager import CDBManager#
from GivUtilities import get_giv_id

global logger
global xls_file
#global database

logger = CLogger()
# xls_file = CXlsReportGenerator()
#database = CDBManager('AP3reports_rec')

global giv_id
global giv_date

global run_thread
run_thread = False   # Checked by the thread

def print_run():
    print("Run_thread=", run_thread)