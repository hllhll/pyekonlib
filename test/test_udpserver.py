# For homeassistant, impoart this package via github using manifest-requirements, can link to github tag
# https://developers.home-assistant.io/docs/creating_integration_manifest/#custom-requirements-during-development--testing
from _ast import Set

from pyekonlib import *
from pyekonlib.Server import UDPServer
from pyekonlib.Migration import SetDeviceUDPServer
import asyncio
import hexdump

devConnected = False


async def hvacStatusRecived(deviceSession, state):
    print("HVAC State")
    print(state.toString())

def myAIOCreateTask(task):
    loop = asyncio.get_event_loop()
    asyncio_task = loop.create_task(task)

async def hvacConnected(deviceSession, firstState):
    global devConnected
    print("Device connected! " + hexdump.dump(deviceSession.device.deviceData)  + " state: ")
    print(firstState.toString())
    devConnected = True

async def hvacTimeout(deviceSession):
    print("Disconnected")
    devConnected = False

# remember that call later accept sync cb
def callLater(time, func):
    event_loop = asyncio.get_event_loop()
    event_loop.call_later(time, func)


import socket
async def aio_main():
# Tadiran connect
    """ekonServer = UDPServer(6343, 0x9C400008, got_new_hvac_status, asyncio.sleep, myAIOCreateTask,
                           ("185.28.152.215", 6343))"""
    # Airconet +
    """ekonServer = UDPServer(6343, 0x9C400008, got_new_hvac_status, asyncio.sleep, myAIOCreateTask,
                           ("3.137.73.173", 6343))"""
    ekonServer = UDPServer(6343, 0x9C400008, hvacConnected, hvacTimeout, hvacStatusRecived, callLater, myAIOCreateTask, ("3.137.73.173", 6343))
    newStateScenario = AirconStateData(onoff=True, mode=AirconMode.Cool, targetTemp=220, currentTemp=220, fanSpeed=2)
    await ekonServer.start()

    try:
        SetDeviceUDPServer("192.168.1.20", "192.168.1.10", 6343)
    except socket.error as e:
        print(e)

    await asyncio.sleep(1)
    print("==========aio_main scenerio===========")
    """await ekonServer.sendNewState(newStateScenario)
    await asyncio.sleep(5)
    newStateScenario.fanSpeed = 1
    await ekonServer.sendNewState(newStateScenario)"""
    await asyncio.sleep(7200)


asyncio.run(aio_main())
