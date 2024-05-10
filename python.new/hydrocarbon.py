#!/usr/bin/python3

'''
### MODIFIED
A Modified Control Panel program  to run a VST Green Machine, Gen2 and SmartPanel, written in Python3

This program was modifed to display and report hydrocarbon % via the second I2C Analog chanel

Based on version: CP2-100.107 (Uncertified)

Patch Notes:  see readme.md

'''

BUILD = '100.107'
DEBUGGING = True
LONG_TIME_THRESHOLD = 15 #sec
LOW_PRESSURE_THRESHOLD = -40.0
SHORT_TIME_THRESHOLD = 1 #sec
FAST_TIME_THRESHOLD = 50 #ms

import sys

import vst_secrets

secrets = vst_secrets.secrets
DEBUGGING = secrets["DEBUGGING"]
version = secrets["VERSION"]
build = secrets["BUILD"]
device_name = secrets["DEVICE_NAME"]

screen_width = 800
screen_height = 480
secret_type = "External"

# try:
#     sys.path.append("/boot")
#     import vst_secrets

#     secrets = vst_secrets.secrets
#     DEBUGGING = secrets["DEBUGGING"]

# except ImportError as error:

#     print("Import Exception")
#     device_name = "NEEDS_SECRET"
#     build = "100.106"
#     version = f"CPX-{build}"
#     secret_type = "Internal"
#     screen_width = 800
#     screen_height = 480

# else:

#     device_name = secrets["DEVICE_NAME"]
#     version = secrets["VERSION"]
#     build = secrets["BUILD"]
#     secret_type = "External"

#     DEBUGGING = secrets["DEBUGGING"]
#     screen_width = 800
#     screen_height = 480

### DEBUGGING

with open('vst_debug', 'r') as infile:

    debug_it = infile.read()

    if(debug_it=="DEBUGGING=False"):
        DEBUGGING=False
    elif(debug_it=="DEBUGGING=True"):
        DEBUGGING=True

    print(f"Debugging={DEBUGGING}")

if DEBUGGING:
    version = f"X{version}"


from dateutil import tz
from datetime import datetime,timezone,timedelta
from timeit import default_timer as timer

EDT = timezone(timedelta(hours=-4))

#dt = datetime.now()

local = tz.tzlocal()

#import subprocess
import random
import json
import csv
import pickle
import time
import math
import os
#import pytz

#  Support new buzzer
import multiprocessing 
import pigpio
PIN=30

pi = pigpio.pi()

# Remove the obsolete controller.obj and replace with JSON
os.system('rm -rf /home/pi/python/controller.obj')

# Remove the Controller JSON file to have it rebuilt - New for #100
os.system('rm -rf /home/pi/python/controller.json')


import requests
from gpiozero import DigitalInputDevice
test_button = DigitalInputDevice(5)

import redis

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server


# cont = json.loads(rconn.get("cont"))
# alarms = json.loads(rconn.get("alarms"))


from shutil import copyfile

# Setup Logging

import logging

#  Get Local IP Address
import socket
#local_ip = (socket.gethostbyname(socket.gethostname()))


## Modules contributed by Blues Wireless for file download

#from get_update import *

## Turn on the ability to keep logs

logger = logging.getLogger("pylog")

logging.basicConfig(filename='/home/pi/python/cp2.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

## Module responisble for on screen graphic (GUI) elements

import PySimpleGUI as sg

from PIL import Image, ImageTk

filename = "VST_icon_white.png"

# Resize PNG file to size (300, 300)

im = Image.open(filename)
im = im.resize((100,50), resample=Image.BICUBIC)



### 
### Set some default options for the display
###

sg.set_options(
    window_location=(0,0), 
    margins=(0,0),
    titlebar_background_color = 'blue',
    titlebar_text_color = 'blue',
)

from functions import get_serial

## I2C MCP Setup

import board
import busio
from digitalio import Direction
from adafruit_mcp230xx.mcp23017 import MCP23017
i2c = busio.I2C(board.SCL, board.SDA)

mcp = MCP23017(i2c)

###
### Setup pins on the Raspberry Pi
###

pin0 = mcp.get_pin(0)
pin1 = mcp.get_pin(1)
pin2 = mcp.get_pin(2)
pin3 = mcp.get_pin(3)

dispenser_shutdown = mcp.get_pin(4)
the_buzzer = mcp.get_pin(5)

new_buzzer = 30

tls_relay = mcp.get_pin(8)

## Have system check this relay for ON in fast_updates() ## Overfill alarm being
## OFF indicates the Overflow condition has occured.

panel_power = mcp.get_pin(10) ## This will only be off if the field interlock switch is OFF

pin0.direction = Direction.OUTPUT
pin1.direction = Direction.OUTPUT
pin2.direction = Direction.OUTPUT
pin3.direction = Direction.OUTPUT

the_buzzer.direction = Direction.OUTPUT
the_buzzer.value = False ## Reset  buzzer

dispenser_shutdown.direction = Direction.OUTPUT  ##  GM Fault Relay (dispenser interface for shutdown)
dispenser_shutdown.value = True


#### Dispenser shutdown relay Normally Open (NO) Energized
#### Except when there is a 72 hour shutdown alarm

tls_relay.direction = Direction.INPUT
panel_power.direction = Direction.INPUT

## ADC Stuff

import Adafruit_ADS1x15
adc = Adafruit_ADS1x15.ADS1115()
GAIN = 1

t = True ## Test variable to turn on Relay

kickstart_timer = timer()
leak_test_timer = timer()
cycle_time = timer()

scan_time = timer()
print_timing = 0


###  Toggle to track whether or not there is pending file download
file_download = False

run_cyc = False
run_step = 0
run_steps = []
step_count = 0
accum_time = 0

#version = "20210809-46A"
head_left = ''
head_right = ''
modem_status = 'Starting Up'
maint_code = '878'
startup_code = '1793'
was_active = False

# REboot Flag for tracking reboot condition

reboot_flag = False
reboot_time = 0

###  Super Secret code

vst_code = '321321'
vst_code2 = '321321'

window_pass = None
window = None

logging.info(f"Program version {version} starting")

### Setup intitial values for Controller dictionary

continuous_mode = False
run_mode = ''
locked = True
elapsed_test_time = 0.0
manual_purge_mode = False
manual_burp_mode = False
manual_purge_count = 0


cont = {}
step = 0

# Get GMID from Device_ID at the top of the program for now

cont['gmid'] = device_name
cont['deviceID'] = ""
cont['productID'] = "com.vsthose.admin:vstcp2"
cont['scr_width'] = screen_width
cont['scr_height'] = screen_height

cont['runcycles']= 0
cont['startup'] = '000000'
cont['continuous'] = True
cont['pressure'] = 0.0
cont['hydrocarbons'] = 0.0
cont['mode'] = 0
cont['faults']=0
cont['status'] = ''
cont['temp']=0.0
cont['pressure_set_point'] = 0.2
cont['version'] = version
cont['serial'] = ''
cont['seq'] = 0
cont['maintenance_mode'] = False
cont['test_mode'] = False
cont['was_test_mode'] = False
cont['test_purge_mode'] = False
cont['test_burp_mode'] = False
cont['manual_mode'] = True
cont['utc'] = ''

# Wireless Parameters
cont['band'] = '-1'
cont['rssi'] = '-1'
cont['bars'] = '-1'

### Run Cycle TEST Parameters

cont['rc_high_limit'] = -0.35
cont['rc_low_limit'] = -0.55

cont['rc_on_time'] = 15
cont['rc_off_time'] = 5

# Added for new rolling average

pressure_list = []
current_list = []
hc_list = []

#  Pick Correct Cycles per block based on testing

#cont['cycles_per_block'] = 40
#cont['cycles_per_block'] = 10

###  Changing to 1 to TEST centerville
cont['cycles_per_block'] = 1

if 'profile' not in cont:
    profile='CS8'   ### Default profile

# ## Current relates variables
cont['current'] = 0.0
cont['adc_peak'] = 0
cont['adc_rms'] = 0
cont['adc_zero'] = 15422.0
cont['adc_raw'] = 0

cont['adc_zero_hc'] = 5120.0
cont['adc_peg_hc'] = 27530.0

cont['curr_amp'] = 0.0
cont['curr_sum'] = 0.0
cont['curr_samp'] = 0
cont['curr_avg'] = 0.0
cont['curr_rms'] = 0.0
#cont['adc_zero'] = 15150.0
cont['adc_value'] = 0.0
cont['adc_value_hc'] = 0.0
cont['curr_counter'] = 0
cont['calibration'] = 0


#save_controller(cont)

to_modem = ""
modem = []

###
### Setup Alarms Dictionary
###

alarms={}

alarms['low_pressure_alarm'] = False
alarms['high_pressure_alarm'] = False
alarms['zero_pressure_alarm'] = False
alarms['var_pressure_alarm'] = False
alarms['sd_card_alarm'] = False
alarms['overfill_alarm'] = False
alarms['vac_pump_alarm'] = False
alarms['maint_alarm'] = False
alarms['press_sensor_alarm'] = False
alarms['shutdown_alarm'] = False
alarms['buzzer'] = False
alarms['tls_relay'] = False
alarms['modem_alarm'] = False

alarms['buzzer_high'] = True
alarms['buzzer_low'] = True
alarms['buzzer_zero'] = True
alarms['buzzer_var'] = True
alarms['buzzer_triggered'] = False
alarms['buzzer_silenced'] = False

alarms['tls_buzzer_triggered'] = False

alarms['buzzer_delay'] = 0
alarms['buzzer_current'] = 0
alarms['buzzer_count'] = 0


alarms['shutdown'] = False

alarms['shutdown_stage'] = 0
alarms['critical_alarm_time'] = 0
#alarms['nuisance_alarm_time'] = 0
alarms['med_alarm_time'] = 0
alarms['shutdown_time_60'] = 0
alarms['shutdown_alarm_time'] = 0

alarms['overfill_alarm_time'] = 0
alarms['overfill_alarm_alert_time'] = 0
alarms['overfill_alarm_override_time'] = 0

alarms['buzzer_time'] = 0
alarms['buzzer_duration'] = 0

alarms['zero_pressure_start'] = 0
alarms['high_pressure_start'] = 0
alarms['low_pressure_start'] = 0
alarms['var_pressure_start'] = 0

alarms['test_start_timer'] = 0.0 

## Variable Pressure Place holder

alarms['var_pressure'] = 0.0
alarms['all_stop'] = False

### Timings for Alarms

if DEBUGGING:

    ###
    ###  Abbreviated Alarm Times.  Seconds instead of minutes
    ###

    HOURS24 = 1*60  ## One Minute
    HOURS36 = 2*60
    HOURS47 = 3*60
    HOURS72 = 4*60
    HOURS1 = 1*60
    HOURS4 = 4*60

    MIN60 = 60
    MIN30 = 30
    MIN120 = 120
    BUZZER = True

else:

    HOURS24 = 24*60*60
    HOURS36 = 36*60*60
    HOURS47 = 47*60*60
    HOURS72 = 72*60*60
    HOURS1 = 60*60
    HOURS4 = 4*60*60

    MIN60 = 60*60
    MIN30 = 30*60
    MIN120 = 120*60
    BUZZER = True
    
shutdown_count = 0


kickstart_elapsed = 12 * 60 * 60  ##  Maximum seconds between runs.  Kick the GM if greater than this

kickstart_timer = timer()

#run_timer = timer()
run_timer = 0
special_run_count = 0

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033c'

    def xy(x, y):
        return f"\u001b[{y};{x}H"


#################################
###
###   FUNCTIONS BEGIN HERE
###
#################################


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


def save_cont(cont):

    with open('/home/pi/python/cont2_data.json', 'w') as outfile:
        json.dump(cont, outfile)
        test = 1

    return test


def load_controller():

    try:
        with open('/home/pi/python/cont2_data.json') as json_file:
            c = json.load(json_file)
    except:
        save_cont(cont)
        c = load_controller()

    return c

def get_alarms():

    alarmsw = json.loads(rconn.get("alarms")) ####  LOOK!!!
    return alarms


def save_alarms(alarm):

    with open('/home/pi/python/alarm_data.json', 'w') as outfile:
        json.dump(alarm, outfile)

    rconn.set("alarms",json.dumps(alarms))


def test_mode_on():


    global cont2
    global cont
    global alarms

    cont2 = load_controller()


    cont["test_mode"] = True

    if DEBUGGING:
        logit("info","Test Mode is Active.")

    print(f'{bcolors.RESET}')  ### Reset Terminal

    print(f'{bcolors.BOLD}')
    print(f'################################')    
    print(f'## Local Test Mode ACTIVATED. ##')
    print(f'################################')    
    print(f'{bcolors.ENDC}')

    #if cont2['test_mode'] is not None:
    cont2['test_mode'] = True
    save_cont(cont2)

    alarms['test_start_timer'] = time.time()


def test_mode_off():

    global cont
    global cont2

    cont2 = load_controller()

    cont["test_mode"] = False

    alarms['test_start_timer'] = 0.0
    
    
    print(f'{bcolors.BOLD}')
    print(f'###################################')    
    print(f'## Local Test Mode NOT Activatd. ##')
    print(f'###################################')    
    print(f'{bcolors.ENDC}')


    if cont2['test_mode'] is not None:
        cont2['test_mode'] = False

    save_cont(cont2)

    if DEBUGGING:

        logit("info","Test Mode is NOT Active.")

    all_stop()


def test_mode_reset():

    cont['rc_high_limit'] = -0.35
    cont['rc_low_limit'] = -0.55
    cont['rc_on_time'] = 15
    cont['rc_off_time'] = 5
    
    save_cont(cont)

    window['rc_high_limit'].update(str(cont['rc_high_limit']))
    window['rc_low_limit'].update(str(cont['rc_low_limit']))
    window['rc_on_time'].update(str(cont['rc_on_time']))
    window['rc_off_time'].update(str(cont['rc_off_time']))

def test_mode_up1():

    #if(cont['rc_high_limit'] - 0.02) > cont['rc_low_limit']:
    cont['rc_high_limit'] = round(cont['rc_high_limit'] + .01,2)
    
    window['rc_high_limit'].update(str(cont['rc_high_limit']))

    save_cont(cont)

def test_mode_dn1():

    if(cont['rc_high_limit'] - 0.01) > cont['rc_low_limit']:
        cont['rc_high_limit'] = round(cont['rc_high_limit'] - .01,2)

    window['rc_high_limit'].update(str(cont['rc_high_limit']))

    save_cont(cont)

def test_mode_up2():

    if (cont['rc_low_limit'] + 0.01) < cont['rc_high_limit']:
        cont['rc_low_limit'] = round(cont['rc_low_limit'] + .01,2)

    window['rc_low_limit'].update(str(cont['rc_low_limit']))

    save_cont(cont)

def test_mode_dn2():
    cont['rc_low_limit'] = round(cont['rc_low_limit'] - .01,2)

    window['rc_low_limit'].update(str(cont['rc_low_limit']))

    save_cont(cont)

def test_mode_up3():
    cont['rc_on_time'] = cont['rc_on_time'] + 1

    window['rc_on_time'].update(str(cont['rc_on_time']))

    save_cont(cont)

def test_mode_dn3():
    cont['rc_on_time'] = cont['rc_on_time'] - 1
    if cont['rc_on_time'] < 0:
        cont['rc_on_time'] = 0

    window['rc_on_time'].update(str(cont['rc_on_time']))

    save_cont(cont)

def test_mode_up4():
    cont['rc_off_time'] = cont['rc_off_time'] + 1

    window['rc_off_time'].update(str(cont['rc_off_time']))

    save_cont(cont)

def test_mode_dn4():
    cont['rc_off_time'] = cont['rc_off_time'] - 1
    if cont['rc_off_time'] < 0:
        cont['rc_off_time'] = 0

    window['rc_off_time'].update(str(cont['rc_off_time']))

    save_cont(cont)


def all_stop():

    # Stop all processing

    global run_cyc
    global run_step
    global run_timer
    global run_mode
    global alarms 
    
    run_cyc = False
    run_step = 0
    run_timer = 0
    run_mode = 0
    alarms['all_stop'] = True
    
    set_mode(0)
    set_relays(0)

def beep_SOS():
    beep()
    #beep(0.1,3,0.05)

def beep_long():

    beep()
    #beep(6,10,1)

def one_beep():
    beep()
    
    #beep(0.1,1,0)

def chirp():
    beep()
    #beep(0.1,1,0)

def buzzer(freq, dur):
    

    pi.set_PWM_frequency(30, freq)
    pi.set_PWM_dutycycle(30,128)
    time.sleep(dur)
    pi.set_PWM_dutycycle(30,0)
    
    pi.stop()
    
    
def beep():
    #pass
    #   beep ( duration_tone,count,duration_pause)

    if BUZZER and (profile == 'CS8' or profile == 'CS12') :
        
        #pin = 30
        #pi.set_PWM_frequency(pin,880)
                    
        freq = 880
        dur = 0.5
        
        buzz = multiprocessing.Process(target=buzzer,args=(freq,dur, ))
        buzz.start()

def startup_beep():
                    
    freq = 880 
    dur = 0.5
    
    buzz = multiprocessing.Process(target=buzzer,args=(freq,dur, ))
    buzz.start()
    


def logit(err,msg):

    if DEBUGGING:  
        print(f'### {err} - {msg}')
    else:
    	pass



def panel_power_relay_active():

    ##############################################
    ###
    ###    PANEL POWER (MAINTENANCE SWITCH) RELAY
    ###
    ##############################################

    global cont

    try:

        pp_relay = panel_power.value

    except:

        logit("error", "ALARM: PANEL POWER Relay not reporting!")

        alarms['maint_alarm'] = True

    else:

        if alarms['maint_alarm']:
            alarms['maint_alarm'] = False

            logit("info", "ALARM: PANEL POWER Relay reporting again!")

        return pp_relay



def tls_relay_active():

    #############################################
    ###
    ###    TLS / ATG / OVERFILL RELAY
    ###
    ##############################################

    ### The TLS_Relay will return True if Activated

    ###  Get earlier versions of this function in build 078
   
    return tls_relay.value


def set_mode(mode):
    
    global cont
    
    cont['mode'] = mode
    

def relay_on(r):

    #print(f"Relay: {r} is on")
    try:
        mcp.get_pin(r).value = True
    except:
        print("Relay On Failure")
        # If there was a problem communicating with the relay, wait 1/10 of a second and try again
        time.sleep(0.10)
        relay_on(r)


def relay_off(r):

    try:
        mcp.get_pin(r).value = False
    except:

        # If there was a problem communicating with the relay, wait 1/10 of a second and try again
        time.sleep(0.10)
        relay_off(r)

       
def run_cycle(r):

    ### Create a run cycle template that is a list of modes and timings for each mode.

    if DEBUGGING:

        logging.info('RunMode Inside: {r}')

        ### Debug Run Cycles
        ### These are shortened to make the logic easier to follow
        
        if r == 'run':
            run_cycle_template = [[1,10],[0,1],[2,1],[3,1],[2,1],[3,1],[2,1],[3,1],[2,1],[3,1],[2,1],[3,1],[2,1],[3,1],[0,4]]  ## Debug Run Cycle
        elif r == 'man':
            run_cycle_template = [[1,10],[0,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[0,4]]  ## Debug Run Cycle
        elif r == 'func':
            run_cycle_template = [[1,20],[2,6],[1,6],[2,6],[1,6],[2,6],[1,6],[2,6],[1,6],[2,6]]  ## Debug Functionality Cycle
        elif r == 'leak':
            run_cycle_template = [[9,30]]  ## Debug Functionality Cycle Mode '9' is a special ALL ON mode
        elif r == 'eff':
            run_cycle_template = [[0,5],[1,5],[0,5],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[0,4]] ## Efficency Testing
            #run_cycle_template = [[0,30],[1,60],[0,5],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[0,4]]  ## Efficiency Testing
        elif r == 'special_purge':
            run_cycle_template = [[2,10],[0,3]]  ## Special Purge mode for Testing
        elif r == 'special_run':
            run_cycle_template = [[1,15],[0,5]]  ## Special Purge mode for Testing
        elif r == 'manual_purge':
            run_cycle_template = [[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5]]
        elif r == 'manual_purgex2':
            run_cycle_template = [[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5]]
        elif r == 'manual_burp':
            run_cycle_template = [[3,5]] # Burp for 5 seconds
    
    else:

        ###
        ###  These are the production Run Cycles
        ###

        if r == 'run':
            #run_cycle_template = [[1,150],[0,3],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[0,15]]  ## Normal Run Cycle
            run_cycle_template = [[1,120],[0,3],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[0,15]]  ## Normal Run Cycle
        elif r == 'man':
            #run_cycle_template = [[1,150],[0,3],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[0,15]]  ## Normal Run Cycle
            run_cycle_template = [[1,120],[0,3],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[0,15]]  ## Normal Run Cycle
        elif r == 'func':
            run_cycle_template = [[1,60],[2,60],[3,5],[1,60],[2,60],[3,5],[1,60],[2,60],[3,5],[1,60],[2,60],[3,5],[1,60],[2,60],[3,5]]  ## Normal Functionality Cycle
        elif r == 'leak':
            run_cycle_template = [[9,1800]]  ## Normal Leak Cycle Mode '9' is a special ALL ON mode
        elif r == 'eff':
            run_cycle_template = [[0,300],[1,60],[0,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[0,1]] ## Efficency Testing
            #run_cycle_template = [[0,5],[1,5],[0,5],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[2,5],[3,1],[0,4]] ## Efficency Testing
        elif r == 'special_purge':
            run_cycle_template = [[2,10],[0,3]]  ## Special Purge mode for Testing
        elif r == 'special_run':
            run_cycle_template = [[1,15],[0,5]]  ## Special Run mode for Testing
        elif r == 'manual_purge':
            run_cycle_template = [[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5]]
        elif r == 'manual_purgex2':
            run_cycle_template = [[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5],[2,50],[3,5]]
        elif r == 'manual_burp':
            run_cycle_template = [[3,5]] # Burp for 5 seconds
            
    return(run_cycle_template)


def set_relays(mode):

    '''
    This routine actually turns the relays on and off, depending on what mode it is given
    '''

    #global run_timer
    
    set_mode(mode)

    if DEBUGGING:
        print(f"Set Relay Mode: {mode}")
    ### Setup the relay on/off patterns based on the mode

    if mode == 0:
        
        relay_off(0) #CR3 - Motor
        relay_off(1) #CR1
        relay_off(2) #CR2
        relay_off(3) #CR5
        
    elif mode == 1:
        
        relay_on(0)
        relay_on(1)
        relay_off(2)
        relay_on(3)
        
    elif mode == 2:
                
        relay_on(0)
        relay_off(1)
        relay_on(2)
        relay_off(3)
        
    elif mode == 3:
                
        relay_off(0)
        relay_off(1)
        relay_off(2)
        relay_on(3)
    
    elif mode == 9:
                
        relay_off(0)
        relay_on(1)
        relay_on(2)
        relay_on(3)
    
    elif mode == 8:

        relay_off(0)
        relay_off(1)
        relay_on(2)
        relay_on(3)

    else: 
                    
        relay_off(0)
        relay_off(1)
        relay_off(2)
        relay_off(3)

  
                    
def mapit(x, in_min, in_max, out_min, out_max):
    
    ''' Function to map an input that works like the Arduino map() function '''

    return (x-in_min) * (out_max-out_min) / (in_max-in_min) + out_min

def check_testmode():

    #test_button.is_active

    if test_button.is_active:

        cont["testmode"] = True
        logit("info","Test Mode is Active.")
    else:
    
        cont["testmode"] = False
        logit("info","Test Mode is NOT Active.")

    
def test_mode():

    '''
    Super Duper Test mode.  If the Test mode button is ON then pressure
    is controlled via this test mode instead of the autmatic mode
    '''

    global special_run_count
    global modem_status
    global cont
    global alarms
    global run_cyc
    global run_step
    global run_steps
    global run_timer
    global run_mode
    global print_timing
    global elapsed_test_time
    global manual_purge_mode


    ## beep_SOS()

    modem_status = 'TEST MODE'
    pressure = cont['pressure']

    ### Test mode needs to be set to stop normal operation

    # if alarms['test_start_timer'] == 0:
    #     alarms['test_start_timer'] = timer()

    remaining_time = int(HOURS4 - (time.time()-alarms['test_start_timer']))
    
    print(f"In TEST MODE, Time remaining: {remaining_time} secs")

    print(f"Special Run Count: {special_run_count}")
    
    #elapsed_test_time = time.time() - alarms['test_start_timer']

    if manual_purge_mode == False:

        elapsed_test_time = time.time() - alarms['test_start_timer']

        print(f"\n")
        print(f"###########################")
        print(f"## Test Mode Parameters: ##")
        print(f"###########################")
        print(f'\n')
        print(f"##    RC Limit: High: {bcolors.HEADER}{cont['rc_high_limit']}{bcolors.ENDC} Low: {bcolors.HEADER}{cont['rc_low_limit']}{bcolors.ENDC}")
        print(f"##  Current Pressure: {bcolors.HEADER}{pressure}{bcolors.ENDC}")
        print(f"##  Test Start Timer: {bcolors.HEADER}{round(time.time() - alarms['test_start_timer'],0)}{bcolors.ENDC}")
        #print(f"##         Time.Time: {round(time.time(),0)}")
        #print(f"##        Test Timer: {round(alarms['test_start_timer'],0)}")

        if special_run_count == 2 and run_cyc == False:
                                 
            run_cyc = True
            run_step = 0
            run_timer = 0
            run_mode = 'special_purge'
            
            special_run_count = 0


        if pressure > cont['rc_high_limit'] and run_cyc == False:

            run_cyc = True

            #elapsed_test_time = timer() - alarms['test_start_timer']

            if special_run_count < 2:
                run_step = 0
                run_timer = 0
                run_mode = 'special_run'
                
                special_run_count += 1
             
            '''
            if elapsed_test_time < 35:
                if (run_mode != 'special_run'):
                    run_step = 0
                    run_timer = 0
                    run_mode = 'special_run'
                
            elif elapsed_test_time >= 35:
            # and elapsed_test_time <= 48:
                if(run_mode != 'special_purge'):
                    run_step = 0
                    run_timer = 0
                    run_mode = 'special_purge'
            '''
                    
            #### Measure pressure before running again
            ### after running special run twice, do a 10 second special purge

        elif pressure < cont['rc_low_limit'] and run_cyc == False:

            if run_mode != "manual_purge":
                #elapsed_test_time = timer() - alarms['test_start_timer']

                # run_cyc = True ## make sure regular run cycles cannot happen
                # run_mode = "special_burp"
                run_step = 0
                run_timer = 0
                run_cyc = False
                set_relays(8)  # Fresh Air / Special Burp
                set_mode(8)

   

        ### Special PURGE is run for as long as is needed
        ### to bring pressure back down


    ### 
    ### If manual / special purge then system cannot automatically run
    ### manual purge is NOT "test mode". Manual purge operates completeny
    ### independant and trumps EVERYTHING
    ###

    ### PURGE CYCLE, not just purge mode, 50 seconds
    ### Special purge kills the run cycle
    ### and consist of a standardn purge seq of 50 sec and 5sec burp, repeated
    ### 6 times.
    ###

def manual_purge_button():

    global run_step
    global run_timer
    global run_cyc
    global run_mode
    global manual_purge_mode
 
    ### IF PURGE BUTTON:

    if manual_purge_mode == True:

        run_step = 0
        run_timer = 0
        run_cyc = False

        manual_purge_mode = False

        set_mode(0)  ### reset mode to idle
        set_relays(0)
    else: # Manual Purge is False
        run_cyc = True
        run_mode = "manual_purgex2"
        print(f"Manual Purge from Panel!")
        manual_purge_mode = True

    chirp()

def manual_burp_on():
    global run_cyc
    global run_mode
    global manual_burp_mode

    run_cyc = True
    run_mode = "manual_burp"
    manual_burp_mode = True

def manual_purge_on():

    global manual_purge_count
    global purge_run_times
    global run_cyc
    global run_mode
    global manual_purge_mode

    run_cyc = True
    run_mode = "manual_purge"
    manual_purge_mode = True


def manual_purge_off():

    global run_cyc
    global run_mode
    global manual_purge_mode
    global special_run_count
    
    run_step = 0
    run_timer = 0
    run_cyc = False

    manual_purge_mode = False
    special_run_count = 0

    set_mode(0)  ### reset mode to idle
    set_relays(0)


def manual_burp_off():

    global run_cyc
    global run_mode
    global manual_burp_mode

    run_step = 0
    run_timer = 0
    run_cyc = False

    manual_burp_mode = False

    set_mode(0)  ### reset mode to idle
    set_relays(0)


def get_startup_code():

    startup_code = '000000'
    locked = True

    try:
        fob = open("code.obj","rb")  
        
    except: 
        logit("error","Error reading code.obj.  Startup code failed to load.")

    else:
        startup_code = pickle.load(fob)  ## "c" is the controller object
        fob.close()

    return startup_code


def get_controller():

    try:
        cont = json.loads(rconn.get("cont"))
    except:
        #pass
        cont = {}    
        
    return cont



def save_controller(c):

    # json_file = '/home/pi/python/controller.json'

    # with open(json_file, 'w') as outfile:
    #     json.dump(c, outfile)

    rconn.set("cont",json.dumps(cont))


def get_profile():

    p = "CS8"

    try:
        p = rconn.get("profile")
    except:
        pass
 
    return p

    # try:
    #     fob = open("profile.obj","rb")
     
    # except:
    #     logit("error","Error reading profile.obj.  Profile failed to load.")

    # else:
    #     c= pickle.load(fob)  ## "c" is the controller object
    #     fob.close()

    # return c


def save_profile(p):


    rconn.set("profile",json.dumps(p))

    # try:
    #     fob = open("profile.obj","wb")

    # except:
    #     logit("error","Error writing profile.obj.  Profile failed to save.")

    # else:
    #     pickle.dump(c,fob)
    #     fob.close()


def save_startup_code(c):

    try:
        fob = open("code.obj","wb")


    except:

        logit("error","Error writing code.obj.  Startup code failed to save.")

    else:
        pickle.dump(c,fob)
        fob.close()


def get_runcycles(cont):

    try:

        runcycles = int(rconn.get("runcycles"))
        #fob = open("mcu.obj","rb")

    except: 

        cont_load = json.loads(rconn.get('cont'))

        logit("error","Error reading runcycles.  Runcycle Count failed to load.")
        runcycles = cont_load['runcycles']
        rconn.set('runcycles',cont['runcycles'])

    else:

        # else:
        #cont['runcycles'] = pickle.load(fob)  ## "cont" is the controller object
        
        
        #fob.close()

        logit("info","Runcycles set to {cont['runcycles']}.")

        print(f"*-------Runcycles set to {cont['runcycles']}.")

        return runcycles

def save_runcycles(runs):

    rconn.set('runcycles',runs)

 

def get_current():

    '''
    
    Test to prove Tony's theory

    '''

    global cont
    global alarms

    try:

        adc_time = time.time()

        c = adc.read_adc(2, gain=GAIN)
        d = adc.read_adc(3, gain=GAIN)
      
    except:

        logit("error","Cannot read current from Vac Pump Motor!")

    else:

        i = abs(c-d)
        
        if len(current_list) >= 20: 
            del current_list[0] #  Remove the first item from the list

        current_list.append(i)

        cont['adc_peak'] = max(current_list)

        cont['adc_rms'] = cont['adc_peak'] #* 0.707yes
        
        cont['curr_rms'] = mapit(cont['adc_rms'],1248.0,4640.0,2.1,8.0) # for IO Panel 3.3B - 16 Bit
        #cont['curr_rms'] = mapit(cont['adc_rms'],740.0,3000.0,2.0,8.0) # for IO Panel 3.1B - 12 Bit

        cont['current'] = round(cont['curr_rms'],2)
    

def check_current(i):

    global alarms
    global cont

    if i <= 4.0:

        if cont['curr_counter'] >= 9:

            alarms['vac_pump_alarm'] = True

            all_stop()
            
            set_screen('a')

            if alarms['critical_alarm_time'] ==0:
                alarms['critical_alarm_time'] = timer()

            logit("err","Critical Alarm - Vac Pump")

        else:
            cont['curr_counter'] = cont['curr_counter'] + 1

    else:

        cont['curr_counter'] = 0

    if DEBUGGING:
        print(f"Current Counter: {cont['curr_counter']}")


def get_pressure():

    global cont
    global alarms

    try:     
        cont['adc_value'] = adc.read_adc(0, gain=GAIN)
             
    except:

        alarms['press_sensor_alarm'] = True

        ### Add Silence Button 
        window['sb'].update(visible=True)
        window.read(timeout=1)

        logit("error","Critical Alarm - Pressure Sensor - Sensor not found")

        if DEBUGGING:
            print(f'{bcolors.BOLD}')
            print(f'################################')   
            print(f'## Pressure sensor not found')
            print(f'################################')   
            print(f'{bcolors.ENDC}')

        all_stop()

        pressure = -99.9   ### arbitrary value to indicate pressure sensor is broken

    else:

        # print(f"Got here...{cont['adc_value']}")

        if cont['adc_value'] < 1:

            if DEBUGGING:
                print(f'{bcolors.BOLD}')
                print(f'################################')   
                print(f'## Pressure sensor broken')
                print(f'################################')   
                print(f'{bcolors.ENDC}')

            # print(f"ADC Value is zero...")
            
            alarms['press_sensor_alarm'] = True
            pressure = -99.9
            all_stop()            
      
        else:
        
            ### Get the correct pressure by mapping the returned ADC values
            for i in range(0,9):

                pressure = mapit(cont['adc_value'], cont['adc_zero'],22864.0,0.0, 20.8)
                pressure = round(pressure,2)

                if pressure < LOW_PRESSURE_THRESHOLD:

                    alarms['press_sensor_alarm'] = True

                    #window['sb'].update(visible=True)
                    #window.read(timeout=1)

                    logit("error","Critical Alarm - Pressure Sensor - Pressure < -31.0")
                    
                    if not alarms['all_stop']: 
                        
                        if DEBUGGING:
                            print(f'{bcolors.BOLD}')
                            print(f'################################')   
                            print(f'## Pressure to LOW!')
                            print(f'################################')   
                            print(f'{bcolors.ENDC}')

                        all_stop()

                ### Compute Rolling average of Pressure

                if len(pressure_list) >= 200: 
                    del pressure_list[0] #  Remove the first item from the list

                pressure_list.append(pressure)
                cont['pressure'] = round(sum(pressure_list) / len(pressure_list),2)
    
    # save_controller(cont)


def get_hydrocarbons():

    global cont
    global alarms

    ain0 = adc.read_adc(0, gain=GAIN)
    ain1 = adc.read_adc(1, gain=GAIN)
    ain2 = adc.read_adc(2, gain=GAIN)
    ain3 = adc.read_adc(3, gain=GAIN)
    
    #print(f"ADC Readings AIN0: {ain0}, AIN1: {ain1}, AIN2: {ain2}, AIN3: {ain3}")

    try:     
        cont['adc_value_hc'] = adc.read_adc(1, gain=GAIN)
             
    except:

        if DEBUGGING:
            print(f'{bcolors.BOLD}')
            print(f'################################')   
            print(f'## Hydrocarbon sensor not found')
            print(f'################################')   
            print(f'{bcolors.ENDC}')

    else:

        #print(f"Getting Hydrocarbosn...{cont['adc_value_hc']}")

        if cont['adc_value_hc'] < 1:

            if DEBUGGING:
                print(f'{bcolors.BOLD}')
                print(f'################################')   
                print(f'## Hydrocarbon sensor broken')
                print(f'################################')   
                print(f'{bcolors.ENDC}')

            # print(f"ADC Value is zero...")
      
        else:
        
            ### Get the correct pressure by mapping the returned ADC values
            for i in range(0,9):

                hc = mapit(cont['adc_value_hc'], cont['adc_zero_hc'],cont['adc_peg_hc'], 0.0,  60.6)
                hc = round(hc,2)

                #print (f" Immmediate HC Value: {hc}")

                ### Compute Rolling average of Pressure

                if len(hc_list) >= 10: 
                    del hc_list[0] #  Remove the first item from the list
                    
                hc_list.append(hc)

                cont['hydrocarbons'] = round(hc,2)

    # save_controller(cont)


def pressure_sensor_alarm(pressure):

    global alarms
    global cont

    ##  Pressure Sensor possiblly broken

    if (pressure < -40.0) or (cont['adc_value'] < 1):
        alarms['press_sensor_alarm'] = True

        #if alarms['buzzer_silenced'] == False:
        one_beep()

        window['sb'].update(visible=True)
        window.read(timeout=1)
        
    else:
        alarms['press_sensor_alarm'] = False



    if alarms['press_sensor_alarm'] is True:
        if not alarms['all_stop']:
            all_stop()
            print("Another pressure Sensor alarm")

        #if alarms['buzzer_silenced'] == False:
            one_beep()

            window['sb'].update(visible=True)
            window.read(timeout=1)
        
        if alarms['critical_alarm_time'] == 0:
            alarms['critcal_alarm_time'] = timer()


def zero_pressure_alarm(pressure):

    global alarms

    ## Zero Pressure - UST Pressure is 0.00 IWC +/- 0.15 for 60 continuous seconds

    if((pressure >= -0.15) and (pressure < 0.15)):

        if alarms['zero_pressure_start'] == 0:
            alarms['zero_pressure_start'] = timer()
        else:
            if timer() - alarms['zero_pressure_start'] > MIN60:
                alarms['zero_pressure_alarm'] = True

    else:

        alarms['zero_pressure_start'] = 0
        alarms['zero_pressure_alarm'] = False


def low_pressure_alarm(pressure):

    global alarms

    ## Low Pressure - UST Pressure < -6.00 IWC for 30 continuous minutes.

    if(pressure < -6.0):

        if alarms['low_pressure_start'] == 0:
            alarms['low_pressure_start'] = timer()
        else:
            if timer() - alarms['low_pressure_start'] > MIN30:
                alarms['low_pressure_alarm'] = True

    else:

        alarms['low_pressure_start'] = 0
        alarms['low_pressure_alarm'] = False



def high_pressure_alarm(pressure):

    global alarms

    ## High Pressure - UST Pressure > 2.00 IWC for 30 Continuous minutes.

    if(pressure > 2.0):
       
        if alarms['high_pressure_start'] == 0:
            alarms['high_pressure_start'] = timer()
        else:
            if timer() - alarms['high_pressure_start'] > MIN30:
                alarms['high_pressure_alarm'] = True

    else:

        alarms['high_pressure_start'] = 0
        alarms['high_pressure_alarm'] = False


def var_pressure_alarm(pressure):

    global alarms

    ## Variable Pressure - UST Pressure does not vary from any pressure by +/- 0.20 IWC for 60 continuous minutes.

    if(abs(pressure - alarms['var_pressure'])) <= 0.2:

        if alarms['var_pressure_start'] == 0:
            alarms['var_pressure_start'] = timer()


        else:
            if timer() - alarms['var_pressure_start'] > HOURS1:

                alarms['var_pressure_alarm'] = True

    else:
        alarms['var_pressure_start'] = 0
        alarms['var_pressure_alarm'] = False
        alarms['var_pressure'] = round(pressure,2)
    
    if DEBUGGING and alarms['var_pressure_start'] > 0:
        print(f"Var Pressure Time: {int(timer()-alarms['var_pressure_start'])}")


def check_overfill():

    global was_active

    '''
    Check for an overfill alarm.  If TLS relay is not HIGH, there is an overfill
    '''
    
    if tls_relay_active():

        '''
        If overfill alarm time has never been set, alarmo should trigger iafter 10 seconds
        if overfill alarm time is more than 120 minutes then trigger alarm again
        Overfill Alarm Overide should reset the clock
        '''

        ### If the relay is triggered then overfill startup timer continues to be reset - Per Doug

        #alarms['overfill_alarm_alert_time'] = time.time()  ## Intiiate an Alarm

        if alarms['overfill_alarm_alert_time'] == 0:
            alarms['overfill_alarm_alert_time'] = time.time()  ## Intiiate an Alarm

        elif time.time() - alarms['overfill_alarm_alert_time'] > 10:
            alarms['overfill_alarm_time'] = 0
            alarms['overfill_alarm'] = True
            was_active = True
            all_stop()

            #set_screen('a')

            

            if alarms['tls_buzzer_triggered'] is False:
                alarms['tls_buzzer_triggered'] = True 

                if DEBUGGING:

                    logging.info('TLS Relay - Overfill Alarm')

                    print(f'{bcolors.BOLD}')
                    print(f'################################')    
                    print(f'## Error - OVERFILL!          ##')
                    print(f'################################')    
                    print(f'{bcolors.ENDC}')

                one_beep()

            else:
                pass

        else:
            logit("info",f"ALARM: Overfill Alarm Override: {timer()-alarms['overfill_alarm_time']}")
    else:
        
        if was_active:
            
            print(f"Was Active:{was_active}, Overfill Time Countdown: {time.time() - alarms['overfill_alarm_time']}")
            if alarms['overfill_alarm_time'] == 0:
                alarms['overfill_alarm_time'] = time.time()

            elif time.time() - alarms['overfill_alarm_time'] > MIN120:
                alarms['overfill_alarm'] = False
                alarms['overfill_alarm_time'] = 0

                alarms['tls_buzzer_triggered'] = False

    ###
    ###  End of TLS Relay Alarm
    ###

    alarms['maint_alarm'] = panel_power_relay_active()

    if alarms['overfill_alarm'] is True and alarms['critical_alarm_time'] == 0:
        alarms['critical_alarm_time'] = timer()

    ### Current limit to trip Vac pump alarm should be 6.9 Amps
    ###  We have changed this to 5.0



def fast_updates():

    global alarms
    global cont
    global run_timer

    '''These updates happens as fast as the TIMEOUT for PySimpleGUI'''

    get_current()

    get_pressure()

    get_hydrocarbons()
    
    if run_cyc is True \
        and cont['mode']== 2 \
        and timer()-run_timer >= 35 \
        and cont['vac_pump_alarm_checked'] is False:

        '''t
        GET CURRENT IN PURGE MODE:

        If run mode is not stopped and it active AND we are in the PURGE MODE
        and at least 35 seconds has elapsed in the PURGE mode then start
        comparing the current of the vac pump motor to make sure its pulling
        enough current
        '''

        check_current(cont['current'])
        cont['vac_pump_alarm_checked'] = True

        if DEBUGGING:
            logging.info(f"Current: {cont['current']}")
            logging.info(f"Hydrocarbons: {cont['hydrocarbons']}")

    ### Check for an overfill
    check_overfill()


def passcode():

    global window_pass
    global window

    window_pass['passcode_inner'].update(visible=True) 
    window_pass.un_hide()


    window_pass.move(0,-40)

    window.hide()

    # Loop forever reading the window's values, updating the Input field
    keys_entered = ''
    window_pass['input'].update(keys_entered) 
    
    while True:

        #window_pass.BringToFront()

        event, values = window_pass.read()  # read the window
        if event == sg.WIN_CLOSED:  # if the X button clicked, just exit
            break
        if event == 'Clear':  # clear keys if clear button
            keys_entered = ''

        elif event == 'key_back':
            keys_entered = values['input'][:-1]

        elif event in '1234567890':
            keys_entered = values['input']  # get what's been entered so far
            keys_entered += event  # add the new digit
        elif event == 'Submit':
            keys_entered = values['input']
    
            break

        window_pass['input'].update(keys_entered)  # change the window to reflect current key string

    window.un_hide()
    window_pass.hide()

    return keys_entered


def invalid_code(code):
    msg = f'Invalid Code. You entered: {code}'
    sg.popup(msg,location=(300,50),line_width=64, no_titlebar=True, modal=True,keep_on_top=True,auto_close=True, auto_close_duration=10)


def critical_alarm():

    #return False

    #alarms['press_sensor_alarm'] = True

    if alarms['vac_pump_alarm'] or \
        alarms['overfill_alarm'] or  \
        alarms['maint_alarm'] or \
        alarms['press_sensor_alarm']:
        
        

        return True
    else:
        return False
        

def one_sec_updates():

    '''These are all the things to do once every second'''

   
    global cont
    global dt
    global run_cyc
    global alarms
    global locked
    global kickstart_timer
    global kickstart_time
    global run_step
    global run_timer
    global run_steps
    global step_count
    global accum_time
    global mode
    global run_mode
    global cycle_time
    global reboot_time
    global elapsed_test_time
    global manual_purge_mode
    global manual_purge_count
    global event

    global special_run_count
    
    cycle_timer = timer()

    try: event
    except NameError: event = "None"

    try: critical
    except NameError: critical = False

    # print (f'Runcycle: {run_cyc}, Run Mode: {run_mode},run_step: {run_step}, Event: {event}, Screen: {screen_name}, Critical: {critical}')

    print(f"Hydrocarbons: {cont['hydrocarbons']}")
    
    cur_mode = 0
    step_time = 0

    reboot_time = check_reboot(reboot_time)

    cont2 = load_controller()


    if alarms['sd_card_alarm']:
        logging.error("USB Flash media not found.")
        beep()

    dt = datetime.now(tz=tz_mexico)
    window['datetime'].update(dt.strftime("%m/%d/%Y %H:%M"))
    window.read(timeout=1)

    if 'test_purge_mode' not in cont2:
        cont2['test_purge_mode'] = None
        save_cont(cont2)


    if cont2['test_mode'] == True and cont['test_mode'] == False:
        print("Entering Test mode from Remote...")
        cont['test_mode'] = True
        test_mode_on()

    elif cont['test_mode'] == True and cont2['test_mode'] == False:
        print("Exiting Test mode from Remote...")
        cont['test_mode'] = False
        test_mode_off()
 
        #all_stop()

    elif cont['test_mode'] == True:

        if DEBUGGING:
            print(f'{bcolors.BOLD}')
            print(f'##########################')    
            print(f'## Test Mode ACTIVATED. ##')
            print(f'##########################')  
            print(f'{bcolors.ENDC}')  

    else:

        if DEBUGGING:
            print(f'{bcolors.BOLD}')
            print(f'##############################')  
            print(f'## Normal Mode:             ##')  
            print(f'## Test Mode NOT Activated. ##')
            print(f'##############################')  
            print(f'{bcolors.ENDC}')

    if cont2['test_purge_mode'] and not cont['test_purge_mode']:

        if DEBUGGING:
            print(f'{bcolors.BOLD}')
            print(f'#########################################')  
            print(f'## Purge Mode:                         ##')  
            print(f'## Test Mode NOT Activated.            ##')
            print(f'## Entering PURGE Mode from Remote...  ##')
            print(f'#########################################') 
            print(f'{bcolors.ENDC}')

        cont['test_purge_mode'] = True
        manual_purge_on()


    if cont['test_purge_mode'] == True and cont2['test_purge_mode'] == False:

        if DEBUGGING:
            print(f'{bcolors.BOLD}')
            print(f'#########################################')  
            print(f'## Purge Mode:                         ##')  
            print(f'## Test Mode NOT Activated.            ##')
            print(f'## Exiting PURGE Mode from Remote...   ##')
            print(f'#########################################') 
            print(f'{bcolors.ENDC}')


        cont['test_purge_mode'] = False
        manual_purge_off()
        save_cont(cont2)



    if DEBUGGING:


        lpa = alarms['low_pressure_alarm']
        zpa = alarms['zero_pressure_alarm']
        hpa = alarms['high_pressure_alarm']
        vpa = alarms['var_pressure_alarm']

        print(f'{bcolors.RESET}')  ### Reset Terminal

        print(f"\nDebug Mode: {bcolors.HEADER}{DEBUGGING}{bcolors.ENDC}\n")


        print(f"Remote Test Mode: {bcolors.HEADER}{cont2['test_mode']}{bcolors.ENDC}")
        print(f"Remote Purge Mode: {bcolors.HEADER}{cont2['test_purge_mode']}{bcolors.ENDC}")
        print(f"Local Test Mode: {bcolors.HEADER}{cont['test_mode']}{bcolors.ENDC}")
        print(f"Local Purge Mode: {bcolors.HEADER}{cont['test_purge_mode']}{bcolors.ENDC}")
        print(f"Manual Purge Mode: {bcolors.HEADER}{manual_purge_mode}{bcolors.ENDC}")

        print(f"{bcolors.xy(4,12)}{bcolors.WARNING}Primary Alarms:{bcolors.ENDC}")
        
        print(f"{bcolors.xy(4,14)}Vac Pump Alarm........: {bcolors.HEADER}{alarms['vac_pump_alarm']}{bcolors.ENDC}")
        print(f"{bcolors.xy(4,15)}Overfill Alarm........: {bcolors.HEADER}{alarms['overfill_alarm']}{bcolors.ENDC}")
        print(f"{bcolors.xy(4,16)}Maintenance Alarm.....: {bcolors.HEADER}{alarms['maint_alarm']}{bcolors.ENDC}")
        print(f"{bcolors.xy(4,17)}Pressure Sensor Alarm.: {bcolors.HEADER}{alarms['press_sensor_alarm']}{bcolors.ENDC}")

        print(f"{bcolors.xy(40,14)}Low Pressure Alarm....: {bcolors.WARNING if lpa else bcolors.HEADER}{lpa}{bcolors.ENDC}")
        print(f"{bcolors.xy(40,15)}High Pressure Alarm...: {bcolors.WARNING if hpa else bcolors.HEADER}{hpa}{bcolors.ENDC}")
        print(f"{bcolors.xy(40,16)}Zero Pressure Alarm...: {bcolors.WARNING if zpa else bcolors.HEADER}{zpa}{bcolors.ENDC}")
        print(f"{bcolors.xy(40,17)}Var Pressure Alarm....: {bcolors.WARNING if vpa else bcolors.HEADER}{vpa}{bcolors.ENDC}")


        print(f'\nRun Cycle: {bcolors.HEADER}{run_cyc}{bcolors.ENDC}')



    pressure_sensor_alarm(cont['pressure'])

    if not 'was_test_mode' in cont:
        cont['was_test_mode'] = False

    if cont["test_mode"]:
    
        if time.time() - alarms['test_start_timer'] < HOURS4:
            cont['was_test_mode'] = cont['test_mode']
            test_mode()

        else:
            alarms['test_start_timer'] = 0.0
            cont['test_mode'] = False
            cont['was_test_mode'] = False
            all_stop()

    else:

        pass



    if profile == 'CS8' or profile == 'CS12':

        zero_pressure_alarm(cont['pressure'])
        low_pressure_alarm(cont['pressure'])
        high_pressure_alarm(cont['pressure'])
        var_pressure_alarm(cont['pressure'])

        alarms = check_alarms(alarms)

    cont['faults'] = create_faultcode(alarms)

    alarms = check_buzzer(cont,alarms)

    ### I am changing this logic because I think the else clauses in 92X and below might be allowng the GM to run even if there is a vacpump failure.



    critical = False

    if critical == False:

        if run_cyc:
        
            if run_timer == 0:
                run_timer = timer()

            ## returns an array of steps consisting of mode and time

            run_steps = run_cycle(run_mode)

            print(f'\n')
            print(f'##########################')
            print(f'## {bcolors.HEADER} Run Mode: {bcolors.WARNING} {run_mode} {bcolors.ENDC}')
            print(f'##########################\n')

            step_count = len(run_steps)
                
            cur_mode,step_time = run_steps[run_step]

            ### Set Vac Pump Alarm Checked 
            if cur_mode == 1:
                cont['vac_pump_alarm_checked'] = False

            accum_time = int(timer()-run_timer)
            cycle_time = int(timer()-cycle_timer)

            if 'curr_counter' not in cont:
                cont['curr_counter'] = 0

            if DEBUGGING:
                print(f'\n')

                print(f'Cycle.....: {bcolors.HEADER}{cont["runcycles"]}{bcolors.ENDC}', end = ' ') 
                print(f'Step......: {bcolors.HEADER}{run_step}{bcolors.ENDC}', end = ' ')
                print(f'Duration..: {bcolors.HEADER}{step_time}{bcolors.ENDC}', end = ' ') 
                print(f'Accumlated: {bcolors.HEADER}{accum_time}{bcolors.ENDC}', end = ' ')
                print(f'Mode......: {bcolors.HEADER}{cont["mode"]}{bcolors.ENDC}', end = ' ') 
                print(f'Pressure..: {bcolors.HEADER}{cont["pressure"]}{bcolors.ENDC}', end = ' ') 
                print(f'Faults....: {bcolors.HEADER}{cont["faults"]}{bcolors.ENDC}', end = ' ')
                print(f'Counter...: {bcolors.HEADER}{cont["curr_counter"]}{bcolors.ENDC}')

                print(f'\n')
            
                print(f'elapsed: run_step / cycle /  step time : {run_step} / {accum_time} / {step_time}')    

                print(f'\n') 

                print(f'Cycle Time: {round(timer() - cycle_time,2)} sec')

            set_relays(cur_mode)
            

            if timer() - run_timer > step_time:
                
                print(f'Reaching here at least.....')

                if cont["test_mode"]:
                    if (run_mode == 'special_purge') or (run_mode == 'manual_purge'):
                    
                        print(f'Test Mode: Special Purge')
                        
                        #elapsed_test_time = 0
                        special_run_count = 0 

                run_step = run_step + 1

                if run_step >= step_count:

                    ### Probably unnecessary

                    if run_mode == 'manual_purge':
                        run_cyc = False
                        run_step = 0
                        run_timer = 0     

                    #  This section is what to do after the system runs out of steps in a run sequence
                    #  Reset everything
                
                    set_mode(0)  ### reset mode to idle
                    set_relays(0)
                    run_timer = 0
                    run_step = 0
                    

                    #  Increment the runcycle counter
                    
                    cont['runcycles'] = cont['runcycles'] + 1
                    kickestart_timer = timer()

                    # store the current runcycle
                    
                    save_runcycles(cont['runcycles'])
                
                    if continuous_mode == True:
                        run_steps = run_cycle(run_mode) ## returns an array of steps consisting of mode and time
                        step_count = len(run_steps)
                        run_step = 0
                        cur_mode,step_time = run_steps[run_step]
                        # run_timer = timer()
                    else:

                        #print("HERE IS THE CULPRIT")
                        run_cyc = False
                    
                run_timer = timer()    

        ###  This directive establishes a normal RUN mode

        elif not locked and not run_cyc and (cont['pressure'] >= cont['pressure_set_point']):

            ##  Keep system from running on any screen other than Maintenanance or Main
            if screen_name == "Main Screen":

                run_cyc = True
                run_mode = 'run'
                run_step = 0
                run_timer = 0


        elif not run_cyc and timer() - kickstart_timer > kickstart_elapsed:
            kickstart_timer = timer() #  Reset Kickstart Timer

            ### Run a complete cycle every 12 hours to keep the Vacuum pump vanes from seizing

            if screen_name == "Main Screen":
                run_cyc = True
                run_mode = 'run'
                run_step = 0
                run_timer = 0

                print(f'{bcolors.HEADER}12-Hour Kickstart: {bcolors.ENDC}') 
                logging.info("12-Hour Kickstart Triggered")


    ##  Added 2022-08-21 to save controller condition to redis on every pass

    save_controller(cont)
    save_alarms(alarms)


def any_other_alarm():

    '''
    This Alarm function tracks whether or not ANY of the Non-pressure Alarms
    are currently active or not
    '''

    global alarms

    if alarms['overfill_alarm'] or \
        alarms['sd_card_alarm'] or \
        alarms['vac_pump_alarm'] or \
        alarms['press_sensor_alarm'] or \
        alarms['tls_relay'] or \
        alarms['maint_alarm']:

        return True
    else:
        return False



def clear_pressure_alarms():

    global alarms

    print('*** Clearing Pressure Alarms ***')

    alarms['low_pressure_alarm'] = False
    alarms['high_pressure_alarm'] = False
    alarms['zero_pressure_alarm'] = False
    alarms['var_pressure_alarm'] = False

    alarms['med_alarm_time'] = 0
    alarms['shutdown_alarm_time'] = 0 
    alarms['shutdown_alarm'] = False
    dispenser_shutdown.value = True

    alarms['zero_pressure_start'] = 0
    alarms['high_pressure_start'] = 0
    alarms['low_pressure_start'] = 0
    alarms['var_pressure_start'] = 0
    
    ### Reset buzzer conditions

    alarms['buzzer_high'] = True
    alarms['buzzer_low'] = True
    alarms['buzzer_zero'] = True
    alarms['buzzer_var'] = True

    #return alarms

def clear_motor_alarm(alarms):

    global cont 

    alarms['vac_pump_alarm'] = False
    alarms['med_alarm_time'] = 0
    alarms['critcal_alarm_time'] = 0
    cont['curr_counter'] = 0

    return alarms

def clear_overfill_alarm():

    alarms['overfill_alarm'] = False


def check_buzzer(cont,alarms):
    
    if alarms['low_pressure_alarm'] == True:

        if alarms['buzzer_low']:
            one_beep()
            alarms['buzzer_low'] = False

    if alarms['high_pressure_alarm'] == True:

        if alarms['buzzer_high']:
            one_beep()
            alarms['buzzer_high'] = False

    if alarms['zero_pressure_alarm'] == True:

        if alarms['buzzer_zero']:
            one_beep()
            alarms['buzzer_zero'] = False
    
    if alarms['var_pressure_alarm'] == True:

        if alarms['buzzer_var']:
            one_beep()
            alarms['buzzer_var'] = False

    return alarms


def create_faultcode(alarms):

    global cont
    
    fc = 0

    if alarms['vac_pump_alarm'] == True:
        fc = fc + 1 

    if alarms['maint_alarm'] == True:
        fc = fc + 2 

    if alarms['overfill_alarm'] == True:
        fc = fc + 4 

    if alarms['sd_card_alarm'] == True:
        fc = fc + 8 

    if alarms['low_pressure_alarm'] == True:
        fc = fc + 16 

    if alarms['high_pressure_alarm'] == True:
        fc = fc + 32

    if alarms['zero_pressure_alarm'] == True:
        fc = fc + 64

    if alarms['var_pressure_alarm'] == True:
        fc = fc + 128

    if alarms['press_sensor_alarm'] == True:
        fc = fc + 256 

    if alarms['shutdown_alarm'] == True:
        fc = fc + 512 

    if cont['test_mode']:
        fc = fc + 32768

    return fc


def check_alarms(alarms):

    if DEBUGGING:

        print(f'{bcolors.xy(4,22)}{bcolors.FAIL}In Check Alarms...')

        print(f"{bcolors.xy(4,24)}Low Pressure...: {alarms['low_pressure_alarm']} Alarm Time: {int(timer()-alarms['low_pressure_start'] ) }")
        print(f"{bcolors.xy(4,25)}High Pressure..: {alarms['high_pressure_alarm']} Alarm Time: {int(timer()-alarms['high_pressure_start']) }")
        print(f"{bcolors.xy(4,26)}Var Pressure...: {alarms['var_pressure_alarm']} Alarm Time: {int(timer()-alarms['var_pressure_start'] ) }")
        print(f"{bcolors.xy(4,27)}Zero Pressure..: {alarms['zero_pressure_alarm']} Alarm Time: {int(timer()-alarms['zero_pressure_start']) }")

    if (alarms['low_pressure_alarm'] is False and \
        alarms['high_pressure_alarm'] is False and  \
        alarms['var_pressure_alarm'] is False and  \
        alarms['zero_pressure_alarm'] is False):

        #alarms['low_pressure_start'] = 0
        alarms['shutdown_alarm_time'] = 0
        alarms['shutdown_alarm'] = False

    else:

        if DEBUGGING:


            print(f'{bcolors.xy(4,30)}{bcolors.FAIL}There are pressure alarms...{bcolors.ENDC}')

        if (alarms['low_pressure_alarm'] or \
            alarms['high_pressure_alarm'] or \
            alarms['var_pressure_alarm'] or \
            alarms['zero_pressure_alarm']):

            if alarms['shutdown_alarm_time'] == 0:
                alarms['shutdown_alarm_time'] = time.time()
                
                print("Shutdown Timer started") if DEBUGGING else ""

            print(f"Shutdown Timer: {alarms['shutdown_alarm_time']}") 

    return alarms


def save_sd_card(to_file):

    '''

    Write data to a file on SD Card or Flash

    '''

    header = "GMID,Seq,UST Pressure,Runcycles,Faults,Mode,Temp,Current,DevID,Local Datetime, UTC Datime\n"

    try:

        directory = delete_duplicate_data_folder()
        path = f"{directory}/logfile.csv"
        
        g = open(f"{directory}/logfile.json","a")

    except:
        logging.error("USB Flash media not found.")
        alarms['sd_card_alarm'] = True
        beep()
        
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


def save_local_file(local_file):

    '''
    
    Write data to a file on local drive

    '''

    path = "/home/pi/python/logfile.csv"
    header = "GMID,Seq,UST Pressure,Runcycles,Faults,Mode,Temp,Current,DevID,Local Datetime, UTC Datime\n"

    if not os.path.exists(path):

        f_local = open("/home/pi/python/logfile.csv","a")
        f_local.write(header)
        f_local.close()

    f_local = open("/home/pi/python/logfile.csv","a")

    csv_writer = csv.writer(f_local)
    csv_data = csv_writer.writerow(local_file.values())
   
    f_local.close()    


def save_local_file_old(local_file):

    '''
    
    Write data to a file on local drive

    '''

    f_local = open("/home/pi/python/logfile.csv","a")

    csv_writer = csv.writer(f_local)
    csv_data = csv_writer.writerow(local_file.values())
   
    f_local.close()        


def get_mode():

    ''' Turn the numeric mode into a Text Description '''

    mode = ''

    if cont['mode']==0:
        mode="Idle"
    elif cont['mode']==1:
        mode="Run"
    elif cont['mode']==2:
        mode="Purge"
    elif cont['mode']==3:
        mode="Burp"
    
    return mode


def header():
    window['head'].update(visible=True) 


def footer():
    window['foot'].update(visible=True)


def screen_on(screen):
    window[screen].update(visible=True)


def screen_off(screen):
    if screen:
        window[screen].update(visible=False)
        window['foot'].update(visible=False)


def switch_screen(curr_screen,new_screen):

    if curr_screen != new_screen:
        screen_off(curr_screen)
        screen_on(new_screen)


def set_screen(screen):

    global curr_screen

    print(f'Screen, New: {screen}, From: {curr_screen}')

    if screen != curr_screen:

        header()
        switch_screen(curr_screen, screen)
        if screen != 'a':
            footer()

    curr_screen = screen


def init_current(c):

    global cont
    
    ## Current relates variables

    c['curr_amp'] = 0.0
    c['curr_sum'] = 0.0
    c['curr_samp'] = 0
    c['curr_avg'] = 0.0
    c['curr_rms'] = 0.0
    #cont['adc_zero'] = 15150.0
    c['adc_value'] = 0.0
    c['current'] = 0.0
    c['curr_counter'] = 0
    c['calibration'] = 0

    return c


def reboot_everything():

    global reboot_time
    
    ### Complete reboot of system
    logging.info("*** Rebooting System from blues JSON directive")

    # Update UI to reference rebooting

    reboot_time = 60

    window['head_right'].update("REBOOTING")
    window.read(timeout=1)

    os.system("sudo shutdown -r 1")


def cancel_reboot():

    global reboot_time

    logging.info("*** Cancel Reboot System from blues JSON directive")

    # Cancel Reboot
    reboot_time = 0
    os.system("sudo shutdown -c")    


def check_reboot(reboot_time):
    
    if reboot_time !=0:
        reboot_time = reboot_time - 1
    
    return reboot_time


def restart_program():

    ### RESTART PROGRAM WITH NEW COPY OF PROGRAM

    logging.info("*** Rebooting System to load new program!")

    window['head_right'].update("REBOOTING")
    window.read(timeout=1)

    python = sys.executable
    os.execl(python, python, *sys.argv)  

    # *** Changed Paraneters on line above from "* sys.argv"
    # *** to "*sys.argv"  This might affect rebooting so test


def extract_ip():

    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:       
        st.connect(('10.255.255.255', 1))
        IP = st.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        st.close()
    return IP



#####
#####  The main screens function that embodies all the screens, wrapped into one
#####

def screens():

    global cont
    global alarms
    global one_sec_timer
    global run_cyc
    global continuous_mode
    global run_mode
    global step_count
    global run_step
    global locked
    global dt
    global maint_code
    global startup_code
    global cycle_time
    global run_timer
    global accum_time
    global screen_name
    global now2

    global window_pass
    global window

    global head_left
    global head_right
    global modem_status

    global file_download

    global was_active
    screen_name = "Main Screen"

    global curr_screen 
    
    curr_screen = None

    one_sec_timer = timer()
    ten_min_timer = timer()
    leak_test_timer = timer()
    eff_test_timer = timer()

    cycle_time = timer()
    scan_time = timer()
    accum_time = 0

    code = ''

    but_font = 'Piboto 18'
    text_font = 'Piboto 16'
    lock_font = 'Piboto 8'
    space_font = 'Piboto 12'
    status_font = 'Piboto 30'
    small_font = 'Piboto 12'
    alarm_font = 'Piboto 16'
    pad_font = 'Piboto 18'
    input_font = 'Piboto 18'
    date_font = 'Piboto 8'
    heading_font = 'Piboto 20 bold'
    display_font = 'Piboto 22 bold'

    modem_status = f"{cont['access_tech']}/{cont['power_state']}/{cont['modem_state']}/{cont['signal_quality']}"

    bypass = False
    startup_bypass = False

    profile = get_profile()

    print(f"Profile: {profile}")

    serial = get_serial()

    print(f"Serial: {serial}")

    cont['serial'] = serial

    #save_controller(cont)  #####

    print(f"Cont/Serial: {cont['serial']}")

    cont['startup'] = get_startup_code()

    ### Check for valid startup code

    if ((cont['startup'] == serial[-6:]) or (cont['startup'] == vst_code2)):
        locked = False
    else:
        locked = True

    cont = get_controller() ##  Get initial saved Controller state

    cont['runcycles'] = get_runcycles(cont)

    #get_wireless()
    local_ip = extract_ip()
    cont['local_ip'] = local_ip

    cont['scr_width'] = screen_width
    cont['scr_height'] = screen_height
    cont['test_mode'] = False

    ## Update controller object with current values

    cont['gmid'] = device_name
    cont['version'] = version

    print(f"Device Name: {device_name}")
    print (f"Device Name: {cont['gmid']}")

    #init_current()  ## initialize motor current
 
    print(f'Controller ADC Calibration Zero: {cont["adc_zero"]}')

    #get_runcycles()

    sg.theme('DarkBlue 15')

    #sg.theme_background_color('#FF0000')

    ## Create master list of Alarms

    alarm = list( {} for i in range(10) )

    alarm[0]['text'] = "A - VACUUM PUMP" #.......1
    alarm[1]['text'] = "B - PANEL POWER" #.......2
    alarm[2]['text'] = "C - OVERFILL" #..........4
    alarm[3]['text'] = "D - DIGITAL STORAGE" #...8
    alarm[4]['text'] = "E - UNDER PRESSURE" #...16
    alarm[5]['text'] = "F - OVER PRESSURE" #....32
    alarm[6]['text'] = "G - ZERO PRESSURE" #....64
    alarm[7]['text'] = "H - VAR PRESSURE"  #...128
    alarm[8]['text'] = "I - PRESSURE SENSOR" # 256
    alarm[9]['text'] = "J - 72 HOUR SHUTDOWN" #512
    
    # Setup initial Objects
        
    for i in range(10):
        alarm[i]['alarm'] = sg.Text(alarm[i]['text'],size=(32,1),font=(alarm_font))

    ## Determine alarm based on Alarm Code

    
    def alarm_updates():
    
        ## Pick the list of alarms that will be updated based on the currnet profile

        if profile == 'CS8':
            r = [0,1,2,3,4,5,6,7,8,9]
        elif profile == 'CS12':
            r = [0,1,2,3,4,5,6,7,8,9]
        else:
            r = [0,1,2,3,8]

        for i in r:

            ## Compute the alarm value based on the current profile

            if cont['faults'] & pow(2,i):
                alarm[i]['value'] = True
            else:
                alarm[i]['value'] = False


            if alarm[i]['value'] == True:
                alarm[i]['alarm'].Update(value= alarm[i]['text'] + ' ALARM')
                alarm[i]['alarm'].Update(background_color='red')
            else:
                alarm[i]['alarm'].Update(value=alarm[i]['text'] + ' NORMAL')
                alarm[i]['alarm'].Update(background_color='green')

    
    def set_manual_mode_status(mode):

        if mode == 0:

            light_off(0)
            light_off(1)
            light_off(2)
            light_off(3)

            #indicators([0,0,0,0])
            
        elif mode == 1:
            
            light_on(0)
            light_on(1)
            light_off(2)
            light_on(3)

            #indicators([1,1,0,1])
            
        elif mode == 2:
                    
            light_on(0)
            light_off(1)
            light_on(2)
            light_off(3)

             #indicators([1,0,1,0])
            
        elif mode == 3:
                    
            light_off(0)
            light_off(1)
            light_off(2)
            light_on(3)

            #indicators([0,0,0,1])
            
        else: 
                        
            light_off(0)
            light_off(1)
            light_off(2)
            light_off(3)

            #indicators([0,0,0,0])


    def indicators(indicator):

        #global relays

        for i in indicator:
            c = "white" if indicator[i] == 0 else "gray"
            graph.TKCanvas.itemconfig(relays[i],fill=c)    
            

    def light_on(r):

        if r == 0:
            graph.TKCanvas.itemconfig(relay1,fill="green")

        elif r==1:
            graph.TKCanvas.itemconfig(relay2,fill="green")

        elif r==2:
            graph.TKCanvas.itemconfig(relay3,fill="green")

        elif r==3:
            graph.TKCanvas.itemconfig(relay4,fill="green")


    def light_off(r):

        if r == 0:

            graph.TKCanvas.itemconfig(relay1,fill="black")

        elif r==1:
            graph.TKCanvas.itemconfig(relay2,fill="black")

        elif r==2:
            graph.TKCanvas.itemconfig(relay3,fill="black")

        elif r==3:
            graph.TKCanvas.itemconfig(relay4,fill="black")

            
    ###
    ###  Layouts for screens starts here
    ###

    buttons = [ [sg.Button('Maintenance',font=(but_font)),sg.Button('Faults & Alarms',font=(but_font))]]
    silent_button = [ [sg.Button('Silence',font=(but_font))]]

    layout_main = [

        [sg.Text('UST Pressure (IWC):' , size=(20,0), justification = 'r', font=(text_font)),
        sg.Text(cont['pressure'], size=(6,0), justification = 'c', font=(text_font), background_color='dark slate blue', text_color='white', key='press'),
        
        sg.Text('Run Cycles: ', size=(12,0), justification = 'r', font=(text_font)),
        sg.Text(cont['runcycles'], size=(6,0), justification = 'c', font=(text_font), background_color='dark slate blue', text_color='white', key='runcycles')],
        
        [sg.Text(' ', size=(20,2), font=(space_font))],
        
        [sg.Text('STARTING', size=(40,0), justification = 'c', font=(status_font), background_color='green', text_color='white',key='main_status')],
        
        [sg.Text(' ', size=(20,2), font=(space_font))],
        
        [sg.Column(buttons,justification='c', element_justification='c', visible=True)],
        [sg.Column(silent_button,justification='c', element_justification='c', visible=False, key='sb')],
       

        [sg.Text(' ', size=(20,3), font=(space_font))],
        
    ]
    
    if alarms['modem_alarm']:
        status_modem = "ALARM"
    else:
        status_modem = "GOOD"

    ### Layout for About Screen

    print(f"{cont['band']}")

    #modem_text = f"{cont['band']}/{cont['rssi']}/{cont['bars']}"
    
    col_about1 = [
        [sg.Text('Profile:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(profile+'A', size=(20,1),font=(small_font))],
        [sg.Text('Version:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(cont['version'], size=(20,1),font=(small_font))],
        [sg.Text('Serial Number:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(cont['serial'], size=(20,1),font=(small_font))],
        [sg.Text('Device Name:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(cont['gmid'], size=(20,1),font=(small_font))],
        [sg.Text('Overfill Relay:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(not alarms['tls_relay'], size=(20,1),font=(small_font))],
        [sg.Text('Cycles / Block:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(cont['cycles_per_block'], size=(20,1),font=(small_font))],
        
        ]
        
    col_about2 = [
        [sg.Text('Debug:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text("True" if DEBUGGING else "False", size=(20,1),font=(small_font))],
        [sg.Text('Secrets:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(secret_type, size=(20,1),font=(small_font))],
        [sg.Text('Modem Status:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(status_modem, size=(20,1),font=(small_font))],
        [sg.Text('Local IP:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(cont['local_ip'], size=(20,1),font=(small_font))],
        [sg.Text('Device ID:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(cont['deviceID'], size=(20,1),font=(small_font))],
        [sg.Text('Modem:', text_color='white', justification='r',size=(20,1),font=(small_font)),sg.Text(modem_status, size=(20,1),font=(small_font))],

        ]

    layout_about =[
    
        [sg.Column(col_about1, size=(350,250),justification='c'),
        sg.Column(col_about2, size=(350,250),justification='c')], 
        
    ]

    ### Layouts for Changing Profiles

    layout_profiles = [

        #[sg.Text(' ', size=(12,1),font=(text_font))],
        [sg.Button('CS2',size=(7,0),font=(text_font)),sg.Text('North American', size=(20,1),font=(text_font))],
        [sg.Button('CS3',size=(7,0),font=(text_font)),sg.Text('International', size=(20,1),font=(text_font))],
        [sg.Button('CS8',size=(7,0),font=(text_font)),sg.Text('Mexican Non-GVR', size=(20,1),font=(text_font))], 
        [sg.Button('CS9',size=(7,0),font=(text_font)),sg.Text('Mexican GVR', size=(20,1),font=(text_font))],
        [sg.Button('CS12',size=(7,0),font=(text_font)),sg.Text('Franklin Mini-Jet', size=(20,1),font=(text_font))],
        [sg.Text(' ', size=(12,1),font=(space_font))],
    ]


    ### Layouts for Alarms which change, depending on profile

    if profile == 'CS8':

        #  Only CS8 profile has Pressure and 72 Hour Alarms

        col_alarms = [
            
            [alarm[0]['alarm'], alarm[5]['alarm']],
            [alarm[1]['alarm'], alarm[6]['alarm']],
            [alarm[2]['alarm'], alarm[7]['alarm']],
            [alarm[3]['alarm'], alarm[8]['alarm']],
            [alarm[4]['alarm'], alarm[9]['alarm']],
            
        ]

        layout_alarms = [

            [sg.Text(' ', size=(30,1),font=(space_font))],
            [sg.Column(col_alarms, size=(800,220),justification='c')],
            #[sg.Text(' ', size=(30,1),font=(small_font))],
    
        ]

    elif profile == 'CS12':

        #  Only CS8 and CS12 profile has Pressure and 72 Hour Alarms

        col_alarms = [
            
            [alarm[0]['alarm'], alarm[5]['alarm']],
            [alarm[1]['alarm'], alarm[6]['alarm']],
            [alarm[2]['alarm'], alarm[7]['alarm']],
            [alarm[3]['alarm'], alarm[8]['alarm']],
            [alarm[4]['alarm'], alarm[9]['alarm']],  
        ]

        layout_alarms = [

            [sg.Text(' ', size=(30,1),font=(space_font))],
            [sg.Column(col_alarms, size=(800,220),justification='c')],
            #[sg.Text(' ', size=(30,1),font=(small_font))],
    
        ]

    else:

        #  Alarm layout for everything EXCEPT CS8

        col_alarms = [
            
            [alarm[0]['alarm']], 
            [alarm[1]['alarm']], 
            [alarm[2]['alarm']], 
            [alarm[3]['alarm']], 
            [alarm[8]['alarm']]
                
        ]
    

        layout_alarms = [

            [sg.Text(' ', size=(30,1),font=(space_font))],
            [sg.Column(col_alarms, size=(400,220),justification='c')],
            #[sg.Text(' ', size=(30,1),font=(space_font))],
 
        ]

    ### Layout for passcode entry - old
    
    layout_pass = [

        [sg.Text('Enter Your Passcode',justification='c',font=(text_font),size=(20,1))],
        [sg.Input(size=(17, 1), font=(input_font),justification='c', key='input')],
        [sg.Button('1',size=(5,0),font=(pad_font)), sg.Button('2',size=(5,0),font=(pad_font)), sg.Button('3',size=(5,0),font=(pad_font))],
        [sg.Button('4',size=(5,0),font=(pad_font)), sg.Button('5',size=(5,0),font=(pad_font)), sg.Button('6',size=(5,0),font=(pad_font))],
        [sg.Button('7',size=(5,0),font=(pad_font)), sg.Button('8',size=(5,0),font=(pad_font)), sg.Button('9',size=(5,0),font=(pad_font))],
        [sg.Button('Enter',size=(5,0),font=(pad_font),key='Sub'), sg.Button('0',size=(5,0),font=(pad_font)), sg.Button('⌫', key='key_back', size=(5, 0), font=(but_font))],
        [sg.Button('Clear',size=(5,0),font=(pad_font),key='Clr')],
        [sg.Text(' ', size=(12,2),font=(space_font))]
    ]

    layout_code = [

        [sg.Text('Enter Your Startup Code: ',justification='r',size=(20,1),font=(text_font)),
        sg.Text(' ', size=(6,0),font=(input_font)), sg.Input(size=(12, 1), font=(input_font),justification='l', key='inputA')],
        [sg.Button('1',size=(5,0),key='1A',font=(pad_font)), sg.Button('2',size=(5,0),key='2A',font=(pad_font)), sg.Button('3',size=(5,0),key='3A',font=(pad_font)),sg.Button('A',size=(5,0),key='AA',font=(pad_font)),sg.Button('E',size=(5,0),key='EA',font=(pad_font))],
        [sg.Button('4',size=(5,0),key='4A',font=(pad_font)), sg.Button('5',size=(5,0),key='5A',font=(pad_font)), sg.Button('6',size=(5,0),key='6A',font=(pad_font)),sg.Button('B',size=(5,0),key='BA',font=(pad_font)),sg.Button('F',size=(5,0),key='FA',font=(pad_font))],
        [sg.Button('7',size=(5,0),key='7A',font=(pad_font)), sg.Button('8',size=(5,0),key='8A',font=(pad_font)), sg.Button('9',size=(5,0),key='9A',font=(pad_font)),sg.Button('C',size=(5,0),key='CA',font=(pad_font))],
        [sg.Button('Enter',size=(5,0),key='SubB',font=(pad_font)),sg.Button('0',size=(5,0),key='0A',font=(pad_font)),sg.Button('Clear',size=(5,0),key='ClrA',font=(pad_font)),sg.Button('D',size=(5,0),key='DA',font=(pad_font))],

        
        [sg.Text(' ', size=(12,1),font=(space_font))]
    ]

    layout_shutdown = [

        [sg.Text('ACTION ALARM', size=(50,1),justification='c', font=('helvetica 24'))],
        [sg.Text('Station will shut down in', size=(120,1),justification='c', font=(space_font))],
        [sg.Text('00:00:00', size=(120,1),justification='c', font=(space_font), key='shutdown_countdown')],
        [sg.Text('unless the alarm condition is repaired.', size=(120,1),justification='c', font=(space_font))],
        [sg.Text('Contact your SERVICE CONTRACTOR', size=(50,1),justification='c', font=('helvetica 24'))],
        [sg.Text('Find alarm specifics on the "ALARMS" screen', size=(120,1),justification='c', font=(space_font))],
        [sg.Column([ [sg.Button('Acknowledge',size=(12,0),font=(pad_font),key='shutdown_ack')]],justification='c')],
    ]

    layout_shutdown2 = [

        [sg.Text('ACTION ALARM', size=(50,1),justification='c', font=('helvetica 24'))],
        [sg.Text('Your Station is SHUT DOWN!', size=(120,1),justification='c', font=(space_font))],
        [sg.Text('The alarm condition must be repaired.', size=(120,1),justification='c', font=(space_font))],
        [sg.Text('Contact your SERVICE CONTRACTOR', size=(50,1),justification='c', font=('helvetica 24'))],
        [sg.Text('Find alarm specifics on the "ALARMS" screen', size=(120,1),justification='c', font=(space_font))],
        [sg.Column([ [sg.Button('Acknowledge',size=(12,0),font=(pad_font),key='shutdown_ack2')]],justification='c')],
    ]

    ### Layout for the Overfill Override Screen

    overfill_text = '''The overfill override is to be used only when testing the relay on the fuel monitoring system. If there is genuinely an overfill condition of over 90% tank volume, DO NOT override the alarm. Overriding an actual alarm can damage the system.'''
    
    layout_overfill = [

        [sg.Text(' ', size=(30,1),font=(space_font))],
        [sg.Text(overfill_text, size=(48,4),font=(small_font))],
        [sg.Text('', size=(30,2),font=(space_font))],
        [sg.Column([[sg.Button('Confirm Overide of Overfill Alarm',size=(26,0),font=(but_font),key='confirm_overfill_override')]],justification='c')],
    
        [sg.Text(' ', size=(1,1),font=(space_font))],

    ]
    ###  Layout for Manual Screen


    layout_manual = [

        [sg.Text(' ', size=(7,0),font=(space_font)), sg.Graph(canvas_size=(600,100), graph_bottom_left=(0,0), graph_top_right=(599,99),key='graph')],
    
        #[sg.Text(' ', size=(11),font=(text_font))],
        [sg.Text('Run Cycles', size=(24,0), justification = 'c',font=(text_font)),sg.Text(' ', size=(6,0),font=(text_font)),sg.Text('Mode', size=(24,0), justification = 'c',font=(text_font))],
        [sg.Text('', size=(12,1),font=(space_font)),
        sg.Text(cont['runcycles'], size=(12,0), justification = 'c', font=(text_font), background_color='gray', text_color='yellow', key='runcycles_man'),sg.Text(' ', size=(10,0),font=(space_font)),
        sg.Text('', size=(4,1),font=(space_font)),
        sg.Text(cont['mode'], size=(12,0), justification = 'c', font=(space_font), background_color='gray', text_color='yellow', key='mode_man')],
        [sg.Text('', size=(12,0),font=(text_font)),
        sg.Button('Start',size=(10,0),font=(but_font),key='man_start'),
        sg.Button('Stop',size=(10,0),font=(but_font),key='man_stop')],

        [sg.Text(' ', size=(30,1),font=(space_font))],

    ]

    ### Layout for Startup Screen

    if profile == 'CS8' or profile == 'CS12':
 
 
        startup_col1 = [
            [sg.Button('Manual Mode',size=(12,0),font=(but_font))],
            [sg.Button('Overfill Override',size=(12,0),font=(but_font))],
            [sg.Button('Profiles',size=(12,0),font=(but_font))],
        ]
        
        startup_col2 = [
            [sg.Button('Debug On',size=(12,0),font=(but_font))],
            [sg.Button('Start Up Code',size=(12,0),font=(but_font))],
            [sg.Button('About',size=(12,0),font=(but_font))],
        ]

        startup_col3 = [
            [sg.Button('Debug Off',size=(12,0),font=(but_font))],
            [sg.Button('Lock',size=(12,0),font=(but_font))],
            [sg.Button('Test',size=(12,0),font=(but_font))],
        ]

        startup_menu = [
            [
                sg.Column(startup_col1, size=(200,200),justification='c',background_color='#151680'),
                sg.Column(startup_col2, size=(200,200),justification='c',background_color='#151680'),
                sg.Column(startup_col3, size=(200,200),justification='c',background_color='#151680'),

            ], 
        
            
            # [sg.Button('Manual Mode',size=(12,0),font=(but_font)),sg.Button('Debug On',size=(8,0),font=(text_font)),sg.Button('Debug Off',size=(8,0),font=(text_font))],
            # [sg.Button('Overfill Override',size=(12,0),font=(but_font)),sg.Button('Start Up Code',size=(12,0),font=(but_font)),sg.Button('Lock',size=(5,0),font=(small_font))],
            # [sg.Button('Profiles',size=(12,0),font=(but_font)),sg.Button('About',size=(12,0),font=(but_font))],
            # [sg.Button('Test',size=(12,0),font=(but_font))],
        
        ]
    else:

        startup_menu = [
            
            [sg.Button('Manual Mode',size=(12,0),font=(but_font)),
            sg.Button('Pressure Limits',size=(12,0),font=(but_font))],

            [sg.Button('Overfill Override',size=(12,0),font=(but_font)),
            sg.Button('Start Up Code',size=(12,0),font=(but_font)),sg.Button('Lock',size=(5,0),font=(small_font))],
            
            [sg.Button('Profiles',size=(12,0),font=(but_font)),
            sg.Button('About',size=(12,0),font=(but_font))],
        
        ]


    startup_top_menu = [
        [sg.Text('UST Pressure (IWC):', size=(18,0), justification = 'r', font=(text_font), text_color='yellow'),
        sg.Text(cont['pressure'], size=(6,0), justification = 'c', font=(text_font), background_color='gray', text_color='yellow',key='press_startup'),
        sg.Button('Calibrate',font=(small_font))]]


    layout_startup = [

        [sg.Frame('',startup_top_menu, size=(800,40),border_width=0,element_justification='c')],
        [sg.Column(startup_menu,size=(640,220),justification='c',background_color='#151680')],

    ]

    ### Layout for Maintenance Screen
    if profile == 'CS8' or profile == 'CS12':

        maint_menu = [
            [sg.Button('Clear Press Alarm',size=(16,0),font=(but_font),key='clear_press')],
            [sg.Button('Clear Motor Alarm',size=(16,0),font=(but_font))],
            [sg.Button('Run Tests',size=(16,0),font=(but_font))],
            [sg.Button('Startup Screen',size=(16,0),font=(but_font))],
        ]
    
    else:

        maint_menu = [
            [sg.Button('Clear Motor Alarm',size=(16,0),font=(but_font))],
            [sg.Button('Run Tests',size=(16,0),font=(but_font))],
            [sg.Button('Startup Screen',size=(16,0),font=(but_font))],
            [sg.Text(" ", font=(text_font),size=(2,2))],
        ] 

    top_menu_maint = [

        [sg.Text('UST Pressure (IWC):', size=(20,0),justification = 'r', font=(text_font), text_color='yellow'),
        sg.Text(cont['pressure'], size=(6,0), justification = 'c', font=(text_font), background_color='gray', text_color='yellow',key='press_maint'),
        sg.Text(" ",size=(6,0),font=(space_font))]
    ]

    layout_maint = [

        [sg.Column(top_menu_maint,justification='c',element_justification='c', size=(400,35))],
        [sg.Column(maint_menu, element_justification='c', justification='c', size=(250,230))],
        
    ]

    runcycle_menu = [
        [sg.Button('Clear Motor Alarm',size=(16,0),font=(space_font))],
        [sg.Button('Run Tests',size=(16,0),font=(space_font))],
        [sg.Button('Startup Screen',size=(16,0),font=(space_font))],
    ] 


    up_down_menu1 = [
        [sg.Button('^',size=(1,0),font=(small_font),key='up1'),sg.Button('v',size=(1,0),font=(small_font),key='dn1')],
    ]

    up_down_menu2 = [
        [sg.Button('^',size=(1,0),font=(small_font),key='up2'),sg.Button('v',size=(1,0),font=(small_font),key='dn2')],
    ]

    up_down_menu3 = [
        [sg.Button('^',size=(1,0),font=(small_font),key='up3'),sg.Button('v',size=(1,0),font=(small_font),key='dn3')],
    ]

    up_down_menu4 = [
        [sg.Button('^',size=(1,0),font=(small_font),key='up4'),sg.Button('v',size=(1,0),font=(small_font),key='dn4')],
    ]

    layout_runcycle = [

        #[sg.Text('Enter a value for the High limit and the Low limit.', size=(64,0), justification = 'c', font=(space_font), text_color='yellow')],
        [sg.Text('These are the values the GM will control the pressure between.', size=(64,0), justification = 'c', font=(text_font), text_color='yellow')],
        
        [sg.Column([[

        sg.Text('High Limit:', size=(10,0), justification = 'r', font=(text_font), text_color='yellow'),
        sg.Text(cont['rc_high_limit'], size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='rc_high_limit'),
        sg.Column(up_down_menu1,justification='c',element_justification='c'),
        
        sg.Text('Low Limit:', size=(10,0), justification = 'r', font=(text_font), text_color='yellow'),
        sg.Text(cont['rc_low_limit'], size=(6,0), justification = 'l', font=(space_font), background_color='gray', text_color='yellow',key='rc_low_limit'),
        sg.Column(up_down_menu2,justification='c',element_justification='c'),
        
        ]],justification='c',element_justification='c')],

        #[sg.Text(" ",size=(1,0),font=(space_font))],
        [sg.HorizontalSeparator(color='white')],
        #[sg.Text(" ",size=(1,1),font=(small_font))],

        #[sg.Text('Enter a value for run ON and OFF times.', size=(64,0), justification = 'c', font=(space_font), text_color='yellow')],
        [sg.Text('These are the values Pump, V1, & V5 will be ON and OFF.', size=(64,0), justification = 'c', font=(text_font), text_color='yellow')],

        [sg.Column([
        [sg.Text('On:', size=(6,0), justification = 'r', font=(space_font), text_color='yellow'),
        sg.Text(cont['rc_on_time'], size=(6,0), justification = 'l', font=(space_font), background_color='gray', text_color='yellow',key='rc_on_time'),
        sg.Column(up_down_menu3,justification='c',element_justification='c'),
        sg.Text('mm:ss', size=(6,0), justification = 'l', font=(space_font), text_color='yellow'),
        sg.Text('Off:', size=(6,0), justification = 'r', font=(space_font), text_color='yellow'),
        sg.Text(cont['rc_off_time'], size=(6,0), justification = 'l', font=(space_font), background_color='gray', text_color='yellow',key='rc_off_time'),
        sg.Column(up_down_menu4,justification='c',element_justification='c'),
        sg.Text('mm:ss', size=(8,0), justification = 'l', font=(space_font), text_color='yellow')]
        ],justification='c',element_justification='c')],

        [sg.Column([
        [sg.Button('Test Mode On',size=(10,0),font=(space_font)),
        sg.Button('Test Mode Off',size=(12,0),font=(space_font)),
        sg.Button('Manual Purge',size=(10,0),font=(space_font)),
        sg.Button('Reset',size=(10,0),font=(space_font),key='test_mode_reset')
        ]
        ],justification='c',element_justification='c')],
    
        [sg.Text(" ",size=(1,1),font=(space_font))],

    ]

    ###  Layout for Test Screen

    #  [sg.Button('Bump Test',size=(16,0),font=(text_font))]]

    if profile == 'CS2':
        test_menu = [
            [sg.Button('Leak Test',size=(16,0),font=(but_font))],
            [sg.Button('Functionality Test',size=(16,0),font=(but_font))],
            [sg.Button('Efficiency Test',size=(16,0),font=(but_font))],
               
        ]

    else:
        test_menu = [
            [sg.Text(" ",size=(1,2),font=(space_font))],
            [sg.Button('Leak Test',size=(16,0),font=(but_font))],
            [sg.Button('Functionality Test',size=(16,0),font=(but_font))],
      
        ]

                
    
    top_menu = [
        [sg.Text('UST Pressure (IWC):', size=(24,0),justification = 'r', font=(text_font), text_color='yellow'),
        sg.Text(cont['pressure'], size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='press_test'),
    ]]

    layout_test = [

        [sg.Column(top_menu,justification='c',element_justification='c')],
        [sg.Column(test_menu,justification='c',element_justification='c')],
        [sg.Text(" ",size=(1,2),font=(space_font))],

    ]

    layout_func = [

        [sg.Button('Start',size=(12,0),font=(but_font),key='func_start'),
        sg.Text('Push the Start Button to begin the Functionality Test. The test will end after 5 complete cycles of 60 sec Run / 60 sec Purge.', size=(35,3),font=(text_font))],
        [sg.Button('Stop',size=(12,0),font=(but_font),key='func_stop'),
        sg.Text('The test will end after 5 complete cycles or when the Stop button is pressed.', size=(32,2),font=(text_font))],
        [sg.Text(' ',size=(1,1),font=(space_font))],
        [sg.Text('Countdown Cycles: ',size=(16,0),font=(text_font)),sg.Text('', size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='func_countdown')],
        [sg.Text(' ',size=(1,1),font=(space_font))],
    ]

    layout_eff = [

        [sg.Button('Start',size=(16,0),font=(but_font),key='eff_start'),
        sg.Text('Push the Start Button to begin the Efficiency Test. The test will end once complete.', size=(40,2),font=(text_font))],
        [sg.Button('Stop',size=(16,0),font=(but_font),key='eff_stop')],
        [sg.Text(' ',size=(12,2),font=(text_font))],
        [sg.Text('Step: ',size=(6,0),font=(text_font)),sg.Text('', size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='eff_step'),
        sg.Text('Mode: ',size=(6,0),font=(text_font)),sg.Text('', size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='eff_mode'),
        sg.Text('Time: ',size=(6,0),font=(text_font)),sg.Text('', size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='eff_time'),
       
        ],
        [sg.Text(' ',size=(1,1),font=(space_font))],
    ]


    layout_leak = [

        [sg.Button('Start',size=(16,0),font=(but_font),key='leak_start'),
        sg.Text('Push the Start Button to begin the Leak Test. The test will end after 30 minutes.', size=(40,2),font=(text_font))],
        [sg.Button('Stop',size=(16,0),font=(but_font),key='leak_stop')],
        [sg.Text(' ',size=(12,2),font=(text_font))],
        [sg.Text('Countdown Timer: ',size=(16,0),font=(text_font)),sg.Text('', size=(6,0), justification = 'l', font=(text_font), background_color='gray', text_color='yellow',key='leak_countdown')],
        [sg.Text(' ',size=(1,1),font=(space_font))],
    ]

    layout_man_buttons = [

        [sg.Button('Start',size=(16,0),font=(text_font),key='man_start'),
        sg.Text('Push the Start Button to begin Manual Mode. The test will continue until stopped.', size=(40,2),font=(text_font))],
        [sg.Button('Stop',size=(16,0),font=(text_font),key='man_stop')],
        [sg.Text(' ',size=(12,5),font=(text_font))],

    ]

    layout_datetime = [

                [sg.Text("Current Date / Time:",size=(16,0), justification='r',font=(small_font)),sg.Text(dt.strftime("%m/%d/%Y %H:%M"),size=(14,0), justification='r',font=(small_font),text_color="snow",key='curr_date'),
                sg.Text("Change to:",size=(10,0), justification='r',font=(small_font),key='change_date'),sg.InputText(size=(16,1),font=(small_font),key='date_text')],

        [sg.Column(
            [
                [sg.Button('1',size=(5,0),key='1B',font=(pad_font)), sg.Button('2',size=(5,0),key='2B',font=(pad_font)), sg.Button('3',size=(5,0),key='3B',font=(pad_font)),sg.Button('/',size=(5,0),key='/B',font=(pad_font))],
                [sg.Button('4',size=(5,0),key='4B',font=(pad_font)), sg.Button('5',size=(5,0),key='5B',font=(pad_font)), sg.Button('6',size=(5,0),key='6B',font=(pad_font)),sg.Button(':',size=(5,0),key=':B',font=(pad_font))],
                [sg.Button('7',size=(5,0),key='7B',font=(pad_font)), sg.Button('8',size=(5,0),key='8B',font=(pad_font)), sg.Button('9',size=(5,0),key='9B',font=(pad_font)),sg.Button('Space',size=(5,0),key=' B',font=(pad_font))],
                [sg.Button('Enter',size=(5,0),key='xyz',font=(pad_font)),sg.Button('0',size=(5,0),key='0B',font=(pad_font)),sg.Button('Clear',size=(5,0),key='ClrB',font=(pad_font)),sg.Button('⌫', key='backB', size=(5, 0), font=(pad_font))],
                
            ],element_justification='c',justification='c')
        ]


        #[sg.Text('', size=(18,1),font=(text_font)),sg.Button('Change Date',size=(16,0),font=(text_font),key='xyz')],
        #[sg.Text('', size=(1,2),font=(text_font))],


    ]

    xs = 24

    cols_head_l =[  
            [sg.Text(head_left,size=(xs,0), justification='c',font=(date_font),key='head_left')],
            [sg.Button(dt.strftime("%m/%d/%Y %H:%M"),size=(14,1),font=date_font,key='datetime')],
            [sg.Text('Ver: '+version +' / '+ profile+'A', size=(xs,0), justification='c', font=(lock_font), key='version')]
    ]

    cols_head_c =[ 
            [sg.Text('VST ',size=(xs,0), justification='c',font=(heading_font))],  
            [sg.Text(screen_name, size=(xs,0), justification='c',key='SCREENNAME',font=(text_font))],
    ]

    cols_head_r =[ 
            [sg.Image(size=(100,50),key='-IMAGE-')],
            [sg.Text(head_right,size=(xs,0), justification='c',font=(lock_font),key='head_right')], 
            
    ]

    ### sg.Text(dt.strftime("%m/%d/%Y %H:%M"),size=(xs,0),font=space_font,key='datetime',enable_events=True),

    layout_head = [

        [sg.Column(cols_head_l, size=(200,80),element_justification='c',justification='c'),
        sg.Column(cols_head_c, size=(400,80),element_justification='c',justification='c'),
        sg.Column(cols_head_r, size=(200,80),element_justification='c',justification='c')],
        [sg.HorizontalSeparator(color='white')],[sg.Text(" ",size=(1,1))],

    ]

    if locked is True:
        lock_str = 'LOCKED'
    else:
        lock_str = 'UNLOCKED'


    cols_foot = [

        [sg.Text("",size=(32,0),font=(space_font),key='status'),
            sg.Button('Back',font=(but_font)),
            sg.Button('Home',font=(but_font)),
            sg.Text(lock_str,justification='r',size=(32,0),key='lock_status')],
    ]

    ###  sg.Text('S/N: '+serial,justification='r',size=(20,0))]

    layout_foot = [

        [sg.HorizontalSeparator(color='white')],
        [sg.Column(cols_foot, size=(cont['scr_width'],120), justification='c')]
        
    ]


    layout = [

            [sg.Column(layout_head, visible=False, key='head')],

            [
                
                sg.Column(layout_main, visible=False, key='a'),
                sg.Column(layout_alarms, visible=False, key='b'), 
                sg.Column(layout_maint, visible=False, key='c'),
                sg.Column(layout_manual, visible=False, key='d'),
                sg.Column(layout_test, visible=False, key='e'),
                sg.Column(layout_leak, visible=False, key='f'),
                sg.Column(layout_func, visible=False, key='g'),
                sg.Column(layout_pass, visible=False, key='h'),
                sg.Column(layout_startup, visible=False, key='i'),
                sg.Column(layout_code, visible=False, key='j'),
                sg.Column(layout_overfill, visible=False, key='k'),
                sg.Column(layout_about, visible=False, key='l'),
                sg.Column(layout_profiles, visible=False, key='m'),
                sg.Column(layout_man_buttons, visible=False, key='n'),
                sg.Column(layout_datetime, visible=False, key='o'),
                sg.Column(layout_shutdown, visible=False, key='p'),
                sg.Column(layout_runcycle, visible=False, key='r'),
                sg.Column(layout_shutdown2, visible=False, key='q'),
                sg.Column(layout_eff, visible=False, key='s'),
            
            ],
            
            [sg.Column(layout_foot, visible=False, key='foot')] 
            
            ],

    print(f"Screen Width={cont['scr_width']}")



    window = sg.Window('Main Window',layout,location=(5000,5000),

        background_color=sg.theme_background_color(),
        size=(cont['scr_width'],
        cont['scr_height']),
        element_justification='c', 
        titlebar_background_color = 'blue',
        titlebar_text_color = 'blue', 
        keep_on_top=False, finalize=True)     

    #window.move(0,0)
    window.maximize()
    
    
    set_screen('a')

    ### Setup pascode window in advance

    layout_passcode_inner = [[sg.Text(' ',font=(space_font),size=(1,3))],
           [sg.Text('Enter Your Passcode',font=(text_font),justification='c',size=(22,1))],
              [sg.Column(

                [[sg.Input(size=(6, 1), font=(display_font),justification='center', key='input')]],justification='c',

              )]
              ,
              [sg.Button('1',size=(5,0),font=(but_font)), sg.Button('2',size=(5,0),font=(but_font)), sg.Button('3',size=(5,0),font=(but_font))],
              [sg.Button('4',size=(5,0),font=(but_font)), sg.Button('5',size=(5,0),font=(but_font)), sg.Button('6',size=(5,0),font=(but_font))],
              [sg.Button('7',size=(5,0),font=(but_font)), sg.Button('8',size=(5,0),font=(but_font)), sg.Button('9',size=(5,0),font=(but_font))],
              [sg.Button('Enter',size=(5,0),font=(but_font),key='Submit'), sg.Button('0',size=(5,0),font=(but_font)), sg.Button('⌫', key='key_back', size=(5, 0), font=(but_font))],
              #[sg.Button('Clear',size=(5,0),font=(but_font),key='Clear')],
              [sg.Text(size=(15, 1), font=('Helvetica', 18), text_color='red', key='out')],
              ]

    layout_passcode =[
        [sg.Column(layout_passcode_inner, visible=False, key='passcode_inner')],  
    ]


    window_pass = sg.Window('Keypad',layout_passcode,location=(5000,5000),
            size=(cont['scr_width'],
            cont['scr_height']),
            element_justification='c', 
            titlebar_background_color = 'blue',
            titlebar_text_color = 'blue', 
            keep_on_top=False, finalize=True)
            
            ####.Finalize()

    window_pass.move(0,-20)
    window_pass.maximize()

    #window_pass.make_modal()

    logo = ImageTk.PhotoImage(image=im)

    # update image in sg.Image
    window['-IMAGE-'].update(data=logo)


    window_pass.hide()
    
    ##### End of setting up passcode window

    ### Disapear the mouse cursor

    window.TKroot["cursor"] = "none"   ### Hide the mouse cursor - from github
    window.set_cursor('None')
    # window_pass.TKroot["cursor"] = "none"   ### Hide the mouse cursor - from github
    # window_pass.set_cursor('None')
    
    graph = window['graph']
    
    relays = {}

    relays[0] = graph.draw_circle((100,60),30, fill_color='gray',line_color='white')
    relays[1] = graph.draw_circle((200,60),30, fill_color='gray',line_color='white')
    relays[2] = graph.draw_circle((300,60),30, fill_color='gray',line_color='white')
    relays[3] = graph.draw_circle((400,60),30, fill_color='gray',line_color='white')


    relay1 = graph.draw_circle((100,60),30, fill_color='gray',line_color='white')
    relay2 = graph.draw_circle((200,60),30, fill_color='gray',line_color='white')
    relay3 = graph.draw_circle((300,60),30, fill_color='gray',line_color='white')
    relay4 = graph.draw_circle((400,60),30, fill_color='gray',line_color='white')
    modem = graph.draw_rectangle((450,30),(550,80), fill_color='gray',line_color='white')   

    rLabel1 = graph.DrawText('Motor',location=(100,10),color='gray',font=text_font,text_location='center')
    rLabel2 = graph.DrawText('V1',location=(200,10),color='gray',font=text_font,text_location='center')
    rLabel3 = graph.DrawText('V2',location=(300,10),color='gray',font=text_font,text_location='center') 
    rLabel4 = graph.DrawText('V5',location=(400,10),color='gray',font=text_font,text_location='center')
    mLabel =  graph.DrawText('Modem',location=(500,10),color='gray',font=text_font,text_location='center')     


    event_loop = time.time()

    while True:

        window[f'SCREENNAME'].update(screen_name)
        event, values = window.read(timeout=FAST_TIME_THRESHOLD)

        window['eff_time'].update(accum_time)

        alarms2= json.loads(rconn.get("alarms"))
        alarms['sd_card_alarm'] = alarms2['sd_card_alarm']



        if event != "__TIMEOUT__":
            print(f"----------------------------------------")
            print(f"- Event={event}, Screen={screen_name}")
            print(f"----------------------------------------")

            

        #print (f'In Event Loop:: Runcycle: {run_cyc}, Run Mode: {run_mode},run_step: {run_step}, Event: {event}, Screen: {screen_name}')

        if event in (None, 'Exit'):
            break

        if event == "Manual Purge":
        
            manual_purge_button()

        if event == "Silence":

            #chirp()
            window['sb'].update(visible=False)
            alarms['buzzer_silenced'] = True

        ##  Track where the users goes when the 'Back' Button is pressed 

        if event == 'Back':

            run_timer = 0

            if screen_name == 'Functionality Test Screen':
                event = 'Run Tests'
                run_cyc = False
                run_step = 0
                set_mode(0)
                set_relays(0)

            elif screen_name == 'Run Cycle Parameters Screen':
                event = 'Startup Screen'
                startup_bypass = True
                run_cyc = False
                run_step = 0
                set_mode(0)
                set_relays(0)

            elif screen_name == 'Leak Test Screen':
                event = 'Run Tests'
                run_cyc = False
                run_step = 0
                set_mode(0)
                set_relays(0)

            elif screen_name == 'Efficiency Test Screen':
                event = 'Run Tests'
                run_cyc = False
                eff_test_timer = timer()
                run_step = 0
                set_mode(0)
                set_relays(0)

            elif screen_name == 'Test Screen':
                bypass = True
                event = 'Maintenance'

            elif screen_name == 'Startup Screen':
                bypass = True
                event = 'Maintenance'

            elif screen_name == 'Startup Code Entry':
                startup_bypass = True
                event = 'Startup Screen'

            elif screen_name == 'Passcode Entry':
                bypass = True
                event = 'Main'

            elif screen_name == 'Change Date & Time':
                bypass = True
                event = 'Main'


            elif screen_name == 'Startup Screen':
                bypass = True
                event = 'Maintenance'

            elif screen_name == 'Overfill Override Screen':
                startup_bypass = True
                event = 'Startup Screen'

            elif screen_name == 'Profiles Screen':
                startup_bypass = True
                event = 'Startup Screen'
            
            elif screen_name == 'About Screen':
                startup_bypass = True
                event = 'Startup Screen'

            elif screen_name == 'Manual Screen':
                startup_bypass = True
                event = 'Startup Screen'
                continuous_mode = False
                run_cyc = False

                ##  Added per Doug 20210706

                run_step = 0
                set_mode(0)
                set_relays(0)
            

            elif screen_name == 'Maintenance Screen':
                event = 'Main'

            elif screen_name == 'Alarm Screen':
                event = 'Main'   

            ###  End of Event = Back

        if event == 'Main' or event == 'Home':

            if screen_name != "Alarm Screen":

                ## If you exit or return and you are coming FROM the Manual Screen
                cont['maintenance_mode'] = False

                continuous_mode = False
                run_cyc = False
                run_mode = 'run'
                run_step = 0
                run_timer = 0

                set_mode(0)
                set_relays(0)
    

            screen_name="Main Screen"
            run_mode = 'run'
            bypass = False

            set_screen('a')


        if event == 'datetime':
            ### Change the date and time
            screen_name="Change Date & Time"
            set_screen('o')

        if event == "Test":
            screen_name = "Run Cycle Parameters Screen"
            set_screen('r')

        if event == 'Faults & Alarms':
            screen_name="Alarm Screen"
            run_mode='run'

            set_screen('b')

        if event == 'pass':
            screen_name = 'passcode'

            set_screen('h')

        if event == 'Debug On':
            os.system("/home/pi/python/debug_on")
            python = sys.executable
            os.execl(python, python, * sys.argv)

        if event == 'Debug Off':
            os.system("/home/pi/python/debug_off")
            python = sys.executable
            os.execl(python, python, * sys.argv)
        
        if event == 'Lock':
            cont['startup'] = '000000'
            locked = True
            lock_str = 'LOCKED'
            save_startup_code(cont['startup'])
            window['lock_status'].update(lock_str)

        if screen_name == 'Passcode Entry':
            ## Events specifically for passcode keypad
            if event == 'key_back':
                keys_entered = values['input']
                keys_returned = keys_entered[:-1]
                window['input'].update(keys_returned)
                beep()

            elif event == 'Clr':
                keys_entered = ''
                window['input'].update('')

            elif event in '1234567890':
                keys_entered = values['input']
                keys_entered += event

                window['input'].update(keys_entered)

            elif event == 'Sub':
                keys_entered = values['input']
                code = keys_entered

                if code == maint_code:
                    event = 'Maintenance'
                else: 

                    ### Invalid Code

                    code = ''
                    keys_entered = ''
                    window['input'].update('INVALID')

        if screen_name == "Change Date & Time":

            dt = datetime.now(tz=tz_mexico)

            window['datetime'].update(dt.strftime("%m/%d/%Y %H:%M"))
            window['curr_date'].update(dt.strftime("%m/%d/%Y %H:%M"))

            #window.read(timeout=1)

            if 'keys_entered' not in locals():
                keys_entered = ''

            if event == 'ClrB':
                keys_entered = ''
                window['date_text'].update('')
                chirp()

            elif event == 'backB':
                keys_entered = values['date_text']
                keys_returned = keys_entered[:-1]
                window['date_text'].update(keys_returned)
                chirp()

            elif event in ['1B','2B','3B','4B','5B','6B','7B','8B','9B','0B','/B',':B',' B']:
                if len(keys_entered) == 2 or (len(keys_entered) == 5):
                    keys_entered = values['date_text']
                    keys_entered += "/"
                    keys_entered += event[0]
                elif len(keys_entered) == 10:
                    keys_entered = values['date_text']
                    keys_entered += " "
                    keys_entered += event[0]
                elif len(keys_entered) == 13:
                    keys_entered = values['date_text']
                    keys_entered += ":"
                    keys_entered += event[0]
                else:
                    keys_entered = values['date_text']
                    keys_entered += event[0]

                window['date_text'].update(keys_entered)
                chirp()

            elif event == 'xyz':
                dt_string = values['date_text']

                try:
                    dt = datetime.strptime(dt_string, "%m/%d/%Y %H:%M")
                except:
                    print(f"Datetime: Invalid datetime: {dt_string}")
                    

                else:
                    print(f"Date and Time changed to: {dt_string}")
                    window['datetime'].update(dt.strftime("%m/%d/%Y %H:%M"))

                    set_screen('a')


        if screen_name == 'Startup Code Entry':
        
            ## Events specifically for startup code keypad

            if event == 'ClrA':
                keys_entered = ''
                window['inputA'].update('')

            elif event in ['1A','2A','3A','4A','5A','6A','7A','8A','9A','0A','AA','BA','CA','DA','EA','FA']:
                keys_entered = values['inputA']
                keys_entered += event[0]

                window['inputA'].update(keys_entered)

            elif event == 'SubB':
                keys_entered = values['inputA']
                code = keys_entered

                last_sn =  serial[-6:]

                print(f'Code: {code}  Last S/N: {last_sn}')

                if ((code == last_sn) or (code == vst_code2)):


                    ### 
                    ### This is the routine that makes everything asll right 
                    ### and allows regular operation
                    ###

                    event = 'Maintenance'
                    bypass = True
                    startup_bypass = True
                    locked = False
                    cont['startup'] = code
                    save_startup_code(cont['startup'])
                    lock_str = 'UNLOCKED'

                else: 

                    code = ''
                    keys_entered = ''
                    window['inputA'].update('INVALID')

            
        if event == 'Maintenance':

            #cont['maintenance_mode'] = True

            startup_bypass = False
            #all_stop()


            if bypass == True:

                screen_name="Maintenance Screen"
                cont['maintenance_mode'] = True
                all_stop()

                set_screen('c')

            else:
                 
                code = passcode()
                
                if code == maint_code or bypass == True:

                    screen_name="Maintenance Screen"
                    cont['maintenance_mode'] = True
                    all_stop()
                    set_screen('c')

            code = ''
            keys_entered = ''
            window['input'].update('')

        ### END if event == 'Maintenance':


        if event == 'Manual Mode':

            screen_name="Manual Screen"

            set_screen('d')

        if event == 'man_start':

            

            run_cyc = True
            continuous_mode = True
            run_step = 0

            screen_name="Manual Screen"
            run_mode = 'man'

            print (f'In Manual Start, Runcycle: {run_cyc}, Run Mode: {run_mode},run_step: {run_step}, Event: {event}, Screen: {screen_name}')

            #set_screen('d')

        if event == 'Run Tests':
            screen_name="Test Screen"

            set_screen('e')


        if event == 'Leak Test':
            run_mode = 'leak'
            
            screen_name="Leak Test Screen"

            leak_test_timer = timer()
            window['leak_countdown'].update(str(round(MIN30 - (timer() - leak_test_timer))))

            set_screen('f')


        if event == 'Functionality Test':
            run_mode = 'func'
            screen_name="Functionality Test Screen"

            set_screen('g')
    

        if event == 'Efficiency Test':

            run_mode = 'eff'
            screen_name="Efficiency Test Screen"

            eff_test_timer = timer()

            window['eff_mode'].update(cont['mode'])
            window['eff_step'].update(run_step)

            window['eff_time'].update(accum_time)


            #window['eff_countdown'].update(str(round(MIN30 - (timer() - eff_test_timer))))

            set_screen('s')


        if event == 'Run Cycle Parameters':
            run_mode = 'test'
            all_stop()
            screen_name = 'Run Cycle Parameters Screen'

            set_screen('r')

        if event == 'Startup Screen':

            if startup_bypass == True:

                 screen_name="Startup Screen"
                 all_stop()
                 #run_mode = 'maint'
                 set_screen('i')

            else:
                code = passcode()

            if (code == startup_code) or (code == vst_code):

                screen_name="Startup Screen"
                all_stop()
                #run_mode = 'maint'
                set_screen('i')


        if event == 'Start Up Code':
            all_stop()
            #run_mode = 'maint'
            screen_name="Startup Code Entry"

            set_screen('j')

 
        if event == 'Overfill Override':

            all_stop()
            #run_mode = 'maint'
            screen_name="Overfill Override Screen"

            set_screen('k')

        if event == 'confirm_overfill_override':

            ###  If the Confirm Overfill Override button was pressed

            was_active = False
            alarms['overfill_alarm'] = False
            alarms['overfill_alarm_time'] = 0
            alarms['tls_buzzer_triggered'] = False

            #alarms['critical_alarm_time'] = 0
            #alarms['overfill_alarm_override_time'] = time.time()

        if event == 'Profiles':


            all_stop()
            os.system('python3 /home/pi/python/name_change_app.py')
            
            #run_mode = 'maint'
            # screen_name="Profiles Screen"

            # set_screen('m')

        if event == 'About':

            #all_stop()
            #run_mode = 'maint'
            screen_name='About Screen'

            set_screen('l')

        if screen_name == "Profiles Screen":

            if event =='CS2':
                profile = 'CS2'
                save_profile(profile)
                #save_controller(cont)
                time.sleep(1)
                event = 'Restart'

            elif event =='CS12':
                profile = 'CS12'
                #save_controller(cont)
                save_profile(profile)
                time.sleep(1)
                event = 'Restart'               
    
            elif event =='CS8':
                profile = 'CS8'
                #save_controller(cont)
                save_profile(profile)
                time.sleep(1)
                event = 'Restart'

            elif event =='CS9':
                profile = 'CS9'
                #save_controller(cont)
                save_profile(profile)
                time.sleep(1)
                event = 'Restart'

            elif event =='CS3':
                profile = 'CS3'
                #save_controller(cont)
                save_profile(profile)
                time.sleep(1)
                event = 'Restart'

            

            if event =='Restart':
                python = sys.executable
                os.execl(python, python, * sys.argv)
                
            window['version'].update('Ver: '+version +' / '+ profile+'A')


        if event == 'clear_press':
            clear_pressure_alarms()
            print(f'Clearing Pressure Alarms')

        if event == 'Clear Motor Alarm':
            clear_motor_alarm(alarms)

        if event == 'Overfill Override':
            clear_overfill_alarm()

        ## Buttons being called from Functionality test Screen

        if event == 'func_start':
            run_mode = 'func'
            run_cyc = True
            run_step = 0

        if event == 'func_stop':
            run_cyc = False
            run_step = 0
            run_timer = 0
            set_mode(0)
            set_relays(0)


        ## Buttons being called from Efficency test Screen

        if event == 'eff_start':
            run_mode = 'eff'
            run_cyc = True
            run_step = 0
            run_timer = 0
            #run_timer = timer()
            eff_test_timer = timer()

        if event == 'eff_stop':
            run_cyc = False
            run_step = 0
            run_timer = 0

            set_mode(0)
            set_relays(0)

        ## Buttons being called from Leak test Screen

        if event == 'leak_start':
            run_mode = 'leak'
            run_cyc = True
            run_step = 0
            run_timer = 0
            #run_timer = timer()
            leak_test_timer = timer()

        if event == 'leak_stop':
            run_cyc = False
            run_step = 0
            run_timer = 0

            set_mode(0)
            set_relays(0)

       ## Buttons being called from Manual test Screen

        if event == 'man_start':

            run_cyc = True
            continuous_mode = True

            screen_name="Manual Screen"
            run_mode = 'man'
            run_step = 0

            #leak_test_timer = timer()

        if event == 'man_stop':
            run_cyc = False
            run_step = 0
            run_timer = 0
            set_mode(0)
            set_relays(0)


        if event == 'Calibrate':
            cont['adc_zero'] = cont['adc_value']

            print(f'Controller ADC Calibration Zero: {cont["adc_zero"]}')
            

        if screen_name=="Shutdown Screen":

            pass

            ###!!!
            ###
            ###  The problem is that the shutodown tine is being calculated in this
            ###  Window only.  If the user leaves this window, the countdown will stop
            ###``

            # shutdown_time = HOURS72-(time.time()-alarms['alarms_shutdown_alarm'])

            # xhours, xseconds = divmod(shutdown_time * 60, 3600)  # split to hours and seconds
            # xminutes, xseconds = divmod(xseconds, 60)  # split the seconds to minutes and seconds
            # result = "{:02.0f}:{:02.0f}:{:02.0f}".format(xhours, xminutes, xseconds)

            #window['shutdown_countdown'].update(result)

        if event == 'shutdown_ack' or event == 'shutdown_ack2':
            alarms['shutdown_ack_time'] = timer()
            logging.info('Shutdown Acknowledgement Given')

            sg.theme('DarkBlue 15')

            ### Go back to home screen

            screen_name="Main Screen"
            set_screen('a')

            if DEBUGGING:
                print('Shutdown Acknowledgement Given')
        
        ###  Turn Test mode on and off from test mode screen

        if event == 'Test Mode Off':
            test_mode_off()


        if event == 'Test Mode On':
            test_mode_on()


        if event == 'test_mode_reset':
            test_mode_reset()


        if event == 'up1':
            test_mode_up1()


        if event == 'dn1':
            test_mode_dn1()


        if event == 'up2':
            test_mode_up2()


        if event == 'dn2':
            test_mode_dn2()


        if event == 'up3':
            test_mode_up3()


        if event == 'dn3':
            test_mode_dn3()


        if event == 'up4':
            test_mode_up4()


        if event == 'dn4':
            test_mode_dn4()

        ### Everything else that needs to be kept track of that isnt a specific "thing"

        if event == '__TIMEOUT__':

            #print(f"Event Timing: {time.time() - event_loop}")

            #event_loop = time.time()


            if DEBUGGING:
                #print(f'Scan Time: {round(timer() - scan_time,2)} sec')
                head_right = f"DEBUG MODE"

            scan_time = timer()

            # Get updates as fast as 10ms

            fast_updates()
        
            if (timer() - one_sec_timer) > SHORT_TIME_THRESHOLD:

                ### One Second Updates
                ### This timer is for screen updates
                
                one_sec_updates()
                  
                if reboot_time !=0:
                    head_right = f"System Reboot:{reboot_time}"
                else:

                    if cont['test_mode']:
                        modem_status = "TEST MODE" 
                    else:
                        modem_status = f"{cont['access_tech']}/{cont['power_state']}/{cont['modem_state']}/{cont['signal_quality']}"


                    if not DEBUGGING:
                        head_right = modem_status

                ### Only display critical alarm cascade if profile = CS8

                if locked is True:

                    ### If Green Machine is lcoked out

                    window['main_status'].update('GREEN MACHINE DISABLED: ENTER CODE')
                    window['main_status'].update(background_color='red')

                else:

                    ### If Green Machine is NOT locked out

                    if profile == 'CS8' or profile == 'CS12':

                        if alarms['shutdown_alarm_time'] > 0:

                            ###  We are in alarm

                            shutdown_time = (time.time()-alarms['shutdown_alarm_time'])

                            ###  Get correct hours, minutes and seconds to display shutdown timer.

                            print(f'Shutdown Timer: {round(shutdown_time,0)} seconds')    

                            xhours, xseconds = divmod(HOURS72-shutdown_time, 3600)  # split to hours and seconds
                            xminutes, xseconds = divmod(xseconds, 60)  # split the seconds to minutes and seconds
                            result = "{:02.0f}:{:02.0f}:{:02.0f}".format(xhours, xminutes, xseconds)

                            ###  Put correct Hours, Minutes and Seconds on Countdown screen

                            window['shutdown_countdown'].update(result)

                            if (shutdown_time > HOURS72):

                                ###  SYSTEM SHUTDOWN

                                sg.theme('Reds')
                                
                                sg.theme_background_color('#FF0000')

                                window['main_status'].update('SYSTEM SHUTDOWN')
                                window['main_status'].update(background_color='red')

                                # window['sb'].update(visible=True)              
                                # window.read(timeout=1)

                                #window.read()

                                ### TURN OFF DISPENSERS
                                dispenser_shutdown.value = False
                                logit("error","Critical Error - Dispenser Shutdown")

                                #mcp.get_pin(4).value = True
                                
                                ### !!! VERIFY DISPENSER RELAY NORMALLY OPEN / CLOSE

                                print(f"SHUTDONW ALARM #4 - Station HAS SHUT DOWN!")

                                if not alarms['buzzer_silenced']:
                                    beep()

                                if (alarms['shutdown_stage'] != 4):

                                    #beep()

                                    alarms['buzzer_silenced'] = False
                                    window['sb'].update(visible=True)

                                    window.read(timeout=1)

                                    alarms['shutdown_alarm'] = True
                                    alarms['shutdown_stage'] = 4

                                    set_screen('q')  ##  Final Shutdown screen

                            elif (shutdown_time >= HOURS24 and shutdown_time < HOURS36):   #### FIRST ALARM - SHUTDOWN STATION

                                window['main_status'].update('GREEN MACHINE ALARM')
                                window['main_status'].update(background_color='red')
                                

                                window.read(timeout=1)

                                #window.read()

                                print(f"SHUTDONW ALARM #1 - Station WILL SHUT DOWN!")
                                
                                if not alarms['buzzer_silenced']:
                                    beep()

                                if alarms['shutdown_stage'] != 1:
                                    
                                #     beep()
                                    
                                    alarms['buzzer_silenced'] = False
                                    window['sb'].update(visible=True)
                                    alarms['shutdown_stage'] = 1

                                    set_screen('p')  ##  First Shutdown screen
                                    screen_name = "Shutdown Screen"

                                    window.read(timeout=1)
                        
                            elif (shutdown_time >= HOURS36 and shutdown_time < HOURS47):

                                ###  Just moved from one level up

                                print(f"SHUTDONW ALARM #2 - Station WILL SHUT DOWN!")

                                window['main_status'].update('SHUTDOWN IMMINENT')
                                window['main_status'].update(background_color='red')

                                if not alarms['buzzer_silenced']:
                                    beep()

                                if (alarms['shutdown_stage'] != 2):

                                    #beep()

                                    alarms['buzzer_silenced'] = False
                                    window['sb'].update(visible=True)
                                    
                                    alarms['shutdown_stage'] = 2

                                    station_locked = False

                                    set_screen('p')  ## Shutdown Screen
                                    screen_name = "Shutdown Screen"

                                window.read(timeout=1)

                            ###
                            ### SHUTDOWN - THIRD STAGE
                            ###
                            
                            elif ((shutdown_time >= HOURS47) and (shutdown_time < HOURS72)):

                                if alarms['shutdown_time_60'] == 0:
                                    alarms['shutdown_time_60'] = time.time()
                                    shutdown_count = 0
                                
                                if (time.time() - alarms['shutdown_time_60']) >= MIN60:

                                    alarms['shutdown_time_60'] = 0
                                    
                                    print(f"24 Hour SHUTDONW ALARM  #{shutdown_count} - Station is going to SHUT DOWN!")

                                    shutdown_count = shutdown_count + 1

                                    window['main_status'].update('SHUTDOWN IMMINENT')
                                    window['main_status'].update(background_color='red')

                                    if not alarms['buzzer_silenced']:
                                        beep()

                                    if alarms['shutdown_stage'] != 3:

                                        #beep()

                                        alarms['buzzer_silenced'] = False
                                        window['sb'].update(visible=True)

                                        alarms['shutdown_stage'] = 3
                                        
                                        set_screen('q')  ## Shutdown Screen
                                        screen_name = "Shutdown Screen"

                                    window.read(timeout=1)

                            ###
                            ### Shutdown LESS than 24 Hours
                            ###

                            elif ((shutdown_time > 0) and (shutdown_time < HOURS24)):

                                if not alarms['buzzer_silenced']:
                                    window['sb'].update(visible=True)
                                    beep()
                                
                               

                                window['main_status'].update('GREEN MACHINE ALARM')
                                window['main_status'].update(background_color='red')

                        else:  #(shutdown_time == 0):

                            if any_other_alarm():
                                window['main_status'].update('GREEN MACHINE ALARM')
                                window['main_status'].update(background_color='red')

                            else:
                                if cont['mode']==0:
                                    window['main_status'].update('GREEN MACHINE IDLE')
                                    window['main_status'].update(background_color='green')

                                elif cont['mode'] > 0:
                                    window['main_status'].update('GREEN MACHINE RUN')
                                    window['main_status'].update(background_color='green')



                    else:

                        if any_other_alarm():
                            window['main_status'].update('GREEN MACHINE ALARM')
                            window['main_status'].update(background_color='red')

                        else:
                            if cont['mode']==0:
                                window['main_status'].update('GREEN MACHINE IDLE')
                                window['main_status'].update(background_color='green')

                            elif cont['mode'] > 0:
                                window['main_status'].update('GREEN MACHINE RUN')
                                window['main_status'].update(background_color='green')

                ### Update status items in the upper corners of the display

                window['head_left'].update(head_left)
                window['head_right'].update(head_right)

                if screen_name == 'Maintenance Screen' or screen_name == 'Startup Screen' or screen_name == 'Manual Screen' or screen_name == 'Functionality Test Screen':
                    window['lock_status'].update(lock_str)
                    window['status'].update('H: ' + str(cont['hydrocarbons']) + '%/C: '+str(cont['current'])+' A / P: ' +str(cont['pressure']) + ' IWC')
                else:
                    window['status'].update(' ')
                    window['lock_status'].update(' ')
                
                window['runcycles'].update(str(cont['runcycles']))
                window['press'].update(str(cont['pressure']))


                window['datetime'].update(dt.strftime("%m/%d/%Y %H:%M"))

                if screen_name == 'Alarm Screen':
                    alarm_updates()


                if screen_name == 'Manual Screen':
                    window['runcycles_man'].update(str(cont['runcycles']))
                    window['mode_man'].update(get_mode())

                if screen_name == 'Test Screen':
                    window['press_test'].update(str(cont['pressure']))

                if screen_name == 'Maintenance Screen':

                    window['press_maint'].update(str(cont['pressure']))

                if screen_name == 'Startup Screen':
                    window['press_startup'].update(str(cont['pressure']))

                if screen_name == 'Functionality Test Screen':

                    seq = int(float(run_step) /2)
                    window['func_countdown'].update(str(5 - seq))
                    
                if screen_name == 'Leak Test Screen' and run_cyc is True:
                    window['leak_countdown'].update(str(round(MIN30 - (timer() - leak_test_timer))))

                if screen_name == 'Efficiency Test Screen' and run_cyc is True:
                
                    window['eff_mode'].update(cont['mode'])
                    window['eff_step'].update(run_step)


                   #window['eff_countdown'].update(str(round(MIN30 - (timer() - eff_test_timer))))


                set_manual_mode_status(cont['mode'])

                one_sec_timer = timer() # Refresh One second Timer

                if screen_name == "Manual Screen":
                    graph.TKCanvas.itemconfig(modem,fill="gray")                
            

            #### 
            ####  FIFTEEN SECOND TIMER
            ####

            ### Changing 15 seconds to 5 seconds for Centerville.

            ###  No longer use 15 second timer with Soracom modem

    window.close()

# def is_dst(tz, datetime_to_check):
#     """Determine whether or not Daylight Savings Time (DST)
#     is currently in effect"""

#     # Jan 1 of this year, when all tz assumed to not be in dst
#     non_dst = datetime(year=datetime.now().year, month=1, day=1)
#     # Make time zone aware based on tz passed in
#     non_dst_tz_aware = pytz.timezone(tz).localize(non_dst)

#     # if DST is in effect, their offsets will be different
#     return not (non_dst_tz_aware.utcoffset() == datetime_to_check.utcoffset())

# def is_dst2(when):
#     '''Given the name of Timezone will attempt determine if that timezone is in Daylight Saving Time now (DST)'''
#     return when.dst() != timedelta(0)

if __name__ == '__main__':
 
    startup_beep()

    cont['serial'] = get_serial()

    modem = json.loads(rconn.get("modem"))

    #tz_mexico  = pytz.timezone('America/Mexico_City')

    tz_mexico = timezone(timedelta(hours=-5))
    # tz_EST = pytz.timezone('EST')

    # dt_mexico = datetime.now(tz=tz_mexico)
    # dt_EST = datetime.now(tz=tz_EST)

    dt = datetime.now(tz=tz_mexico)
    #dt = dt_mexico


    accum_time = 0

    cont['signal_quality'] = modem['modem']['generic']['signal-quality']['value']
    cont['access_tech'] = modem['modem']['generic']['access-technologies'][0]
    cont['power_state'] = modem['modem']['generic']['power-state']
    cont['modem_state'] = modem['modem']['generic']['state']
    cont['deviceID'] = modem['modem']['3gpp']['imei']
    
    #modem = json.loads(rconn.get("modem"))

    signal_quality = modem['modem']['generic']['signal-quality']['value']
    access_tech = modem['modem']['generic']['access-technologies'][0]
    power_state = modem['modem']['generic']['power-state']
    modem_state = modem['modem']['generic']['state']

    # cont = json.loads(rconn.get("cont"))
    # alarms = json.loads(rconn.get("alarms"))

    print(f'Access Tech: {access_tech}')
    print(f'Power State: {power_state}')
    print(f'State: {modem_state}')
    print(f'Signal Quality: {signal_quality}')

    profile = get_profile()

    save_controller(cont)
    
    #cont['runcycles'] = get_runcycles(cont)

    print(f"Runcycles now set to: {cont['runcycles']}.")

    set_relays(0)

    screens()

