'''
event.py

a module that works in conjunction with control.py to transfer the event data to soracom

version: EV-100.101

works with CSX-102-100 and above


'''

import time
import json
import redis, csv, json, requests,os
import subprocess

### Added Time stamps in 101
from get_auth import get_auth 
from dateutil import tz
from datetime import datetime

timer = 15

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

cont = {}
alarms = {}
old_cont = {}
old_alarms = {}

DEBUGGING = False
HOUR47 = 47*60*60

api_key, token = get_auth()

headers = {
        'Accept': 'application/json',
        'X-Soracom-Api-Key': api_key,
        'X-Soracom-Token': token
    }

def save_alarms(alarms):

    rconn.set("alarms",json.dumps(alarms))
    #print(f'After Saved:\n{rconn.get("alarms")}')


def get_redis():
    cont = json.loads(rconn.get("cont"))
    alarms= json.loads(rconn.get("alarms"))

    #print(f'From Control:\n{rconn.get("alarms")}')
    
    return cont, alarms


def get_time():

    for i in range(0,9):
        modem_str = f'sudo mmcli -m {i} --time -J'

        if DEBUGGING:
            print(modem_str)
        
        returned = subprocess.getoutput(f'sudo mmcli -m {i} --time -J')
        if DEBUGGING:
            print(returned)
        
        if returned[0:5] != "error":
            modem = json.loads(returned)
            break


    json_formatted_str = json.dumps(modem, indent=4)
    if DEBUGGING:
        print(json_formatted_str)

    return modem


def get_modem():

    for i in range(0,9):
        modem_str = f'mmcli -m {i} -J'

        if DEBUGGING:
            print(modem_str)
        
        returned = subprocess.getoutput(f'mmcli -m {i} -J')
        if DEBUGGING:
            print(returned)
        
        if returned[0:5] != "error":
            modem = json.loads(returned)
            break


    json_formatted_str = json.dumps(modem, indent=4)
    if DEBUGGING:
        print(json_formatted_str)

    return modem

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


def save_sd_card(to_file,alarms):

    '''

    Write data to a file on SD Card or Flash

    '''

    header = "GMID,Seq,UST Pressure,Runcycles,Faults,Mode,Temp,Current,DevID,Local Datetime, UTC Datime\n"


    Eastern_tz = tz.gettz('EST5EDT')
    UTC_tz = tz.tzutc()
    
    dt  = datetime.now()
    dt_utc = datetime.now(tz=UTC_tz)
    
    to_file['dt'] = dt.strftime("%m/%d/%Y %H:%M:%S")
    to_file['utc'] = dt_utc.strftime("%m/%d/%Y %H:%M:%S")
    
    
    try:

        directory = delete_duplicate_data_folder()
        path = f"{directory}/logfile.csv"
        
        g = open(f"{directory}/logfile.json","a")

    except:
        #logging.error("USB Flash media not found.")
        alarms['sd_card_alarm'] = True
        #beep()
        
    else:

        if not os.path.exists(path):
            f = open(f"{directory}/logfile.csv","a")
            f.write(header)
            f.close()

        f = open(f"{directory}/logfile.csv","a")       

        csv_writer = csv.writer(f)
        csv_data = csv_writer.writerow(to_file.values())

        g.write(f'{to_file}\n')
        g.close()
        f.close()

        alarms['sd_card_alarm'] = False


    rconn.set("alarms",json.dumps(alarms))
    #print(f'After SAve:\n{rconn.get("alarms")}')
    #print(f'{alarms}')


def save_local_file(local_file):

    '''
    
    Write data to a file on local drive

    '''

    #cont, alarms = get_redis()

    f_local = open("/home/pi/python/logfile.csv","a")

    Eastern_tz = tz.gettz('EST5EDT')
    UTC_tz = tz.tzutc()
    
    dt  = datetime.now()
    dt_utc = datetime.now(tz=UTC_tz)
    
    local_file['dt'] = dt.strftime("%m/%d/%Y %H:%M:%S")
    local_file['utc'] = dt_utc.strftime("%m/%d/%Y %H:%M:%S")

    csv_writer = csv.writer(f_local)
    csv_data = csv_writer.writerow(local_file.values())
   
    f_local.close()        


def transmit_data(cont,alarms):

    '''
    Send the current data to Soracom

    '''

    pressure = round(cont['pressure'],2)
    current = round(cont['current'],2)
    hc = round(cont['hydrocarbons'],2)

    payload = {'id' : cont['gmid'],'s':cont['seq'], 'p':pressure, 'r':cont['runcycles'], 'f':cont['faults'], 'm':cont['mode'], 't':hc, 'c':current}

    print(payload)
    
    try:
        response = requests.post('mqtt://beam.soracom.io:1883', data=json.dumps(payload), headers=headers, timeout=5)
        #response = requests.post("http://unified.soracom.io", data=json.dumps(payload), headers=headers, timeout=5)
    except:
    
    # requests.exceptions.ConnectTimeout:
        print("Error: Connection timeout. Is the modem connected?")
 
    save_local_file(payload)
    save_sd_card(payload,alarms)



def main():

    cnt = 1
    
    cont,alarms = get_redis()

    if 'debugging' not in cont:
        DEBUGGING = False
        cont['debugging'] = DEBUGGING
    else:
        DEBUGGING = cont['debugging']

    modem = get_modem()
    this_time = get_time()

    rconn.set("modem",json.dumps(modem))
    rconn.set('time',json.dumps(this_time))

    signal_quality = modem['modem']['generic']['signal-quality']['value']
    access_tech = modem['modem']['generic']['access-technologies'][0]
    power_state = modem['modem']['generic']['power-state']
    state = modem['modem']['generic']['state']
    imei = modem['modem']['3gpp']['imei']
    tm = this_time['modem']['time']['current']
    
    print(f'Access Tech: {access_tech}')
    print(f'Power State: {power_state}')
    print(f'State: {state}')
    print(f'Signal Quality: {signal_quality}')
    print(f'Current Time: {tm}')
    print(f'IMEI: {imei}')
    

    while True:
        print(f"Transmitting...{cnt}" )
        
        #  The line below grab the prior controller and alarms and retain for comparison
        old_cont = cont
        old_alarms = alarms
        
        event = False
        
        cont,alarms = get_redis()
        
        if ((cont['profile'] == 8 or cont['profile'] == 12) and (alarms['shutdown_alarm_time'] > 0)):
        
            shutdown_time = time.time() - alarms['shutdown_alarm_time']
    
            if shutdown_time > HOUR47:
            
                event = True

        if cont['faults'] != old_cont['faults']:         
                
            if alarms['overfill_alarm'] or \
                alarms['vac_pump_alarm'] or \
                alarms['maint_alarm'] or \
                alarms['press_sensor_alarm']:
                    
                    event = True
            
                
        if event:
            transmit_data(cont, alarms)
                    
            if DEBUGGING:
                print(c"Controller:\n{cont}")
                print(f"Alarms\n{alarms}")
            

        cnt+=1
        print(f'Timer = {timer}')
        time.sleep(timer)

if __name__ == '__main__':
    DEBUGGING = False
    main()