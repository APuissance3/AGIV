# This Python file uses the following encoding: utf-8
""" This module permits to load the config file and could 
share the instance of the config file with others modules
"""
import yaml
import os

config_filename = "benchconfig.yaml"       
config_file_instance = None

def create_config_file_instance():
    """ Create a instance of the AGIV config file """
    global config_file_instance
    config_file_instance = CConfigFile(config_filename)
    return config_file_instance

def get_config_file():
    """ return the config tree of loaded AGIV config file """
    return config_file_instance.config

def get_config_ranges():
    """ Return the range part of the loaded config file """
    return config_file_instance.ranges

class CConfigFile():

    """ Create a instance of the yaml config file with config_filename """
    def __init__(self, fname):
        path = os.path.abspath(__file__)
        fullname = os.path.join(os.path.dirname(path), fname) 
        # Loading all config info from YAML file
        with open(fullname, "r") as stream:
            try:
                self.config  = yaml.safe_load(stream)
                # Shortcut on the ranges data
                self.ranges = self.config['Ranges']
            except yaml.YAMLError as exc:
                print(exc)
                self.strerr = str(exc)
                self.config = None
 