#!/usr/bin/python3

import redis
import json
import pickle

rconn = redis.Redis('localhost',decode_responses=True) 

cont = {}

cont = json.loads(rconn.get("cont"))
runs = json.loads(rconn.get("runcycles"))

fob = open("mcu.obj","wb")

runs = 1105

cont['runcycles']= runs
print(cont)

rconn.set('cont',json.dumps(cont))
rconn.set('runcycles', json.dumps(runs))
pickle.dump(runs,fob)
