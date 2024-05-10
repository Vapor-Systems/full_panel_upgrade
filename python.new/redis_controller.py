import redis
#r = redis.Redis(host='localhost', port=6379, decode_responses=True)

class Red:
    def __init__(self,var_name):
    #def __init__(self,var_name,value):
        self.r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.value=0
        self.name=var_name
        # self.r.set(self.name,self.value)

    def get(self):
        # print(f"{self.name}:{self.value}")
        resp = self.r.get(self.name)
        print(f"Rdis: {resp}")
        return resp

    
    def set(self,value):
        self.r.set(self.name,value)
        self.value = value

# gmid = Red('gmid',"test ID")
# print(f"Value: {gmid.value}")

# #gmid.get()
# gmid.set("Brave new world")
# print(f"Value: {gmid.value}")

# gmid.set("This is test")
# boo= gmid.get()
# print(f"Hoo:{boo}")

    
