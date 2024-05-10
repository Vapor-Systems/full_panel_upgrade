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

#  Get Debug Parameter, if any

import vst_secrets

secrets = vst_secrets.secrets
DEBUGGING = secrets["DEBUGGING"]

if not DEBUGGING:
    HOURS72 = 72*60*60
    HOURS4 = 4*60*60
else:
    HOURS72 = 4*60
    HOURS4 = 30



    
def xy(x,y):
    return f"\u001b[{y};{x}H"

    
def cls():
    print(f"\033c")


def x_time(t):

    xhours,xseconds = divmod(HOURS72-t,3600)
    xminutes,xseconds = divmod(xseconds,60)

    xtime = "{:02.0f}:{:02.0f}:{:02.0f}".format(xhours,xminutes,xseconds)
    
    return xtime


def y_time(t):

    xhours,xseconds = divmod(HOURS4-t,3600)
    xminutes,xseconds = divmod(xseconds,60)

    xtime = "{:02.0f}:{:02.0f}:{:02.0f}".format(xhours,xminutes,xseconds)
    
    return xtime


def z_time(t):

    xhours,xseconds = divmod(t,3600)
    xminutes,xseconds = divmod(xseconds,60)

    xtime = "{:02.0f}:{:02.0f}:{:02.0f}".format(xhours,xminutes,xseconds)
    
    return xtime
 
    
def main():

    t = time.time()
    
    run = 10000

    r = 1
    row = 0
    col = 1
    
    curr_min = 10
    curr_max = 0
    p = 0
    b = 0
    y = 18
    
    # Clear Screen
    
    cls()
    
    p_str = ""
    
    
    modem = json.loads(rconn.get("modem"))
    with open('profile.json') as f:
        profile = json.load(f)
    
    signal_quality = modem['modem']['generic']['signal-quality']['value']
    access_tech = modem['modem']['generic']['access-technologies'][0]
    power_state = modem['modem']['generic']['power-state']
    state = modem['modem']['generic']['state']
    imei = modem['modem']['3gpp']['imei']
    #tm = this_time['modem']['time']['current']
 
    
    
    
    while r < run:       
        
        cont = json.loads(rconn.get("cont"))
        
        try:
            payload = json.loads(rconn.get("payload"))
        except:
            payload = "no payload"

        try:
            alarms = json.loads(rconn.get("alarms2"))
        except:
            pass
            
        x = 1
        
        col=10
        row=1
        
        run_mode = "DEBUG MOD" if(DEBUGGING) else "NORMAL MODE"
        
        print(xy(5,row), f"{rf}______________________________________________________________________________________",end=term)
        
        print(xy(col   ,row+2), f"{kf}RMS ID: {vf}{cont['gmid']}",end=term)
        print(xy(col   ,row+3), f"{kf}Run Mode: {vf}{run_mode}",end=term)
        
        print(xy(col+20,row+2), f"{kf}device ID..: {vf}{imei}",end=term)
        print(xy(col+20,row+3), f"{kf}Sig Quality: {vf}{signal_quality}",end=term)
        
        print(xy(col+50,row+2), f"{kf}Version: {vf}{cont['version']}",end=term)
        print(xy(col+70,row+2), f"{kf}S/N: {vf}{cont['serial']}",end=term)
        print(xy(col+70,row+3), f"{kf}IP: {vf}{cont['local_ip'] }",end='')
        print(xy(col+50,row+3), f"{kf}Profile: {vf}{profile}  ",end=term)
        
        
        print(xy(5,row+5), f"{rf}______________________________________________________________________________________",end=term)
        
        
        col = 10
        row = 8
        
        print(xy(col,row), f"{hf}Vitals:")
        
        print(xy(col,row+1),  f"{kf}Pressure......: {vf}{cont['pressure']}",end=term)
        print(xy(col,row+2),  f"{kf}Runs..........: {vf}{cont['runcycles']}",end=term)
        print(xy(col,row+3),  f"{kf}Mode..........: {vf}{cont['mode']}",end=term)
        print(xy(col,row+4),  f"{kf}Faults........: {vf}{cont['faults']}",end=term)
        print(xy(col,row+5),  f"{kf}Current.......: {vf}{cont['current']}",end=term)
        print(xy(col,row+6),  f"{kf}Hydrocarbon %.: {vf}{cont['hydrocarbons']}",end=term)
        print(xy(col,row+7),  f"{kf}Temperature...: {vf}{cont['temp']}",end=term)
        print(xy(col,row+9),  f"{hf}Current: ",end=term)
        
        print(xy(col,row+10),  f"{kf}Current Count.: {vf}{cont['curr_counter']}",end=term)
        print(xy(col,row+11), f"{kf}MIN Current...: {vf}{curr_min}",end=term)
        print(xy(col,row+12), f"{kf}MAX Current...: {vf}{curr_max}",end=term)
        print(xy(col,row+13), f"{kf}ADC Chan 0....: {vf}{cont['adc_value']} ",end=term)
        print(xy(col,row+14), f"{kf}ADC Chan 2....: {vf}{cont['adc_current_chan_2']} ",end=term)
        print(xy(col,row+15), f"{kf}ADC Chan 3....: {vf}{cont['adc_current_chan_3']} ",end=term)
        print(xy(col,row+16), f"{kf}ADC Abs(2-3)..: {vf}{cont['adc_current_abs']}    ",end=term)
        
            
        curr_max = max(curr_max, cont['current'])
        curr_min = min(curr_min, cont['current'])
            
                
        col = 36
            
        if alarms['shutdown_stage'] > 0:
            
            shut_time = (time.time()-alarms['shutdown_alarm_time'])
            xtime = x_time(shut_time)
                
        else:
            xtime = "N/A"
   
               
        print(xy(col,row), f"{hf}Alarms:")

        print(xy(col,row+1), f"{kf}Vac Pump.........: {vf}{alarms['vac_pump_alarm']}",end=term)
        print(xy(col,row+2), f"{kf}Pressure Sensor..: {vf}{alarms['press_sensor_alarm']}",end=term)
        print(xy(col,row+3), f"{kf}Digital Storage..: {vf}{alarms['sd_card_alarm']}",end=term)
        print(xy(col,row+4), f"{kf}Overfill.........: {vf}{alarms['overfill_alarm']}",end=term)
        print(xy(col,row+5), f"{kf}Maintenance......: {vf}{alarms['maint_alarm']}",end=term)
        print(xy(col,row+6), f"{kf}Shutdown.........: {vf}{alarms['shutdown_alarm']}",end=term)
        print(xy(col,row+7), f"{kf}Shutdown Stage...: {vf}{alarms['shutdown_stage']}",end=term)
        print(xy(col,row+8), f"{kf}Time to Shutdwn..: {vf}{xtime}",end=term)
        
        col = 33

        print(xy(col,row+10), f"{kf}   Test Mode........: {vf}{cont['test_mode']} ",end=term)
        print(xy(col,row+11), f"{kf}     Test High Limit: {vf}{cont['rc_high_limit']}",end=term)
        print(xy(col,row+12), f"{kf}     Test Low Limit.: {vf}{cont['rc_low_limit']}",end=term)
        
       
        et_time = int(time.time() -alarms['test_start_timer']) if alarms['test_start_timer'] > 0 else 0
        rt_time = int(HOURS4-et_time)

        etz_time = z_time(et_time)
        rtz_time = z_time(rt_time)
        
        print(xy(col,row+13), f"{kf}Elapsed test Time...: {vf}{etz_time}",end=term)
        print(xy(col,row+14), f"{kf}Remaining test Time.: {vf}{rtz_time}",end=term)
        
            
        col = 66
            
        print(xy(col,row), f"{hf}Pressure Alarms:")
    
        print(xy(col,row+1), f"{kf}Press Sensor...: {vf}{alarms['press_sensor_alarm']}",end=term)
        print(xy(col,row+2), f"{kf}Low Pressure...: {vf}{alarms['low_pressure_alarm']}",end=term)
        print(xy(col,row+3), f"{kf}High Pressure..: {vf}{alarms['high_pressure_alarm']}",end=term)
        print(xy(col,row+4), f"{kf}Var Pressure...: {vf}{alarms['var_pressure_alarm']}",end=term)
        print(xy(col,row+5), f"{kf}Zero Pressure..: {vf}{alarms['zero_pressure_alarm']}",end=term)
        
        var_pressure_time =  time.time()-alarms['var_pressure_start'] if alarms['var_pressure_start'] > 0 else 0
        zero_pressure_time = time.time()-alarms['zero_pressure_start'] if alarms['zero_pressure_start'] > 0 else 0
        low_pressure_time =  time.time()-alarms['low_pressure_start'] if alarms['low_pressure_start'] > 0 else 0
        high_pressure_time = time.time()-alarms['high_pressure_start'] if alarms['high_pressure_start'] > 0 else 0
        
        ztime = x_time(zero_pressure_time)
        vtime = x_time(var_pressure_time)
        htime = x_time(high_pressure_time)
        ltime = x_time(low_pressure_time)
        
        print(xy(col,row+7), f"{kf}Low Press Time.: {vf}{ltime}",end=term)
        print(xy(col,row+8), f"{kf}High Press Time: {vf}{htime}",end=term)
        print(xy(col,row+9), f"{kf}Var Press Time.: {vf}{vtime}",end=term)
        print(xy(col,row+10), f"{kf}Zero Press Time: {vf}{ztime}",end=term)

        relay_m = "On " if cont['relay'][0] else "Off"
        relay_1 = "On " if cont['relay'][1] else "Off"
        relay_2 = "On " if cont['relay'][2] else "Off"
        relay_5 = "On " if cont['relay'][3] else "Off"

        print(xy(col,row+12), f"{hf}Relay Status:")
        print(xy(col,row+13), f"{kf}  Motor.....: {vf}{relay_m} ",end=term)
        print(xy(col,row+14), f"{kf}  Valve 1...: {vf}{relay_1 }",end=term)
        print(xy(col,row+15), f"{kf}  Valve 2...: {vf}{relay_2} ",end=term)
        print(xy(col,row+16), f"{kf}  Valve 5...: {vf}{relay_5} ",end=term)


        
        print(xy(5,row+17), f"{rf}______________________________________________________________________________________",end=term)
        
        
        print(xy(0   ,row+18), f"{kf}Payload:",end='')
        print(xy(0   ,row+19),  f"{vf}{payload}    ",end=term)


        try: mode
        except NameError: mode = 0
            
        try: step
        except NameError: step = 0
            
        y = row +21
            
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
            
            r = r + 1    
                
        time.sleep(1)
            
if __name__ == '__main__':
    
    main()
