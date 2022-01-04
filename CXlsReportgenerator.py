# This Python file uses the following encoding: utf-8
import openpyxl as opx
from openpyxl import Workbook
from datetime import datetime




class CXlsReportGenerator():
    """ This class is used to build the measures report excel file """

    def __init__(self, _parent=None):
        self.filename = None
        self.wb = Workbook()

    def set_filename (self, fname):
        self.filename = fname
    
