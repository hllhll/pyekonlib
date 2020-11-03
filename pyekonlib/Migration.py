import requests
import json


def sendCommand(deviceAddr, command, postData):
    url = "http://%s/config?command=%s" % (deviceAddr, command)
    headers = {'User-Agent': 'LuaSocket 2.0.2', 'Content-Type': 'application/json; charset=utf-8', 'Host': "1.1.1.1"}
    r = requests.post(url, headers=headers, data=json.dumps(postData, separators=(',', ':')))
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