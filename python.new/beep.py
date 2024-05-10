'''
BEEP.PY
'''

import pigpio
import time
import multiprocessing

BUZZER_PIN = 0

pi = pigpio.pi()


def buzzer(pin, freq, dur):

    pi.set_PWM_frequency(pin, freq)
    pi.set_PWM_dutycycle(pin,128)
    time.sleep(dur)
    pi.set_PWM_dutycycle(pin,0)
    
    pi.stop()
    
    
def beep(pin):
    freq = 880
    dur = 0.5
    
    buzz = multiprocessing.Process(target=buzzer,args=(pin,freq,dur, ))
    buzz.start()


def detect_model():
    with open('/proc/cpuinfo', 'r') as f:
        content = f.read()

    if 'Compute Module 4' in content:
        return 'cm4'
    else:
        return 'cm3'


def main():
    cpu_model = detect_model()

    if cpu_model == "cm4":
        BUZZER_PIN=27 ## CM4
    else:
        BUZZER_PIN=30 ## CM3

    i=0

    while True:
        print(f"Buzer Pin:  {BUZZER_PIN}")
        beep(BUZZER_PIN)
        print(f"Beep: # {i}")
        i+=1
        time.sleep(1.0)


if __name__ == '__main__':
    
    main()
