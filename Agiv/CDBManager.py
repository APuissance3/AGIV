# This Python file uses the following encoding: utf-8
# """ Store the calibration and measure records in a database """

import sys
#import pathlib
import os
try:
    from .CConfigFile import create_config_file_instance, get_config_ranges
    from .Utilities import *

except Exception as ex:
    from CConfigFile import create_config_file_instance, get_config_ranges
    from Utilities import *

from datetime import date



"""  Requete qui marche:
 Note: pour Sqlite la primary key est toujours AUTO_INCREMENT. Il faut supprimer le mot clé 
"""
SQL_TABLE_GIV_IG =  f'CREATE TABLE  IF NOT EXISTS GivIds ('\
                    f'KeyId SERIAL,'\
                    f'GivId TEXT UNIQUE,'\
                    f'PRIMARY KEY (KeyId) );'

SQL_TABLE_CALIBRATOR_DATA = f'CREATE TABLE  IF NOT EXISTS Calibrator_info ('\
                    f'KeyId SERIAL ,'\
                    f'Name TEXT,'\
                    f'SN TEXT,'\
                    f'CalDate TEXT,'\
                    f'MeasDate TEXT,'\
                    f'CalReport TEXT, '\
                    f'UNIQUE (SN, CalDate, MeasDate),'\
                    f'PRIMARY KEY (KeyId) );'

SQL_TABLE_RANGES =  f'CREATE TABLE  IF NOT EXISTS Ranges ('\
                    f'KeyId SERIAL,'\
                    f'Range TEXT,'\
                    f'Gamme TEXT UNIQUE,'\
                    f'ToCalibrate INTEGER,'\
                    f'fullscale REAL,'\
                    f'tolerance REAL,'\
                    f'digitNb REAL,'\
                    f'PRIMARY KEY (KeyId) );'

# Date type: Lock or Record (calibration or measurement)
SQL_TABLE_DATES =   f'CREATE TABLE  IF NOT EXISTS RecDates ('\
                    f'KeyId SERIAL,'\
                    f'GivId TEXT,'\
                    f'Date TEXT,'\
                    f'Type TEXT,'\
                    f'UNIQUE (Date, Type),'\
                    f'PRIMARY KEY (KeyId) );'
                    

SQL_TABLE_CALIB_PARAM =   f'CREATE TABLE  IF NOT EXISTS Calib_params ('\
                    f'GivRef INTEGER,'\
                    f'DateRef INTEGER,'\
                    f'RangeRef INTEGER,'\
                    f'zoffset REAL,'\
                    f'gain REAL,'\
                    f'DateRec TEXT,'\
                    f'FOREIGN KEY(GivRef) REFERENCES GivIds (KeyId),'\
                    f'FOREIGN KEY(DateRef) REFERENCES RecDates (KeyId),'\
                    f'FOREIGN KEY(RangeRef) REFERENCES Ranges (KeyId)'\
                    f' );'

SQL_TABLE_MEASURES = f'CREATE TABLE  IF NOT EXISTS Measure_points ('\
                    f'GivRef INTEGER,'\
                    f'StartKey INTEGER,'\
                    f'DateMeas timestamp,'\
                    f'RangeRef INTEGER,'\
                    f'RefVal REAL,'\
                    f'MeasVal REAL,'\
                    f'FlgKo INTEGER,'\
                    f'FOREIGN KEY(GivRef) REFERENCES GivIds (KeyId),'\
                    f'FOREIGN KEY(RangeRef) REFERENCES Ranges (KeyId)'\
                    f' );'

SQL_TABLE_MEASURE_START = f'CREATE TABLE  IF NOT EXISTS Measure_Start ('\
                    f'KeyId SERIAL,'\
                    f'StartDate TEXT,'\
                    f'PRIMARY KEY (KeyId) );'

DB_SYST = "postgreSQL"

if "sqlite3" in DB_SYST:
    import sqlite3
else:
    import psycopg2


database = None

def initialise_database( db_name):
    """ Open, initialise tables, and populate range table 
    The config file must be awailable when call this function
    """
    global database
    database = CDBManager(db_name) if "sqlite3" in DB_SYST else \
               CDBManager('etalonnage','utllafond','ELA.AP3saucats', host='10.41.33.97', port='5432')
    database.build_database()
    database.populate_database()
    return database

def get_database():
    return database

class CDBManager():

    def __init__(self, name='etalonnage', user='root', password='', host='localhost', port=3306 ):
        self.connector = None
        self.cursor = None
        self.curdir = os.path.abspath(os.getcwd())
        self.name = name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        # Attributes specifics to the schema of the database
        self.giv_key = None # KeyId of Actual selected GIV
        self.GivId =  None
        self.range_key = None # KeyId of Actual range
        self.newcaldate = None # Actual date KeyId that we adjust GIV
        self.lockdate = None # Registered date of the last calibration in the GIV
        self.start_key = None # KeyId of the measure date starting


    def connect(self):
        if self.connector is not None: # Already connected
            return

        if "sqlite3" in DB_SYST:
            local_db_file = get_Agiv_dir()+'\\'+self.name+'.db3'
            self.connector = sqlite3.connect(local_db_file)
        else:
            self.connector = psycopg2.connect(user=self.user, password=self.password, 
                    host=self.host , port=self.port, database=self.name)
        self.cursor = self.connector.cursor()
        return self.connector

    def close(self):
        self.connector.close()
        self.connector = None
    
    def register_Aoip_in_DB(self, *aoip_datas):
        """ register AOIP datas with the actual date and S/N for key """
        self.connect()
        #self.cursor = self.connector.cursor()
        sqlcmd = "INSERT INTO Calibrator_info (MeasDate, Name, SN, CalDate, CalReport)"\
                    "VALUES (date('now'), '{}','{}','{}','{}') ON CONFLICT DO NOTHING;".format(
                        aoip_datas[0][0],
                        aoip_datas[0][1],
                        aoip_datas[0][2],
                        aoip_datas[0][3]                     
                    )

        cur = self.cursor.execute(sqlcmd)
        self.connector.commit()                     

    def set_default_giv_key(self, key):
        self.giv_key = key

    def get_db_date(self):
        self.connect()
        sqlcmd = "SELECT (to_char(NOW() AT TIME ZONE 'Europe/Paris','YYYY_MM_DD_HH24hMI'));"
        cur = self.cursor.execute(sqlcmd)
        res = self.cursor.fetchone()
        return res[0]
       

    def get_aoip_info(self, date):        
        """ Get info for the AOIP registered at the date """
        ret =('Unknown','N/A','N/A')
        sqlcmd = "SELECT Name, SN, CalDate FROM Calibrator_info WHERE MeasDate = '{}';"\
                    .format(date)
        curs = self.cursor.execute(sqlcmd)
        res = self.cursor.fetchone()
        if res is not None and len(res)>0:
            ret =  (res[0],res[1],res[2])
        return ret
        
    def retrive_giv_list(self):
        """ Get list of Giv identifier and there KeyId """ 
        self.connect()
        sqlcmd = f"SELECT KeyId, GivId, DateMeas FROM GivIds, Measure_points "\
                  "WHERE GivId IS NOT 'None' AND KeyId = GivRef;"
        cur = self.cursor.execute(sqlcmd)
        self.giv_key = self.cursor.fetchall()

    def register_giv(self, GivId):
        """ register the GIV id and note its primary key 
        to simplifie the next request 
        """
        self.connect()
        sqlcmd = f"INSERT INTO GivIds (GivId) VALUES ('{GivId}') ON CONFLICT (GivId) DO NOTHING;"
        self.cursor.execute(sqlcmd)
        #self.exec_insert_ignore_unique(sqlcmd)
        self.connector.commit()
        self.GivId = GivId    # Memorisation of the GIV ID
        self.giv_key = self.get_giv_key(GivId)
        return self.giv_key



    def get_giv_key(self, GivId):
        self.connect()
        sqlcmd = f"SELECT KeyId FROM GivIds WHERE GivId = '{GivId}';"
        cur = self.cursor.execute(sqlcmd) 
        cur = self.cursor       
        try:
            # modif 26/08 (self.giv_key, self.GivId) = self.cursor.fetchone()
            self.giv_key = self.cursor.fetchone()[0]  # Une seul colone
            print ("Giv key:{}".format(self.giv_key ))
        except:
            print (f"GIV {GivId} not found.")
            self.giv_key = None
        return self.giv_key


    def register_giv_last_cal_date(self, date, GivId):
        """ Add the calibration date of the GIV 
        and get this KeyId 
        """
        self.connect()
        sqlcmd = f"INSERT INTO RecDates (Date, GivId, Type) "\
                 f"VALUES ('{date}','{GivId}','LOCK' ) ON CONFLICT DO NOTHING;" 
        curs = self.cursor.execute(sqlcmd)
        self.connector.commit()
        sqlcmd = f" SELECT KeyId FROM RecDates WHERE Date = '{date}' AND Type='LOCK';"
        curs = self.cursor.execute(sqlcmd)
        res = self.cursor.fetchone()
        self.lockdate = res[0]

    def retrive_giv_last_cal(self, GivId):
        self.connect()
        sqlcmd = f" SELECT Date FROM RecDates WHERE (GivId = '{GivId}' AND Type='LOCK') ORDER BY KeyId DESC;"
        curs = self.cursor.execute(sqlcmd)
        res = self.cursor.fetchone()
        self.lockdate = res[0] if res != None else "Unknown"
        return self.lockdate

        
    def register_now_cal_date(self):
        """ Add the actual measurement date of the GIV 
        """
        self.connect()
        sqlcmd = "INSERT INTO RecDates (Date, Type, GivId) "\
                    f"VALUES (date('now'),'MEAS', '{self.GivId}') ON CONFLICT DO NOTHING;"
        curs = self.cursor.execute(sqlcmd)
        self.connector.commit()
        sqlcmd = "SELECT KeyId FROM RecDates WHERE Date = '{}' AND Type ='MEAS';"\
                    .format(date.today().strftime('%Y-%m-%d'))
        curs = self.cursor.execute(sqlcmd)
        res = self.cursor.fetchone()
        self.newcaldate = res[0]



    def register_range(self, range_name):
        """ Note the range (french header) and set it's id to record the next measures  
        """
        self.connect()
        sqlcmd = "SELECT keyId FROM Ranges WHERE Gamme = '{}';".format(range_name)
        self.cursor.execute(sqlcmd)
        self.range_key = self.cursor.fetchone()[0]
        print ("Range key:{}".format(self.range_key))


    def get_range_fullscale(self, range_key):
        self.connect()
        sqlcmd = f"SELECT fullscale FROM Ranges WHERE KeyId = {range_key}"
        cur = self.cursor.execute(sqlcmd)
        fs = self.cursor.fetchone()[0]
        return fs


    def register_measure_start(self):
        """ Note the date and time of the starting of measures. Return the KeyId of this start 
        permits to show multiples measures session in one Excel sheet """
        self.connect()
        sqlcmd = "INSERT INTO Measure_Start (StartDate) VALUES(NOW() AT TIME ZONE 'Europe/Paris') RETURNING KeyId;"
        self.cursor.execute(sqlcmd)
        self.start_key = self.cursor.fetchone()[0]
        self.connector.commit()
        pass



    def register_measure(self, ref, meas, ko):
        """ Note the ref and measured value for the last register GivId and Range 
        The date field is auto-filled 
        """
        self.connect()
        ko_val = 1 if ko else 0  # Conversion bool / integer
        sqlcmd = f"INSERT INTO Measure_points (GivRef, StartKey, DateMeas, RangeRef, RefVal, MeasVal, FlgKo) VALUES("\
                 f"{self.giv_key}, {self.start_key}, NOW() AT TIME ZONE 'Europe/Paris',"\
                 f" {self.range_key}, {ref}, {meas}, {ko_val}) ON CONFLICT DO NOTHING;"
        res = self.cursor.execute(sqlcmd)
        self.connector.commit()

    def register_ajustments(self, offset, gain, flg_wr=False):
        """ register Z and G for a range 
        """
        self.connect()
        date_key = self.newcaldate if flg_wr else self.lockdate
        sqlcmd = "INSERT INTO Calib_params (GivRef, DateRef, RangeRef, zoffset, gain, DateRec) VALUES("\
                 "{}, {}, {}, {:.06f}, {:.06f}, NOW() AT TIME ZONE 'Europe/Paris') ON CONFLICT DO NOTHING;".format(self.giv_key, date_key, self.range_key, offset, gain)
        res = self.cursor.execute(sqlcmd)
        self.connector.commit()



    def get_dates_of_measures_for_registrered_Giv(self, only_last = False):
        """ Return the list of measures dates grouped by days for this device  """
        self.connect()
        strdates = []
        """ 30/08/2023
        sqlcmd = "SELECT DATE(DateMeas) FROM Measure_points, GivIds "\
                    f"WHERE KeyId={self.giv_key} GROUP BY DATE(DateMeas) ORDER BY DateMeas DESC;"
        """
        sqlcmd = f"SELECT  to_char(DateMeas,'YYYY-MM-DD') as day FROM Measure_points "\
                 f"WHERE (Measure_points.GivRef = {self.giv_key}) "\
                 f"GROUP BY day ORDER BY day DESC;"
        print(sqlcmd)
        cur = self.cursor.execute(sqlcmd)        
        #strdates = self.cursor.fetchone()[0] if only_last else self.cursor.fetchall()[0]
        if only_last:
            strdates = self.cursor.fetchone()[0]
            #strdates = strdates[0]
        else:
            raw_dates = self.cursor.fetchall()
            for date in raw_dates:
                strdates.append(date[0])    # Use only 1st column of the results
        return strdates

    def get_measure_sequences_by_date_for_registered_Giv(self ,date, only_last = False):
        """ Return the Start_keys for a Giv at one date """
        self.connect()
        sqlcmd = "SELECT StartKey, to_char(MAX(DateMeas),'YYYY-MM-DD HH24:MI') FROM Measure_points "\
                 f"WHERE GivRef = {self.giv_key} AND DATE(DateMeas)= '{date}'"\
                 " GROUP BY StartKey ORDER BY StartKey DESC;"
                 # Test 19/09/2023 " GROUP BY StartKey ORDER BY StartKey DESC;"
        cur = self.cursor.execute(sqlcmd)
        if only_last:
            starts = self.cursor.fetchone() 
        else:
            starts= self.cursor.fetchall()
        return starts

    def get_ranges_of_measures_by_date_and_start_for_registrered_Giv(self, date, start_key = None):
        """ Return the list of ranges for one date and one GIV   """
        self.connect()
        sql_start_key = f" AND StartKey = {start_key}" if start_key != None else ""
        sql_group = f" ,StartKey " if start_key != None else ""
        sqlcmd = "SELECT RangeRef, Range FROM Measure_points,Ranges WHERE "\
                 f"GivRef = {self.giv_key} AND DATE(DateMeas)= '{date}' "\
                 f"AND RangeRef = Ranges.KeyId AND RangeRef = Ranges.KeyId " + sql_start_key + \
                 " GROUP BY RangeRef, Range, StartKey "\
                 " ORDER BY RangeRef ASC, StartKey DESC;"
                 #" GROUP BY RangeRef ORDER BY RangeRef ASC, StartKey DESC;"
        cur = self.cursor.execute(sqlcmd)
        rec_result = self.cursor.fetchall()
        return (rec_result)   # Typiquely: [0]: (1, 'Output current'), [1]: (2, 'Output 0-100mV)  ...
    
    def get_ranges_of_measure_by_giv_key_for_a_date(self, giv_key, date):
        """ Return list of measured range for one Giv at one date """
        sqlcmd = "SELECT RangeRef, Range FROM Measure_points, Ranges WHERE"\
                 f" GivRef = {giv_key} AND DATE(DateMeas) = '{date}' GROUP BY RangeRef"
        cur = self.cursor.execute(sqlcmd)
        rec_result = self.cursor.fetchall()
        return (rec_result)  

    def get_all_givs_and_last_measures_dates(self):
        sqlcmd = "SELECT KeyId, GivId,  MAX(to_char(DateMeas,'YYYY/MM/DD')) AS mes_date FROM GivIds, Measure_points "\
                 "WHERE GivId IS NOT NULL AND KeyId = GivRef " \
                 " GROUP BY KeyId ORDER BY mes_date DESC;"
        cur = self.cursor.execute(sqlcmd)
        rec_result = self.cursor.fetchall()
        return (rec_result)  


    def get_measures_by_range_date_giv_id(self, date, range_id, start_key=None):
        """ Return the list of the measures for one day and one range. If there are many measures
        on the same, day, we return only the most recents one (with group by)
        """
        self.connect()
        sql_start_key = f" AND Startkey = {start_key}" if start_key != None else ""
         # 28/08-1       sqlcmd = "SELECT MAX(DateMeas), RangeRef, RefVal, MeasVal FROM Measure_points WHERE "\
         # 28/08-2       sqlcmd = "SELECT DATE(MAX(DateMeas)), RangeRef, RefVal, MeasVal FROM Measure_points WHERE "\
        """    Original
        sqlcmd = "SELECT MAX(DateMeas), RangeRef, RefVal, MeasVal, FlgKo FROM Measure_points WHERE "\
            f"GivRef = {self.giv_key} AND DATE(DateMeas)= '{date}' AND RangeRef = {range_id}"\
            + sql_start_key + " GROUP BY RangeRef, RefVal ORDER BY RangeRef, RefVal, DateMeas;"
        sqlcmd = "SELECT  to_char(MAX(DateMeas),'YYYY-MM-DD HH24:MI') as dtm,"\
             " RangeRef, RefVal, MeasVal, FlgKo FROM Measure_points WHERE "\
            f"GivRef = {self.giv_key} AND DATE(DateMeas)= '{date}' AND RangeRef = {range_id}"\
            + sql_start_key + " GROUP BY RangeRef, RefVal, MeasVal, FlgKo ORDER BY dtm;"
        """
        # On utilise une jointure avec la sous requete qui retourne les point de référence les plus récent 
        # des conditions demandées. Puis obtient le reste des infos rien que pour ces points
        sqlcmd = f"SELECT  MaxDateMeas as dtm, mp.RangeRef, mp.RefVal, mp.MeasVal, mp.FlgKo "\
                 f"FROM Measure_points mp "\
                 f"JOIN ("\
	             f"SELECT  to_char(MAX(DateMeas),'YYYY-MM-DD HH24:MI') as MaxDateMeas, RefVal FROM Measure_points "\
	             f"WHERE GivRef = {self.giv_key} AND DATE(DateMeas)= '{date}' AND RangeRef = {range_id} "\
	             f"GROUP BY RefVal "\
	             f"ORDER BY RefVal "\
                 f")J_MaxDate ON J_MaxDate.Refval = mp.RefVal "\
                 f" AND J_MaxDate.MaxDateMeas = to_char((mp.DateMeas),'YYYY-MM-DD HH24:MI') "\
                 f"WHERE GivRef = {self.giv_key} AND DATE(DateMeas)= '{date}' AND RangeRef = {range_id} "\
                 f"{sql_start_key} "\
                 f"ORDER BY dtm;"
        cur = self.cursor.execute(sqlcmd)
        rec_result = self.cursor.fetchall()
        return (rec_result)   # Typiquely: [0]:


    def exec_insert_ignore_unique(self, sqlcmd):
        ex= None
        if "sqlite3" in DB_SYST:
            try: 
                self.cursor.execute(sqlcmd)       # Add the component to the database
            except sqlite3.IntegrityError as ex: 
                if not 'UNIQUE constraint' in ex.args[0]: # try to duplicate a  entry is not realy  an error  
                    print(f"Error: {ex}")
            except sqlite3.Error as ex:
                    print(f"Error: {ex}")
        else:
            try:
                self.cursor.execute(sqlcmd)       # Add the component to the database
            except Exception as ex:
                print(f"Error: {ex}")
                pass

    def populate_database(self):
        """ Fill the ranges tables with ranges in Yaml file """
        """ Append minimal informations to check DB """
        cfg_ranges = get_config_ranges()
        for range, range_data in cfg_ranges.items():
            fs = range_data['full_scale'] if 'full_scale' in range_data else 0.0
            (tol, digitNb) = range_data['tolerance'] if 'tolerance' in range_data else (0.0, 0.0)
            # Check for 'active' and 'calibrate' key if exist
            if 'active' in range_data and range_data['active']:
                to_cal= 1 if 'calibrate' in range_data and range_data['calibrate'] else 0
                sql = "INSERT INTO Ranges (Gamme, Range, ToCalibrate, fullscale, tolerance, digitNb) VALUES"\
                      f" ( '{range}', '{range_data['english_name']}', {to_cal}, {fs}, {tol}, {digitNb} )"\
                      "ON CONFLICT DO NOTHING; "
                      # "( '{}', '{}', {} );".format(range, range_data['english_name'], to_cal)
                self.cursor.execute(sql)
                #self.exec_insert_ignore_unique(sql)
        self.connector.commit()


    def build_database(self):
        self.connect()
        sql = SQL_TABLE_GIV_IG
        self.cursor.execute(sql)   # Create GivId
        sql = SQL_TABLE_CALIBRATOR_DATA
        self.cursor.execute(sql )    # Create calibrator info
        sql = SQL_TABLE_RANGES
        self.cursor.execute(sql)   # Create Ranges
        sql = SQL_TABLE_DATES
        self.cursor.execute(sql)    # Create Dates
        sql = SQL_TABLE_CALIB_PARAM
        self.cursor.execute(sql)    # Create Dates
        sql = SQL_TABLE_MEASURES
        self.cursor.execute(sql)    # Create 
        sql = SQL_TABLE_MEASURE_START
        self.cursor.execute(sql)    # Create 
        self.connector.commit()



if __name__ == "__main__":
    #db = CDBManager('AP3reports_rec')

    db = CDBManager('etalonnage','utllafond','ELA.AP3saucats', host='10.41.33.97', port='5432')
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
    db.register_range('Sortie tension 0..100mV')
    db.register_measure(0.002, 0.00234)
    dates = db.get_dates_of_measures_for_registrered_Giv()
    date = dates[0][0]
    ranges_rec = db.get_ranges_of_measures_by_date_for_registrered_Giv(date)
    range_id = ranges_rec[0][0]
    range_id = 5 # To check doublons range
    meas_rec = db.get_measures_by_range_date_GivId(date, range_id)
    db.close()



"""  Exemple de requete possible Si on ne cherche pas l'optimisation
INSERT INTO Measure_points (GivRef, DateMeas, RangeRef, RefVal, MeasVal) VALUES(
(select KeyId from GivIds WHERE GivId='GIV_000.001'),
date('now'),
(SELECT KeyId from Ranges where Gamme='Sortie tension 0..100mV'),
0.002, 
0.0033 );
"""
""" Affichage tous les points d'un jour par Range,RefVal, et date 
SELECT DateMeas, Range, RangeRef, RefVal, MeasVal FROM Measure_points, 
Ranges WHERE GivRef = 2 AND DATE(DateMeas)= '2022-01-06' AND 
Measure_points.RangeRef=Ranges.KeyId ORDER BY RangeRef, RefVal, DateMeas;
"""

