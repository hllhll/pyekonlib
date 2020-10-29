import pyekonlib.Controllers as ekon
import pyekonlib.Frames as frames
import hexdump
import asyncio
import socket
#from curio import socket
import curio
from pyekonlib import *

serverId=0x9C400008
clientData=b'\x10\xe0\x14 ?a\xf3\xb1\r-2\x0e\xdf-\xa0p\xe0'

localIP	 = "0.0.0.0"
localPort   = 6343
bufferSize  = 512

async def myAIOCreateTask(task):
	loop = asyncio.get_event_loop()
	asyncio_task = loop.create_task(task())


async def myAISleep(milis):
	await asyncio.sleep(milis)


client = ekon.ClientController(clientData)
peer = 123
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((localIP, localPort))
sock.setblocking(False)

async def devConnected(srvController,deviceSession):
	print ("**test.py device connected deviceData:" + str(deviceSession.device.deviceData))


async def devData(srvController, deviceSession, airconState):
	print ("test.py device data " + airconState.toString())
	"""if airconState.targetTemp == 220:
		airconState.targetTemp = 230
		print("gen new update")"""
	# Note that the screen takes a while to update, but I think it applies in the moment.
	# await srvController.updateDeviceState(deviceSession, airconState)


async def devTimeout(srvController, deviceSession):
	print ("**test.py device timeout " + str(deviceSession.device.deviceData))


async def sendData(data):
	# print ("sendData sending")
	# print (hexdump.dump(data))
	# await sock.sendto(data, peer)
	sock.sendto(data, peer)

async def main(sleepfn):
	global server, sock
	tst = AirconStateData()
	server.onDeviceConnect = devConnected
	server.onDeviceData = devData
	# Not sure if this should be here
	server.onDeviceTimeout = devTimeout
	server.sendData = sendData

	# https://stackoverflow.com/questions/48506460/python-simple-socket-client-server-using-asyncio
	await server.startPeriodicTimeoutCheck()
	while True:
		try:
			data, addr = sock.recvfrom(256)
		except BlockingIOError as e:
			await sleepfn(1)
			continue
		global peer
		peer = addr
		await server.processData(data)
	await server.stopPeriodicTimeoutCheck()


async def aio_main():
	global server
	server = ekon.ServerController(myAIOCreateTask, myAISleep, serverId)
	await main(myAISleep)


async def myCurioSleep(x):
	await curio.sleep(x)


async def myCurioCreateTask(task):
	await curio.spawn(task)


async def curio_main():
	global server
	server = ekon.ServerController(myCurioCreateTask, myCurioSleep, serverId)
	await main(myCurioSleep)

async def dummyAsincIoTask():
	print("dummy")


asyncio.run(aio_main())
#curio.run(curio_main)