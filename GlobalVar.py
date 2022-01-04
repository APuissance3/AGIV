# This Python file uses the following encoding: utf-8
""" This file contains the common global variables """
from CLogger import CLogger
from CXlsReportgenerator import CXlsReportGenerator

global logger
global xls_file

logger = CLogger()
xls_file = CXlsReportGenerator()

global run_thread
run_thread = False   # Checked by the thread

def print_run():
    print("Run_thread=", run_thread)