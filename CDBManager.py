# This Python file uses the following encoding: utf-8
# """ Store the calibration and measure records in a database """

import sys
#import pathlib
import os
from GlobalVar import *
from CConfigFile import create_config_file_instance, get_config_ranges
from Utilities import *



"""  Requete qui marche:
 Note: pour Sqlite la primary key est toujours AUTO_INCREMENT. Il faut supprimer le mot clé 
"""
SQL_TABLE_GIV_IG =  f'CREATE TABLE  IF NOT EXISTS GIV_ids ('\
                    f'`Key_id` INTEGER NOT NULL UNIQUE,'\
                    f'`Giv_id` TEXT UNIQUE,'\
                    f'PRIMARY KEY (`Key_id`) );'

SQL_TABLE_RANGES =  f'CREATE TABLE  IF NOT EXISTS Ranges ('\
                    f'`Key_id` INTEGER NOT NULL UNIQUE,'\
                    f'`Range` TEXT,'\
                    f'`Gamme` TEXT UNIQUE,'\
                    f'`To_calibrate` INTEGER,'\
                    f'PRIMARY KEY (`Key_id`) );'

# Date type: Lock or Record (calibration or measurement)
SQL_TABLE_DATES =   f'CREATE TABLE  IF NOT EXISTS RecDates ('\
                    f'`Key_id` INTEGER NOT NULL UNIQUE,'\
                    f'`Date` INTEGER,'\
                    f'`Type` TEXT,'\
                    f'PRIMARY KEY (`Key_id`) );'

SQL_TABLE_CALIB_PARAM =   f'CREATE TABLE  IF NOT EXISTS Calib_params ('\
                    f'`Giv_ref` INTEGER,'\
                    f'`Date_ref` INTEGER,'\
                    f'`Range_ref` INTEGER,'\
                    f'`offset` REAL,'\
                    f'`gain` REAL,'\
                    f'FOREIGN KEY(`Giv_ref`) REFERENCES GIV_ids(`Key_id`)'\
                    f'FOREIGN KEY(`Date_ref`) REFERENCES RecDates(`Key_id`)'\
                    f'FOREIGN KEY(`Range_ref`) REFERENCES Ranges(`Key_id`)'\
                    f' );'

SQL_TABLE_MEASURES = f'CREATE TABLE  IF NOT EXISTS Measure_points ('\
                    f'`Giv_ref` INTEGER,'\
                    f'`Date_meas` TEXT,'\
                    f'`Range_ref` INTEGER,'\
                    f'`Ref_val` REAL,'\
                    f'`Meas_val` REAL,'\
                    f'FOREIGN KEY(`Giv_ref`) REFERENCES GIV_ids(`Key_id`)'\
                    f'FOREIGN KEY(`Range_ref`) REFERENCES Ranges(`Key_id`)'\
                    f' );'


DB_SYST = "sqlite3"

if "sqlite3" in DB_SYST:
    import sqlite3
else:
    import mariadb


database = None

def initialise_database( db_name):
    """ Open, initialise tables, and populate range table 
    The config file must be awailable when call this function
    """
    global database
    database = CDBManager(db_name)
    database.build_database()
    database.populate_database()
    return database

def get_database():
    return database

class CDBManager():

    def __init__(self, name, user='root', password='', host='localhost', port=3306 ):
        self.connector = None
        self.cursor = None
        self.curdir = os.path.abspath(os.getcwd())
        self.name = name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        # Attributes specifics to the schema of the database
        self.giv_key = None # key_id of Actual selected GIV
        self.range_key = None # key_id of Actual range

    def connect(self):
        if self.connector is not None: # Already connected
            return

        if "sqlite3" in DB_SYST:
            self.connector = sqlite3.connect(self.curdir+'\\'+self.name+'.db3')
        else:
            self.connector = mariadb.connect(user=self.user, password=self.password, 
                    host=self.host , port=self.port, database=self.name)
        self.cursor = self.connector.cursor()
        return self.connector

    def close(self):
        self.connector.close()
        self.connector = None
    

    def register_giv(self, giv_id):
        """ register the GIV id and note its primary key 
        to simplifie the next request 
        """
        giv_id = giv_id.replace(' ','') # Erase spaces
        self.connect()
        #self.cursor = self.connector.cursor()
        sqlcmd = "INSERT INTO GIV_ids (Giv_id) VALUES ('{}');".format(giv_id) 
        #self.cursor.execute(sqlcmd)
        self.exec_insert_ignore_unique(sqlcmd)
        self.connector.commit()
        sqlcmd = "SELECT Key_id FROM GIV_ids WHERE GIV_id = '{}';".format(giv_id)
        cur = self.connector.execute(sqlcmd)
        self.giv_key = cur.fetchone()[0]
        print ("Giv key:{}".format(self.giv_key ))


    def register_range(self, range_name):
        """ Note the range (french header) and set it's id to record the next measures  
        """
        self.connect()
        sqlcmd = "SELECT key_id FROM Ranges WHERE Gamme = '{}';".format(range_name)
        cur = self.cursor.execute(sqlcmd)
        self.range_key = cur.fetchone()[0]
        print ("Range key:{}".format(self.range_key))

    def register_measure(self, ref, meas):
        """ Note the ref and measured value for the last register GIV_id and Range 
        The date field is auto-filled 
        """
        self.connect()
        sqlcmd = "INSERT INTO Measure_points (Giv_ref, Date_meas, Range_ref, Ref_val, Meas_val) VALUES("\
                 "{}, datetime('now'), {}, {}, {});".format(self.giv_key, self.range_key, ref, meas)
        res = self.connector.execute(sqlcmd)
        self.connector.commit()


    def get_dates_of_measures_for_registrered_Giv(self):
        """ Return the list of measures dates grouped by days for this device  """
        self.connect()
        sqlcmd = "SELECT DATE(Date_meas) FROM Measure_points, GIV_ids "\
                 "WHERE Key_id={} GROUP BY DATE(Date_meas) ORDER BY Date_meas;".format(self.giv_key)
        cur = self.cursor.execute(sqlcmd)
        dates = cur.fetchall()
        return dates


    def get_ranges_of_measures_by_date_for_registrered_Giv(self,date):
        """ Return the list of ranges for one date and one GIV   """
        self.connect()
        sqlcmd = "SELECT Range_ref, Range FROM Measure_points,Ranges WHERE "\
                 "Giv_ref = {} AND DATE(Date_meas)= '{}' AND Range_ref = Ranges.Key_id"\
                 " GROUP BY Range_ref ORDER BY Range_ref;".format(self.giv_key,
                 date)
        cur = self.cursor.execute(sqlcmd)
        rec_result = cur.fetchall()
        return (rec_result)   # Typiquely: [0]: (1, 'Output current'), [1]: (2, 'Output 0-100mV)  ...

    def get_measures_by_range_date_giv_id(self, date, range_id):
        """ Return the list of the measures for one day and one range. If there are many measures
        on the same, day, we return only the most recents one (with group by)
        """
        self.connect()
        sqlcmd = "SELECT MAX(Date_meas), Range_ref, Ref_val, Meas_val FROM Measure_points WHERE "\
                 "Giv_ref = {} AND DATE(Date_meas)= '{}' AND Range_ref = {}"\
                 " GROUP BY Range_ref, Ref_val ORDER BY Range_ref, Ref_val, Date_meas;".format(self.giv_key,
                 date, range_id)
        cur = self.cursor.execute(sqlcmd)
        rec_result = cur.fetchall()
        return (rec_result)   # Typiquely: [0]:


    def exec_insert_ignore_unique(self, sqlcmd):
        ex= None
        if "sqlite3" in DB_SYST:
            try: 
                self.connector.execute(sqlcmd)       # Add the component to the database
            except sqlite3.IntegrityError as ex: 
                if not 'UNIQUE constraint' in ex.args[0]: # try to duplicate a  entry is not realy  an error  
                    print(f"Error: {ex}")
            except sqlite3.Error as ex:
                    print(f"Error: {ex}")
        else:
            pass  # Complete here for maria or others 


    def populate_database(self):
        """ Fill the ranges tables with ranges in Yaml file """
        """ Append minimal informations to check DB """
        cfg_ranges = get_config_ranges()
        for range, range_data in cfg_ranges.items():
            # Check for 'active' and 'calibrate' key if exist
            if 'active' in range_data and range_data['active']:
                to_cal= 1 if 'calibrate' in range_data and range_data['calibrate'] else 0
                sql = "INSERT INTO `Ranges` (Gamme, Range, To_calibrate) VALUES"\
                      "( '{}', '{}', {} );".format(range, range_data['english_name'], to_cal) 

                self.exec_insert_ignore_unique(sql)
        sql = "INSERT INTO GIV_ids (Giv_id) VALUES ('GIV_000.001');"
        self.exec_insert_ignore_unique(sql)
        self.connector.commit()


    def build_database(self):
        self.connect()
        self.cursor.execute(SQL_TABLE_GIV_IG)   # Create Giv_id
        self.cursor.execute(SQL_TABLE_RANGES)   # Create Ranges
        #self.cursor.execute(SQL_TABLE_DATES)    # Create Dates
        self.cursor.execute(SQL_TABLE_CALIB_PARAM)    # Create Dates
        self.cursor.execute(SQL_TABLE_MEASURES)    # Create Dates
        self.connector.commit()



if __name__ == "__main__":
    db = CDBManager('AP3reports_rec')
    db.connect()
    db.build_database()

    cfg_object = create_config_file_instance()   # Read config file and create an instance
    if cfg_object.config == None: # There is an error in config file
        msg_dialog_Error("Chargement du fichier de configuration impossible.",
            "Vérifier la présence et la cohérence de benchconfig.yaml",
            cfg_object.strerr)
        
        sys.exit(1)
    db.populate_database()
    db.register_giv('494.647')
    #db.register_range('Sortie tension 0..100mV')
    #db.register_measure(0.002, 0.00234)
    dates = db.get_dates_of_measures_for_registrered_Giv()
    date = dates[0][0]
    ranges_rec = db.get_ranges_of_measures_by_date_for_registrered_Giv(date)
    range_id = ranges_rec[0][0]
    range_id = 5 # To check doublons range
    meas_rec = db.get_measures_by_range_date_giv_id(date, range_id)
    db.close()



"""  Exemple de requete possible Si on ne cherche pas l'optimisation
INSERT INTO Measure_points (Giv_ref, Date_meas, Range_ref, Ref_val, Meas_val) VALUES(
(select Key_id from GIV_ids WHERE Giv_id='GIV_000.001'),
date('now'),
(SELECT Key_id from Ranges where Gamme='Sortie tension 0..100mV'),
0.002, 
0.0033 );
"""
""" Affichage tous les points d'un jour par Range,Ref_val, et date 
SELECT Date_meas, Range, Range_ref, Ref_val, Meas_val FROM Measure_points, 
Ranges WHERE Giv_ref = 2 AND DATE(Date_meas)= '2022-01-06' AND 
Measure_points.Range_ref=Ranges.Key_id ORDER BY Range_ref, Ref_val, Date_meas;
"""

