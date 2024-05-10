#!/usr/bin/python3

import os
import pickle
import sys
import json
import redis
import time

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

from data_operations import Data
data = Data()

cont = {}
alarms = {}

kf = key_format = "\033[1;32m"
vf = value_format = "\033[1;34m"
hf = "\033[95m"
gf = "\033[92m"
rf = "\033[91m"

term = "\n"

def dprint(d,key_format,value_format,term):
    for key in d.keys() :
        print (f"{key_format}{key :>20}: {value_format}{d[key] :<20}",end=term)

def dprint2(d,key_format,value_format,term):
    for key in d.keys() :
        print (f"{key_format}{key}: {value_format}{d[key]}",end=term)

def dprint3(d,f,key_format,value_format,term):
    
    matched = {k:v for k,v in d.items() if f in k}
    
    dprint2(matched,key_format,value_format,term)
    print("\n\n")
  
  
        
    #for k,v in d.items():
    #     if f in k:
    #         print(k,v)

    
def xy(x,y):
    return f"\u001b[{y};{x}H"

    
def cls():
    print(f"\033c")


def main():

    t = time.time()
    

    if len(sys.argv) == 2:
        v  = sys.argv[1]
        v2 = ''
        run = 1
        
    elif len(sys.argv) > 2:
       v  = sys.argv[2]
       v2 = sys.argv[1] 
       
       if v2 == '-c':
           run = 10000
 
    
    r = 0
    
    while r < run:       
        
        cont = json.loads(rconn.get("cont"))

        try:
            alarms = json.loads(rconn.get("alarms2"))
        except:
            pass
            
        #print(alarms)    
        print(xy(1,15), alarms)
    
        r = r + 1
        
        if v == 'alarms':
        
            cls()
            
            col = 5

            
            try:
                
                print(xy(col   ,2), f"{kf}RMS ID: {vf}{cont['gmid']}",end=term)
                print(xy(col+20,2), f"{kf}device ID: {vf}{cont['deviceID']}",end=term)
                print(xy(col+40,2), f"{kf}Version: {vf}{cont['version']}",end=term)
                print(xy(col+60,2), f"{kf}S/N: {vf}{cont['serial']}",end=term)
                print(xy(col+80,2), f"{kf}IP: {vf}{cont['local_ip']}",end=term)
                
                col = 10
                
                print(xy(col,4), f"{hf}Vitals:")
                
                print(xy(col,6),  f"{kf}Pressure......: {vf}{cont['pressure']}",end=term)
                print(xy(col,7),  f"{kf}Runs..........: {vf}{cont['runcycles']}",end=term)
                print(xy(col,8),  f"{kf}Mode..........: {vf}{cont['mode']}",end=term)
                print(xy(col,9),  f"{kf}Faults........: {vf}{cont['faults']}",end=term)
                print(xy(col,10), f"{kf}Current.......: {vf}{cont['current']}",end=term)
                print(xy(col,11), f"{kf}Hydrocarbon %.: {vf}{cont['hydrocarbons']}",end=term)
                print(xy(col,11), f"{kf}Temperature...: {vf}{cont['temp']}",end=term)

                
                col = 36
                        
                print(xy(col,4), f"{hf}Alarms:")

                print(xy(col,6), f"{kf}Vac Pump.........: {vf}{alarms['vac_pump_alarm']}",end=term)
                print(xy(col,7), f"{kf}Pressure Sensor..: {vf}{alarms['press_sensor_alarm']}",end=term)
                print(xy(col,8), f"{kf}Digital Storage..: {vf}{alarms['sd_card_alarm']}",end=term)
                print(xy(col,9), f"{kf}Overfill.........: {vf}{alarms['overfill_alarm']}",end=term)
                print(xy(col,10), f"{kf}Maintenance......: {vf}{alarms['maint_alarm']}",end=term)
                print(xy(col,11), f"{kf}Shutdown.........: {vf}{alarms['shutdown_alarm']}",end=term)

                col = 64
                
                print(xy(col,4), f"{hf}Pressure Alarms:")
            
                print(xy(col,6), f"{kf}Low Pressure...: {vf}{alarms['low_pressure_alarm']}",end=term)
                print(xy(col,7), f"{kf}High Pressure..: {vf}{alarms['high_pressure_alarm']}",end=term)
                print(xy(col,8), f"{kf}Var Pressure...: {vf}{alarms['var_pressure_alarm']}",end=term)
                print(xy(col,9), f"{kf}Zero Pressure..: {vf}{alarms['zero_pressure_alarm']}",end=term)

                print(xy(1,15))
                
            except:
            
                print(xy(1,20), alarms)
                
            
        elif v == '--raw':
        
            print(f'{cont}\n\n')
            
        
        elif v == '--like':
        
            f = sys.argv[2]
            dprint3(cont,f,key_format,value_format,", ")
            
             
             
        elif v == '--all':

            dprint2(cont,key_format,value_format,", ")

            print("\n\n")

            dprint2(alarms,key_format,value_format,", ")

            print("\n\n")
                    
            
        elif v == '--all_v':
        
            dprint(cont,key_format,value_format,term)
            dprint(alarms,key_format,value_format,term)
            
            print("\n\n")

            #print(f'All Keys w/values (pretty):\n\n {json.dumps(cont, indent=4)}')

        else:
        
            key_to_extract = {v}

                        
            if v in cont:
            
                new = {key: cont[key] for key in key_to_extract}
                dprint(new,key_format,value_format,term)
                #print(f"{key}:{cont[key]}")
                
            else:
                print(f"Key Not found: {key}.  \nAll Keys: {cont.keys()}")
                

                
        if v2 != '-c':
            break
                
        time.sleep(1)
            
if __name__ == '__main__':
    
    main()
