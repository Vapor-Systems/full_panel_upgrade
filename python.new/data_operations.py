''' Data Operations'''

import redis
import json
import logging
import subprocess 

rconn = redis.Redis('localhost',decode_responses=True) ### Installing Redis as dictionary server

class Data:

    def save_object(self,name,obj):

        try:
            rconn.set(name,json.dumps(obj))
        except:
            logging.error("Error writing {name} code to redis.  Switching to json.")

            try:
                json_file = f'/home/pi/python/{name}.json'

                with open(json_file, 'w') as outfile:
                    json.dump(obj, outfile)
            except:
                logging.error("Error writing {name} object.  Profile failed to save.")


    def save_startup_code(self,startup):
        self.save_object('startup',startup)


    def save_timers(self,timers):
        self.save_object('timers',timers)


    def save_alarms(self,alarms):
        self.save_object('alarms',alarms)


    def save_controller(self,controller):
        self.save_object('cont',controller)


    def save_profile(self,profile):
        self.save_object('profile',profile)


    def save_runcycles(self,runcycles):
        self.save_object('runcycles',runcycles)


    def get_object(self,name,init_value):
        returned  = init_value

        try:
            returned = json.loads(rconn.get(f'{name}'))
        except:
            logging.error('Error reading {name} Redis Object.  Attempting JSON.')

            try:
                json_file = f'/home/pi/python/{name}.json'

                with open(json_file, 'r') as infile:
                    returned = json.load(infile)
            except: 
                logging.error('Error reading {name} JSON.  Startup code failed to load.')
            else:
                keys_returned = json.load(json) 

                self.save_object(name,returned)  ### Save as Redis Object

        return returned


    def get_secrets(self):
        return self.get_object('secrets',None)


    def get_controller(self):
        return self.get_object('cont',None)


    def get_timers(self):
        return self.get_object('timers',None)


    def get_alarms(self):
        return self.get_object('alarms',None)


    def get_startup_code(self):
        return self.get_object('startup','000000')


    def get_profile(self):
        return self.get_object('profile','CS8')

    def get_modem(self):
        try:
            modem_str = subprocess.getoutput('mmcli -m 0 -J')
            modem = json.loads(modem_str)
            json_formatted_str = json.dumps(modem, indent=4)

            return modem

        except:

            return None


    def get_runcycles(self,cont):

        rc = self.get_object('runcycles',-1) 
        cont['runcycles'] = rc if rc else -1

        return cont


    def get_serial(self,cont):

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
        

        cont['serial'] = cpuserial
        self.save_controller(cont)

        return cont

