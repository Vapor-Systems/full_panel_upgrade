
import requests, json

def get_auth():

    headers = {'Content-type': 'application/json'}

    data = {'email': 'admin@vsthose.com','password': 'B4ustart!'}

    response = requests.post('https://g.api.soracom.io/v1/auth',headers=headers,json=data)

    data = json.loads(response.text)
    api_key = data['apiKey']
    token = data['token']

    # print(response.text)

    return api_key, token


