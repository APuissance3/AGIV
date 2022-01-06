# This Python file uses the following encoding: utf-8
import openpyxl as opx
from openpyxl import Workbook
from datetime import datetime




class CXlsReportGenerator():
    """ This class is used to build the measures report excel file """

    def __init__(self, _fname=None):
        self.filename = _fname
        self.wb = Workbook()

    def set_filename (self, fname):
        self.filename = fname
    


# Check excel file generation 

if __name__ == "__main__":
    my_xls_name = "./builded_excel.xlsx"
    
