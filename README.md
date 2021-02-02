# pyekonlib

This is a package that implements Ekon/Connect/Airconet+ communication protocol with the wireless HVAC Controller.

# How device communication works
## AP association to the Wifi network
The device, being esp8285-like-based, utilize ESPTouch/ESPSmart config method in order to find
and convey the wifi network credentials to the device.
This can be achived using the original app, or through any alternative app such as [ESPTouch](https://play.google.com/store/apps/details?id=com.khoazero123.iot_esptouch_demo)

##  Configuring the device
After the device has joind the wireless network it is required to tell it to what server to connect to,
this is done by an HTTP POST to the device
 ```
POST /config?command=client HTTP/1.1
User-Agent: LuaSocket 2.0.2
Content-Length: <content-length>
Content-Type: application/json; charset=utf-8
Host: 1.1.1.1

{"client_set":[{"ip":"<server_addr>","port":<server_udp_port>,"protocol":"UDP","local_port":80},{"protocol":"","ip":""},{"protocol":"","ip":""},{"protocol":"","ip":""}]}
```
Yup, the communication is connection-less UDP.
With the `client` we can instruct the device to communicate with are own crafted server,
implemented by this library, reside on arbitrary ip address.
**The entire request, should be sent in a single send() call**, thus any python http library for curl request would probably won't suffice

This can be performed by the library
```
from pyekonlib.Migration import SetDeviceUDPServer

SetDeviceUDPServer("deviceAddr", "serverAddr", serverPort)
```
where `serverAddr` is the address of the machine running this lib's server
and serverPort is the UDP port it's listening on.
If the device has connected already to a preconfigured server, it will connect to both the new `serverAddr` while also remaining connected to the old one. Upon restart it will connect to the new one only.

## Protocol
Not all fields were identified, but enough was identified in order to 
give basic meaning and parse incoming frames from the device, and forge 
frames that would be understood by the device. Please tell if u have an
idea about the contents of the fields that are not fully understood :P


# Known issues
- In Forward mode, using the Ekon/TC app, You may change settings of the HVAC, and it will ignore you \
  This is due to the script pulling the device, and updating ekon's server before ekon server's sends out
  the message to the device (or the `proxy` which is this lib). Increasing `SEND_HEARTBEAT_INTERVAL = 10` in the `ServerController`
  might help with thad  
- ~~While development I've stumbled situations where device stops responding, please take note if this happens~~
  - Try to power-cycle the device, if not, hard-reset (button or `POST ?comand=restore` )  and pair with regular app to see that it's working
  - **Havn't encountered in a while, this is probobly no longer an issue.**
- Should't matter to most of you: Device emulation (I.E. Simulating a device) is only slightly implemented - NOT WORKING

# Code structure
I've stuck to most of the code being async and roughly async-framework agnostic
(I probably did it really bad if U know something in python, please PR)
- Frames - Abstract raw protocol datagrams away from the caller
- Controllers - Abstracts the interactions of the protocol away from the caller
  - Responsible for both side of communication and
    receiving/sending using the specified callbacks.
  - Provides callback to the user when identifying new device and 
    the receiving of a new (or equally, old) state from the device   
- Server - Abstracts mostly anything and gives out callbacks for device connection,
  disconnection, and updates from the device, plus sending new state to the device.

# Note from the developer
I'm not a developer, I'm a security researcher, as such the code quality is probably poor
nor do I like python so much but it seemed most reasonable to do this in python.
The main thought when abstracting-away the protocol and communication was to implement integration for 
various Smart-home integration solutions, such as HomeAssistant.
