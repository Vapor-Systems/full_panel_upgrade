'''

saver.py

a module that works in conjunction with control.py to save the data on local media

version: SAV-100.12

works with CSX-102-101 and above


'''

import time
import json
import redis, csv, json, requests,os
import subprocess

### Added Time stamps in 101
from get_auth import get_auth 
from dateutil import tz
from datetime import datetime

import logging

logger = logging.getLogger("pylog")
logging.basicConfig(filename='/home/pi/python/cp2.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


SAVE_DURATION = 15

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

cont = {}
alarms = {}

DEBUGGING = True


def save_alarms(alarms):
    rconn.set("alarms",json.dumps(alarms))


def get_redis():
    cont = json.loads(rconn.get("cont"))
    alarms= json.loads(rconn.get("alarms"))

    return cont, alarms


def delete_duplicate_data_folder():

    mount_point = os.listdir('/media/pi/')
    directory = []
    for x in mount_point:
        path = f'/media/pi/{x}'
        ismount = os.path.ismount (path)
        if ismount:
            directory = path
        else:
            os.system(f' sudo rm -rf {path}')
        
    if DEBUGGING:
        print(f' {path} removed')

    return directory


def add_date(payload):

    Eastern_tz = tz.gettz('EST5EDT')
    UTC_tz = tz.tzutc()
    
    dt  = datetime.now()
    dt_utc = datetime.now(tz=UTC_tz)
    
    payload['dt'] = dt.strftime("%m/%d/%Y %H:%M:%S")
    payload['utc'] = dt_utc.strftime("%m/%d/%Y %H:%M:%S")
   
    return payload
   

def save_sd_card(in_file):

    '''

    Write data to a file on SD Card or Flash

    '''

    alarms['sd_card_alarm'] = False


    header = "GMID,Seq,UST Pressure,Runcycles,Faults,Mode,Temp,Current,Local Datetime, UTC Datime\n"

    sd_file = add_date(in_file)
    
    directory = delete_duplicate_data_folder()

    print(f"Directory: {directory}")
    
    if not directory:
        alarms['sd_card_alarm'] = True
        logging.error("USB Flash media not found.")
    else:
        path = f"{directory}/logfile.csv"
        
    
        '''
        try:
            directory = delete_duplicate_data_folder()
            path = f"{directory}/logfile.csv"
            
        except:
            logging.error("USB Flash media not found.")
            alarms['sd_card_alarm'] = True

        else:
        '''

        if not os.path.exists(path):
            f = open(f"{directory}/logfile.csv","a")
            f.write(header)
            f.close()

        f = open(f"{directory}/logfile.csv","a")       

        csv_writer = csv.writer(f)
        csv_data = csv_writer.writerow(sd_file.values())
        
        if DEBUGGING:
            print(f"Saved CSV file: {csv_data}")
        
        f.close()

        #alarms['sd_card_alarm'] = False

    print(f"Alarms {alarms}")
    rconn.set("alarms",json.dumps(alarms))


def save_local_file(in_file):

    '''
    
    Write data to a file on local drive

    '''

    f_local = open("/home/pi/python/logfile.csv","a")

    local_file = add_date(in_file)
    
    csv_writer = csv.writer(f_local)
    csv_data = csv_writer.writerow(local_file.values())
    
    print(f"Saved Local file: {local_file}")
        
    f_local.close()    

    rconn.set("alarms",json.dumps(alarms))    


def get_payload(cont,alarms):

    pressure = round(cont['pressure'],2)
    current = round(cont['current'],2)
    hc = round(cont['hydrocarbons'],2)

    payload = {'id' : cont['gmid'],'s':cont['seq'], 'p':pressure, 'r':cont['runcycles'], 'f':cont['faults'], 'm':cont['mode'], 't':hc, 'c':current}

    return payload


def main():

    cnt = 1
    
    cont,alarms = get_redis()
    alarms= json.loads(rconn.get("alarms"))

    save_duration = SAVE_DURATION
    
    if 'debugging' not in cont:
        DEBUGGING = False
        cont['debugging'] = DEBUGGING
    else:
        DEBUGGING = cont['debugging']

    save_time = time.time()
    
    while True:
    
        cont,alarms = get_redis()
        alarms= json.loads(rconn.get("alarms"))

        if DEBUGGING:
            print(cont)

        payload = get_payload(cont,alarms)
        
        ###  Save data no matter what     
        if time.time() - save_time >= save_duration:
            print(f"Saving({save_duration})...{int(time.time())}")
            save_local_file(payload)
            save_sd_card(payload)
            save_time = time.time()

        time.sleep(1)

if __name__ == '__main__':
    DEBUGGING = False
    main()