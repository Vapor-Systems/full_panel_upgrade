import board
import busio
from digitalio import Direction
from adafruit_mcp230xx.mcp23017 import MCP23017
i2c = busio.I2C(board.SCL, board.SDA)

import random
import logging
import time

logger = logging.getLogger("pylog")
logging.basicConfig(filename='/home/pi/python/i2c_test.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import sys

if len(sys.argv) > 1:
    option = sys.argv[1]
    #value = sys.argv[2] if len(sys.argv) > 2 else None

    #print(f"Option: {option}")
    #print(f"Value: {value}")
    
    run_count = int(option)
else:
    print("No command line options provided.")
    run_count = 1000
    
print(f'Runcount: {run_count}')




mcp = MCP23017(i2c)

###
### Setup pins on the Raspberry Pi
###

mcp.get_pin(0).direction = Direction.OUTPUT
mcp.get_pin(1).direction = Direction.OUTPUT
mcp.get_pin(2).direction = Direction.OUTPUT
mcp.get_pin(3).direction = Direction.OUTPUT

import Adafruit_ADS1x15
adc = Adafruit_ADS1x15.ADS1115()
GAIN = 1

### Fast Functionality  test runcycle template
run_cycle_template = [[1,20],[2,6],[1,6],[2,6],[1,6],[2,6],[1,6],[2,6],[1,6],[2,6]]


def mapit(x, in_min, in_max, out_min, out_max):
    
    ''' Function to map an input that works like the Arduino map() function '''

    return (x-in_min) * (out_max-out_min) / (in_max-in_min) + out_min



def get_current():
    
    c = d = 0

    try:    
        try:
            c = adc.read_adc(2, gain=GAIN)
        except:
            logging.error(f'!! Failed to read value from input 2')

        try:
            d = adc.read_adc(3, gain=GAIN)
        except:
            logging.error(f'!! Failed to read value from input 3')
    except:
        logging.error(f'!! Failed to read current')
    else:
        i = abs(c-d)
        current  = round(mapit(i,1248.0,4640.0,2.1,8.0),2)
        
        return current


def get_pressure():
    
    try:
        p = adc.read_adc(0, gain=GAIN)
    except:
        logging.error(f'!! Failed to read pressure')
        
    else:
        pressure = round(mapit(p, 15422,22864.0,0.0, 20.8),2)

        return pressure
    
    

def relay_on(r):

    logging.info(f'.... Relay {r} set to ON')

    try:
        mcp.get_pin(r).value = True
    except:
        logging.error(f'!! Relay {r} did NOT set to ON')
        
        try:
            r_value = mcp.get_pin(r).value
        except:
            logging.error(f'!! I2C Error reading pin: {r} after setting.')
        else:
            if r_value != True:
                logging.error(f'!! I2C Error setting pin: {r}')
                 
        # If there was a problem communicating with the relay, wait 1/10 of a second and try again
        #time.sleep(0.10)
        #relay_on(r)
 

def relay_off(r):

    logging.info(f'.... Relay {r} set to OFF')

    try:
        mcp.get_pin(r).value = False
    except:
        logging.error(f'!! Relay {r} did not set to OFF')
        
        try:
            r_value = mcp.get_pin(r).value
        except:
            logging.error(f'!! I2C Error reading pin: {r} after setting.')
        else:
            if r_value != True:
                logging.error(f'!! I2C Error setting pin: {r}')
        
        # If there was a problem communicating with the relay, wait 1/10 of a second and try again
        #time.sleep(0.10)
        #relay_off(r)


def set_relays(mode):

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
    
    
def fast_updates():

    c = get_current()
    logging.info(f'...... Reading Current: {c}')
    
    
    p = get_pressure()
    logging.info(f'...... Reading Pressure {p}')
    
   
def one_second_updates():

    mode = random.randint(0,3)
    
    logging.info(f'... Setting Relays to Mode: {mode}')
    set_relays(mode)
    
    
def main():

    one_second_timer = time.time()
    fast_timer = time.time()
    run = 0
    fast_step = 0 


    while run < run_count:	
    
        if (time.time() - one_second_timer) > 1:
        
            run += 1
            logging.info(f'## Run: {run}')
            one_second_updates()
            one_second_timer=time.time()
            
            fast_step = 0
            
            
        if (time.time() - fast_timer) > 0.01:
        
            fast_step += 1
            logging.info(f'.....Run: {run}, Step: {fast_step}')
            fast_updates()
            fast_timer=time.time()


if __name__== '__main__':
    set_relays(0)
    main()
    print(f'\nSetting All relays OFF\n')
    set_relays(0)


 
    
    

