
import requests,json
import multiprocessing
import redis
import json
import time
import pigpio

pi = pigpio.pi()

import logging
logger = logging.getLogger("pylog")
logging.basicConfig(filename='/home/pi/python/cp2.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import board
import busio
from digitalio import Direction
from adafruit_mcp230xx.mcp23017 import MCP23017
import Adafruit_ADS1x15



import PySimpleGUI as sg

screen_width = 800
screen_height = 480

sg.set_options(
    window_location=(0,0), 
    margins=(0,0),
    titlebar_background_color = 'blue',
    titlebar_text_color = 'blue',
)

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

class r:

    def __init__(self,location,stuff):
        pass

    def getf(name):
        new_float = float (rconn.get(name))
        return new_float

    def geti(name):
        new_int = int(rconn.get(name))
        return new_int

    def getb(name):
        b = rconn. get(name)
        if b == 'True':
            return True 
        else:
            return False
        
    def setb(value,state):
    
        if state:
            rconn.set(value,'True')
        else:
            rconn.set(value,'False')

def beep_SOS():
    beep()

def beep_long():
    beep()

def one_beep():
    beep()
    
def chirp():
    beep()

def buzzer(freq, dur):

    '''
    New Buzzer function that replays on multiprocessing and that new buzzer in the Comfile
    '''

    pi.set_PWM_frequency(30, freq)
    pi.set_PWM_dutycycle(30,128)
    time.sleep(dur)
    pi.set_PWM_dutycycle(30,0)
    
    pi.stop()
    
    
def beep():

    BUZZER = json.loads(rconn.get("buzzer"))
    profile = rconn.get("profile")

    if BUZZER and (profile == 'CS8' or profile == 'CS12') :
        
        freq = 880
        dur = 0.5
        
        buzz = multiprocessing.Process(target=buzzer,args=(freq,dur, ))
        buzz.start()

def startup_beep():
                    
    freq = 880 
    dur = 0.5
    
    buzz = multiprocessing.Process(target=buzzer,args=(freq,dur, ))
    buzz.start()
    


def get_float (name):
    new_float = float (rconn.get (name))
    return new_float

def get_int (name):
    new_int = int(rconn.get (name))
    return new_int

def get_bool (name):
    b = rconn. get (name)
    if b == 'True':
        return True 
    else:
        return False


def set_bool(value,state):
    
    if state:
        rconn.set(value,'True')
    else:
        rconn.set(value,'False')      

def get_secrets():

    try:
        with open('secrets.json', 'r') as secrets_file:
            secrets = json.load(secrets_file)

    except FileNotFoundError:
        secrets = {"DEBUGGING" : "False", "DEVICE_NAME" : "RND-0001", "BUILD" : "100.127", "VERSION" : "CSX-002G" }


    return secrets


def get_auth():

    headers = {'Content-type': 'application/json'}

    data = {'email': 'admin@vsthose.com','password': 'B4ustart!'}

    response = requests.post('https://g.api.soracom.io/v1/auth',headers=headers,json=data)

    data = json.loads(response.text)
    api_key = data['apiKey']
    token = data['token']

    # print(response.text)

    return api_key, token


def get_runcycles():

    try:
        fob = open("mcu.obj","rb")

    except: 

        logit("error","Error reading mcu.obj.  Runcycle Count failed to load.")
        cont['runcycles'] = 0

    else:
        cont['runcycles'] = pickle.load(fob)  ## "cont" is the controller object
        fob.close()


def mapit(x, in_min, in_max, out_min, out_max):
    
    ''' Function to map an input that works like the Arduino map() function '''
    
    return (x-in_min) * (out_max-out_min) / (in_max-in_min) + out_min


def detect_model():
    with open('/proc/cpuinfo', 'r') as f:
        content = f.read()

    if 'Compute Module 4' in content:
        return 'cm4'
    else:
        return 'cm3'


def get_serial():

    # Extract serial from cpuinfo file
    
    cpuserial = "0000000000000000"

    try:
        
        f = open('/proc/cpuinfo','r')
        
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[18:26]
        f.close()

    except:
        
        cpuserial = "ERROR000000000"
    
    return cpuserial.upper()


def check_i2c_error():

    i2c_failure = True
    mcp_failure = True
    error_msg = ""

    try:
        i2c = busio.I2C(board.SCL, board.SDA)
    except:
        #  I2C Failure
        i2c_failure = True
        logging.error("FAILURE: i2c Bus")
        error_msg = "0x0001"
    else:
        i2c_failure = False
        
        try:
            mcp = MCP23017(i2c)
        except:
            mcp_failure = True
            logging.error("FAILURE: MCP Chip")
            error_msg += " 0x0002"
        else:
            mcp_failure = False
            #break
            
    #### Abruptly stop the program and issue an alarm

    if i2c_failure or mcp_failure:

        sg.theme('DarkBlue 15')

        layout_error = [

            [sg.Text(' ',size=(1,2),font=('Piboto 32 bold'))],
            [sg.Text('ERROR: I2C Alarm!' , size=(32,1), justification = 'c', font=('Piboto 32 bold'), text_color='yellow')],
            [sg.Push(),sg.Text('Call VST Field Support - Error Code:' + error_msg, size=(60,1), justification = 'c', font=('Piboto 24'), text_color='white'),sg.Push()],
            [sg.Text(' ',size=(1,2),font=('Piboto 32 bold'))],
        ]

        layout = [
            [sg.Frame('',layout_error, visible=True,border_width=0, key='error', background_color='#151680')],
        ]

        window = sg.Window('Error Window',layout,location=(0,0),
            background_color=sg.theme_background_color(),
            size=(screen_width,screen_height),
            element_justification='c', 
            titlebar_background_color = 'blue',
            titlebar_text_color = 'blue', 
            keep_on_top=False, finalize=True)     

        window.maximize()
        
        while True:
            print(f"i2c Error:{i2c_failure}, MCP Error:{mcp_failure}")
            time.sleep(1)

    else:
        return i2c, mcp
    

def reset_i2c():

    
    global i2c
    global mcp
    global adc
    global dispenser_shutdown
    global tls_relay
    global panel_power

    ### RESTART PROGRAM PROGRAM

    logging.error("*** Resetting I2C Controller because of continued I2C Errors")
    # os.system("sudo systemctl restart control")

    try:
        i2c = busio.I2C(board.SCL, board.SDA)
    except:
        reset_i2c()
        
    try:    
        mcp = MCP23017(i2c)
        adc = Adafruit_ADS1x15.ADS1115()
    except:
        reset_i2c()    
        
    try:
        mcp.get_pin(0).direction = Direction.OUTPUT
        mcp.get_pin(1).direction = Direction.OUTPUT
        mcp.get_pin(2).direction = Direction.OUTPUT
        mcp.get_pin(3).direction = Direction.OUTPUT
        mcp.get_pin(7).direction = Direction.OUTPUT
        mcp.get_pin(14).direction = Direction.OUTPUT

        dispenser_shutdown = mcp.get_pin(4)
        tls_relay = mcp.get_pin(8)
        panel_power = mcp.get_pin(10)

        tls_relay.direction = Direction.INPUT
        panel_power.direction = Direction.INPUT
        dispenser_shutdown.direction = Direction.OUTPUT
        dispenser_shutdown.value = True
    except:
        reset_i2c()


if __name__ == '__main__':
    pass
