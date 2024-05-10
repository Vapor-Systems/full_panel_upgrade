#!/usr/bin/python3

import os
import pickle
import sys
import json
import redis
import time
import math


rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

from data_operations import Data
data = Data()

cont = {}
alarms = {}

current_list = []
pressure_list = []
run_list = []


kf = key_format = "\033[1;32m"
vf = value_format = "\033[1;34m"
hf = "\033[95m"
gf = "\033[92m"
rf = "\033[91m"
bf = "\033[94m"
wf = "\033[97m"
yf = "\033[93m"
dbf = "\033[34m"
dgf = "\033[32m"
drf = "\033[31m"
cyf = "\033[36m"
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
    
    curr_min = 10
    curr_max = 0
    p = 0
    b = 0
    r = 0
    y = 18
    
    cls()
    
    p_str = ""
    
    while r < run:       
        
        cont = json.loads(rconn.get("cont"))

        try:
            alarms = json.loads(rconn.get("alarms2"))
        except:
            pass
            
        #print(alarms)    
        #print(xy(1,15), alarms)
    
        r = r + 1
        
        if v == 'alarms':
        
            #cls()
            
            col = 5
            row = 1
            
            
            try:
            
                x = 1
                
                
                print(xy(5,row), f"{rf}______________________________________________________________________________________",end=term)
                
                print(xy(col   ,row+2), f"{kf}RMS ID: {vf}{cont['gmid']}",end=term)
                print(xy(col+20,row+2), f"{kf}device ID: {vf}{cont['deviceID']}",end=term)
                print(xy(col+50,row+2), f"{kf}Version: {vf}{cont['version']}",end=term)
                print(xy(col+70,row+2), f"{kf}S/N: {vf}{cont['serial']}",end=term)
                print(xy(col+70,row+3), f"{kf}IP: {vf}{cont['local_ip']}",end=term)
                
                print(xy(5,row+4), f"{rf}______________________________________________________________________________________",end=term)
                
                
                col = 10
                row = 8
                
                print(xy(col,row), f"{hf}Vitals:")
                
                print(xy(col,row+1),  f"{kf}Pressure......: {vf}{cont['pressure']}",end=term)
                print(xy(col,row+2),  f"{kf}Runs..........: {vf}{cont['runcycles']}",end=term)
                print(xy(col,row+3),  f"{kf}Mode..........: {vf}{cont['mode']}",end=term)
                print(xy(col,row+4),  f"{kf}Faults........: {vf}{cont['faults']}",end=term)
                print(xy(col,row+5), f"{kf}Current.......: {vf}{cont['current']}",end=term)
                print(xy(col,row+6), f"{kf}Hydrocarbon %.: {vf}{cont['hydrocarbons']}",end=term)
                print(xy(col,row+7), f"{kf}Temperature...: {vf}{cont['temp']}",end=term)
                print(xy(col,row+8), f"{kf}Current Count.: {vf}{cont['curr_counter']}",end=term)
                
                curr_max = max(curr_max, cont['current'])
                curr_min = min(curr_min, cont['current'])
                
                    
                col = 36
                       
                print(xy(col,row), f"{hf}Alarms:")

                print(xy(col,row+1), f"{kf}Vac Pump.........: {vf}{alarms['vac_pump_alarm']}",end=term)
                print(xy(col,row+2), f"{kf}Pressure Sensor..: {vf}{alarms['press_sensor_alarm']}",end=term)
                print(xy(col,row+3), f"{kf}Digital Storage..: {vf}{alarms['sd_card_alarm']}",end=term)
                print(xy(col,row+4), f"{kf}Overfill.........: {vf}{alarms['overfill_alarm']}",end=term)
                print(xy(col,row+5), f"{kf}Maintenance......: {vf}{alarms['maint_alarm']}",end=term)
                print(xy(col,row+6), f"{kf}Shutdown.........: {vf}{alarms['shutdown']}",end=term)
                print(xy(col,row+7), f"{kf}Shutdown Stage...: {vf}{alarms['shutdown_stage']}",end=term)
                
                print(xy(col,row+8), f"{kf}MAX Current......: {vf}{curr_max}",end=term)
                

                col = 64
                
                HOURS72 = 72*60*60
                
                print(xy(col,row), f"{hf}Pressure Alarms:")
            
                if alarms['shutdown_stage'] > 0:
                
                    shut_time = (time.time()-alarms['shutdown_alarm_time'])
                    xhours,xseconds = divmod(HOURS72-shut_time,3600)
                    xminutes,xseconds = divmod(xseconds,60)
                    xtime = "{:02.0f}:{:02.0f}:{:02.0f}".format(xhours,xminutes,xseconds)                
                else:
                    xtime = "N/A"


                print(xy(col,row+1), f"{kf}Low Pressure...: {vf}{alarms['low_pressure_alarm']}",end=term)
                print(xy(col,row+2), f"{kf}High Pressure..: {vf}{alarms['high_pressure_alarm']}",end=term)
                print(xy(col,row+3), f"{kf}Var Pressure...: {vf}{alarms['var_pressure_alarm']}",end=term)
                print(xy(col,row+4), f"{kf}Zero Pressure..: {vf}{alarms['zero_pressure_alarm']}",end=term)
                print(xy(col,row+6), f"{kf}Time to Shutdwn: {vf}{xtime}",end=term)
                
                print(xy(col,row+8), f"{kf}MIN Current.....: {vf}{curr_min}",end=term)
                
                #var_pressure_time = int((time.time() - alarms['var_pressure_start'])/3600) if alarms['var_pressure_start'] > 0 else 0
                #zero_pressure_time = int((time.time() - alarms['zero_pressure_start'])/3600) if alarms['zero_pressure_start'] > 0 else 0
                #low_pressure_time = int((time.time() - alarms['low_pressure_start'])/3600) if alarms['low_pressure_start'] > 0 else 0
                #high_pressure_time = int((time.time() - alarms['high_pressure_start'])/3600) if alarms['high_pressure_start'] > 0 else 0
                var_pressure_time =  time.time()-alarms['var_pressure_start'] if alarms['var_pressure_start'] > 0 else 0
                zero_pressure_time = time.time()-alarms['zero_pressure_start'] if alarms['zero_pressure_start'] > 0 else 0
                low_pressure_time =  time.tine()-alarms['low_pressure_start'] if alarms['low_pressure_start'] > 0 else 0
                high_pressure_time = time.time()-alarms['high_pressure_start'] if alarms['high_pressure_start'] > 0 else 0
                
                
                    
                
                print(xy(col,row+10), f"{kf}Low Press Time.: {vf}{low_pressure_time}",end=term)
                print(xy(col,row+11), f"{kf}High Press Time: {vf}{high_pressure_time}",end=term)
                print(xy(col,row+12), f"{kf}Var Press Time.: {vf}{var_pressure_time}",end=term)
                print(xy(col,row+13), f"{kf}Zero Press Time: {vf}{zero_pressure_time}",end=term)
                print(xy(col,row+14), f"{kf}Time...........: {vf}{time.time()}",end=term)





                print(xy(5,row+15), f"{rf}______________________________________________________________________________________",end=term)
                
                try: mode
                except NameError: mode = 0
                
                try: step
                except NameError: step = 0
                
                y = row +17
                
                old_mode = mode
   
                mode = cont['mode']
                runs = cont['runcycles']
                
                if mode != old_mode:
                
                    ## Steps in the run cycle go from 0 to 14
                    ## determine approximaely what step we are on based on pattern
                    
                    
                    if (mode == 1 and old_mode == 0):
                        step = 0
                    
                    if (mode == 0 and old_mode == 1):
                        step = 1
                        
                    if (mode == 2 and old_mode == 0):
                        step = 2
                        
                    if (mode == 0 and old_mode == 3):
                        step = 14
                    
                    
                    if step == 0:  ##  begin
                        y = y + 1
                        if y > row + 27:
                            y=row + 17
                            
                        print(xy(step*5+5,y),f"{runs}: R",end=term)
                    
                    if step == 1:
                        
                        print(xy(step*5+12,y),f"I",end=term)
                    
                    if step == 2:
                        print(xy(step*5+12,y),f"P",end=term)
                    
                    if step == 3:
                        print(xy(step*5+12,y),f"B",end=term)
                    
                    if step == 4:
                        print(xy(step*5+12,y),f"P",end=term)
                    
                    if step == 5:
                        print(xy(step*5+12,y),f"B",end=term)
                    
                    if step == 6:
                        print(xy(step*5+12,y),f"P",end=term)
                    
                    if step == 7:
                        print(xy(step*5+12,y),f"B",end=term)
                        
                    if step == 8:
                        print(xy(step*5+12,y),f"P",end=term)
                    if step == 9:
                    
                        print(xy(step*5+12,y),f"B",end=term)
                    if step == 10:
                    
                        print(xy(step*5+12,y),f"P",end=term)
                    if step == 11:
                    
                        print(xy(step*5+12,y),f"B",end=term)
                    if step == 12:
                    
                        print(xy(step*5+12,y),f"P",end=term)
                    if step == 13:
                    
                        print(xy(step*5+12,y),f"B",end=term)
                    if step == 14:
                    
                        print(xy(step*5+12,y),f"I",end=term)
                    
                    
                    step = step + 1
                    
            except:
                
                print("Something Wrong!")
                
                
                '''
                if len(current_list) > 60:
                    del current_list[0]
                    
                current_list.append(cont['current'])
                
                print(xy(col,row+10), f"{kf}Length of List: {vf}{len(current_list)}")
                
                j = 0
                k = 0
                
                
                
                for i in range(0,len(current_list)):
                    #print(xy(5+1,20),f"{current_list}")
                    q = int(current_list[i])
                    print(xy(5+i,18+q), f"*", )
                    j = j+1
                    k = k+4 
                '''
                    
                
            
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
