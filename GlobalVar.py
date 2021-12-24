# This Python file uses the following encoding: utf-8
""" This file contains the common global variables """
from CLogger import CLogger

global logger
logger = CLogger()

global run_thread
run_thread = False   # Checked by the thread

def print_run():
    print("Run_thread=", run_thread)