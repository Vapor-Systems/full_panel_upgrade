import time
import pigpio
 
PIN = 27  # CPi-A/B/S
# PIN = 27  # CPi-C
 
pi = pigpio.pi()
 
# We actually can't achieve 2700Hz due to the sampling
# rate, but it will do the best it can
pi.set_PWM_frequency(PIN, 2700)
 
# 128/255 = 50% duty
pi.set_PWM_dutycycle(PIN, 128)
 
# play beep for 100 milliseconds
time.sleep(0.100)
 
#turn off beep
pi.set_PWM_dutycycle(PIN, 0)
 
pi.stop()