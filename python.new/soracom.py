'''

soracom.py

a module that works in conjunction with control.py to transfer the working data to soracom

version: SOR-100.102

works with CSX-102-100 and above


'''

import time
import json
import redis, csv, json, requests,os
import subprocess
import socket 
import logging

logger = logging.getLogger("pylog")

logging.basicConfig(filename='/home/pi/python/soracom.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

### Added Time stamps in 101
from get_auth import get_auth 
from dateutil import tz
from datetime import datetime


timer = 15

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

cont = {}
alarms = {}

DEBUGGING = False
SAVING = False
EVENT_MONITORING = False

api_key, token = get_auth()

headers = {
        'Accept': 'application/json',
        'X-Soracom-Api-Key': api_key,
#        'X-soracom-imsi': {IMSI},
        'X-Soracom-Token': token
    }

def save_alarms(alarms):
    rconn.set("alarms",json.dumps(alarms))


def get_redis():
    try:
        cont = json.loads(rconn.get("cont"))
        alarms= json.loads(rconn.get("alarms"))
    except:
        cont = {}
        alarms = {}

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

    header = "GMID,Seq,UST Pressure,Runcycles,Faults,Mode,Temp,Current,Local Datetime, UTC Datime\n"

    sd_file = add_date(in_file)
    
    try:

        directory = delete_duplicate_data_folder()
        path = f"{directory}/logfile.csv"
        
        g = open(f"{directory}/logfile.json","a")

    except:
        logging.error("USB Flash media not found.")
        alarms['sd_card_alarm'] = True
        
        
        
        #beep()
        
    else:

        if not os.path.exists(path):
            f = open(f"{directory}/logfile.csv","a")
            f.write(header)
            f.close()

        f = open(f"{directory}/logfile.csv","a")       

        csv_writer = csv.writer(f)
        csv_data = csv_writer.writerow(sd_file.values())
        
        if DEBUGGING:
            print(f"Saved SD file: {sd_file}")
            print(f"Saved CSV file: {csv_data}")
        
        g.write(f'{sd_file}\n')
        g.close()
        f.close()

        alarms['sd_card_alarm'] = False

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


def get_payload(cont,alarms):


    with open('profile.json') as f:
        profile = json.load(f)
    
    pressure = round(cont['pressure'],2)
    current = round(cont['current'],2)
    temp = round(cont['temp'],2)
    
    #hc = round(cont['hydrocarbons'],2)

    payload = {'id' : cont['gmid'],'s':cont['seq'], 'p':pressure, 'r':cont['runcycles'], 'f':cont['faults'], 'm':cont['mode'], 't':temp, 'c':current, 'pr':profile}

    return payload

    
def transmit_data(payload):

    '''
    Send the current data to Soracom

    '''    
    # Soracom endpoint information
    soracom_host = 'beam.soracom.io'
    soracom_port = 23080
    
    data = json.dumps(payload)

    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Send data to Soracom
        udp_socket.sendto(data.encode(), (soracom_host, soracom_port))
        logging.info(f"Data sent to {soracom_host}:{soracom_port}")
        print(f"Data sent to {soracom_host}:{soracom_port}: {data}")
    except Exception as e:
        logging.error(f"Error sending data: {e}")
        print(f"Error sending data: {e}")
    finally:
        # Close the socket
        udp_socket.close()
        
        
    
    
    #try:
        #response = requests.post('mqtt://beam.soracom.io:1883', data=json.dumps(payload), headers=headers, timeout=5)
        #response = requests.post('http://unified.soracom.io', data=json.dumps(payload), headers=headers, timeout=15)
        #requests.post('udp://beam.soracom.io:23080', data=json.dumps(payload), headers=headers, timeout=15)
    #except:	
        #print("Error: Connection timeout. Is the modem connected?")
    #else:
        #print(f"Transmitted file: {payload}")
    


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

    transmit_duration = 15
    save_duration = 15
        
    save_time = time.time()
    transmit_time = time.time()
    
    while True:
    
        cont,alarms = get_redis()

        if DEBUGGING:
            print(cont)

        payload = get_payload(cont,alarms)

        rconn.set("payload", json.dumps(payload))
        
        if time.time() - transmit_time >= transmit_duration:
        
            ###
            ###	Event Management
            ###   * change for Event monitoring.  Only send events when there is an alarm
            ###   * Put other event related functions here
            ###
            
            if EVENT_MONITORING:
                if (cont['faults'] > 0) or (cont['mode'] > 0):
                    #print(f"Transmitting({transmit_duration})...{int(time.time())}" )
            
                    transmit_data(payload)
            else:
                transmit_data(payload)
            
            ## Always update time    
            transmit_time = time.time()
 
        if time.time() - save_time >= save_duration:

            if SAVING:
                print(f"Saving({save_duration})...{int(time.time())}")

                save_local_file(payload)
                save_sd_card(payload)
            save_time = time.time()


        time.sleep(1)

if __name__ == '__main__':
    DEBUGGING = False
    main()