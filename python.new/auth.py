import os
import requests
import json

SORACOM_EMAIL = 'admin@vsthose.com'
SORACOM_PASSWORD = 'b4ustart'


def get_auth(email=os.environ.get("SORACOM_EMAIL"), password=os.environ.get("SORACOM_PASSWORD")):
    data = {}
    headers = {'Content-Type': 'application/json'}
    payload = {'email': email, 'password': password}
    response = requests.post("https://api.soracom.io/v1/auth", headers=headers,data=json.dumps(payload)).text
    data = json.loads(res)
    apiKey = data['apiKey']
    token = data['token']
    self.headers = {
        'Accept': 'application/json',
        'X-Soracom-Api-Key': apiKey,
        'X-Soracom-Token': token
    }

    return response
    
def main():

    auth = get_auth(email=SORACOM_EMAIL, password=SORACOM_PASSWORD)
    
    print(auth)
    
if __name__ == '__main__':
    main()
    
