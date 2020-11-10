import requests
import json
import socket

def sendCommand(deviceAddr, command, postData):
    path = "/config?command=%s" % (command)
    headers = {'User-Agent': 'LuaSocket 2.0.2', 'Content-Type': 'application/json; charset=utf-8', 'Host': "1.1.1.1"}
    req_pqyload = json.dumps(postData, separators=(',', ':'))

    headers["Content-Length"] = len(req_pqyload)

    header_rows = (": ".join((k, str(headers[k]))) for k in headers.keys())
    headers = "\r\n".join(header_rows)

    request_str = "POST " + path + " HTTP/1.1\r\n" + \
        headers + "\r\n" + \
        "\r\n" + \
        req_pqyload

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((deviceAddr, 80))
    client.send(request_str.encode())

    # deviceAddr
    response = client.recv(4096)
    str_resp = str(response)

    # TODO, The device has uniqe fingerpring whereas it does not have space between the HTTP headers and data, like
    """HTTP/1.1 200 OK
    Content-Type:text/html
    Content-Length:0"""
    return str_resp.find("200 OK") != -1


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