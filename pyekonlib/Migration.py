import requests
import json


def sendCommand(deviceAddr, command, postData):
    url = "http://%s/config?command=%s" % (deviceAddr, command)
    headers = {'user-agent': 'LuaSocket 2.0.2'}
    r = requests.post(url, headers=headers, data=json.dumps(postData))
    return r.status_code == requests.codes.ok


def SetDeviceUDPServer(deviceAddr, serverAddr, serverPort):
    data = {
        "client_set": [
            {"ip": serverAddr, "port": serverPort, "protocol": "UDP", "local_port": 80},
            {"protocol": "", "ip": ""},
            {"protocol": "", "ip": ""},
            {"protocol": "", "ip": ""},
        ]
    }

    return sendCommand(deviceAddr, "client", data)