import redis
import subprocess
import json

r = redis.Redis('localhost', decode_responses=True)

# digit_variables = [
#     'overfill_alarm_alert_time',
#     'overfill_alarm_time',
#     'critical_alarm_time',
#     'current',
#     'curr_counter',
#     'run_timer',
#     'test_start_timer',
#     'special_run_count',
#     'zero_pressure_start',
#     'low_pressure_start',
#     'var_pressure_start',
#     'high_pressure_start',
#     'var_pressure',
#     'shutdown_alarm_time',
#     'runcycles',
#     'mode',
#     'pressure',
#     'adc_value',
#     'kickstart_timer'
# ]

# bool_variables = [
#     'buzzer',
#     'profile',
#     'overfill_alarm',
#     'was_active',
#     'tls_buzzer_triggered',
#     'vac_pump_alarm',
#     'press_sensor_alarm',
#     'run_cyc',
#     'run_mode',
#     'vac_pump_alarm_checked',
#     'manual_burp_mode',
#     'manual_purge_mode',
#     'zero_pressure_start',
#     'zero_pressure_alarm',
#     'low_pressure_alarm',
#     'high_pressure_alarm',
#     'var_pressure_alarm',
#     'shutdown_alarm',
#     'test_mode',
#     'was_test_mode',
#     'faults',
#     'screen_name'
# ]

# vst_secrets = [
#     ('BUILD', '100.107'),
#     ('DEBUGGING', 'True'),
#     ('LONG_TIME_THRESHOLD', 15),
#     ('SHORT_TIME_THRESHOLD', 1),
#     ('LOW_PRESSURE_THRESHOLD', -40.0),
#     ('FAST_TIME_THRESHOLD', 50),
#     ('PRESSURE_THRESHOLD', 0.2),
#     ('LOW_CURRENT_THRESHOLD', 4.0),
#     ('ADC_ZERO_SETPOINT', 15422.0),
#     ('DEVICE_NAME', 'CPX-0000'),
#     ('locked', 'False')
# ]

# r_alarms = [
#     'low_pressure_alarm',
#     'high_pressure_alarm',
#     'zero_pressure_alarm',
#     'var_pressure_alarm',
#     'sd_card_alarm',
#     'overfill_alarm',
#     'vac_pump_alarm',
#     'maint_alarm',
#     'press_sensor_alarm',
#     'shutdown_alarm',
#     'buzzer',
#     'tls_relay',
#     'modem_alarm',
#     'buzzer_high',
#     'buzzer_low',
#     'buzzer_zero',
#     'buzzer_var',
#     'buzzer_triggered',
#     'buzzer_silenced',
#     'tls_buzzer_triggered',
#     'shutdown',
#     'all_stop'
# ]

# alarms = [
#     'buzzer_delay',
#     'buzzer_current',
#     'buzzer_count',
#     'shutdown_stage',
#     'critical_alarm_time',
#     'med_alarm_time',
#     'shutdown_time_60',
#     'shutdown_alarm_time',
#     'overfill_alarm_time',
#     'overfill_alarm_alert_time',
#     'overfill_alarm_override_time',
#     'buzzer_time',
#     'buzzer_duration',
#     'zero_pressure_start',
#     'high_pressure_start',
#     'low_pressure_start',
#     'var_pressure_start',
#     'test_start_timer',
#     'var_pressure'
# ]

# old_cont = [
#     ('gmid', 'CSX-0000'),
#     ('deviceID', ''),
#     ('productID', 'com.vsthose.admin:vstcp2'),
#     ('scr_width', 800),
#     ('scr_height', 480),
#     ('runcycles', 0),
#     ('startup', 000000),
#     ('continuous', 'true'),
#     ('temp', 0.0),
#     ('pressure_set_point', 0.2),
#     ('version', 'CSX-002B'),
#     ('serial', 00000000),
#     ('seq', 0),
#     ('maintenance_mode', 'False'),
#     ('test_mode', 'False'),
#     ('was_test_mode', 'False'),
#     ('test_purge_mode', 'False'),
#     ('test_burp_mode', 'False'),
#     ('manual_mode', 'False'),
#     ('utc', ''),
#     ('band', -1),
#     ('rssi', -1),
#     ('bars', -1),
#     ('rc_high_limit', -0.35),
#     ('rc_low_limit', -0.55),
#     ('rc_on_time', 15),
#     ('rc_off_time', 5),
#     ('cycles_per_block' 1),
#     ('current', 0.04),
#     ('adc_peak', 64),
#     ('adc_rms', 64),
#     ('adc_zero', 15422.0),
#     ('adc_raw', 0),
#     ('curr_amp', 0.0),
#     ('curr_sum', 0.0),
#     ('curr_samp', 0),
#     ('curr_avg', 0.0),
#     ('curr_rms', 0.040566037735849214),
#     ('adc_value', 15376),
#     ('curr_counter', 0),
#     ('calibration', 0),
#     ('signal_quality', 57),
#     ('access_tech', 'lte'),
#     ('power_state', 'on'),
#     ('modem_state', 'registered'),
#     ('local_ip', '192.168.1.152')
# ]

modem = [
    ('signal_quality', '57'),
    ('access_tech', 'lte'),
    ('power_state', 'on'),
    ('modem_state', 'local_ip')
         ]




def update_data(arg, msg):  # simple function to update any redis dictionary with any list of tuples
    update = dict(arg)
    r.hset(msg, mapping=update)
 
def set_all(data, digits):
    [r.set(x, 'False') for x in data]
    [r.set(y, 0) for y in digits]
    
def all_set(set_list):
    [r.set(x, y) for x, y in set_list]
    
if __name__ == '__main__':
    sig = [('signal_quality', 57)]
    acc = [('access_tech', 'lte')]
    power = [('power_state', 'on')]
    mod = [('modem_state', 'local_ip')]
    reboot = [('reboot','true')]
    
    #update_data(sig, 'modem2')
    #update_data(acc, 'modem2')
    #update_data(power, 'modem2')
    #update_data(mod, 'modem2')
    update_data(reboot, 'reboot')

