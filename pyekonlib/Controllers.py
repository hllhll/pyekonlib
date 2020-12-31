from pyekonlib.Frames import *
import datetime
import hexdump
from copy import copy
import logging

# asyncio is incredibly bad, found this package looks awesome and convinent!

SO_F = 1
SO_ServerUpdateDeviceFrame = 0x10
SO_ServerHeartbeeatFrame = 0x03

_LOGGER = logging.getLogger(__name__)


class Device(object):
	def __init__(self, deviceData=[]):	
		self.deviceData = deviceData


class DeviceSession(object):
	def __init__(self, deviceData=[]):	
		self.device = Device(deviceData)
		self.lastState = AirconStateData()
		self.lastMsgTime = datetime.datetime.now()
		self.firstState = True

	def getDeviceUpdateFrame(self, airconState, server):
		ret = ServerUpdateDeviceFrame()
		ret._number = server.serverId
		ret._state = airconState
		return ret.toBytes()



def emptyFn(dummy1=None, dummy2=None, dummy3=None):
	pass


class ServerController(object):
	DEVICE_TIMEOUT=120 #s
	SEND_HEARTBEAT_INTERVAL = 15

	# For interoprability with different async framework, we require some functions to create task and sleep
	def __init__(self, createAsyncTask, callLaterFn, serverId=0x9C400008):
		# This is sort of a guess that this is a server id
		self.serverId = serverId
		self._sessions = {}
		self.onReceivedDeviceKey = emptyFn
		self.onDeviceData = emptyFn
		self.onDeviceTimeout = emptyFn
		self.sendData = emptyFn
		self._lastHeartbeatSentTime = datetime.datetime(1,1,1,0,0,0,0)
		self._startPeriodicTimeoutCheckStarted = False
		self._timeout_task = None
		self._createAsyncTask = createAsyncTask
		self._callLaterFn = callLaterFn
		self._dummy = 0

	def getCurrentSession(self):
		if len(self._sessions.keys()) > 0:
			return self._sessions[list(self._sessions.keys())[0]]
		return None

	async def processData(self, data):
		frame = DeviceFrame.fromData(data)
		dev = False
		if len(self._sessions.keys()) > 0:
			dev = self._sessions[list(self._sessions.keys())[0]]
		if isinstance(frame, DeviceHeartbeatFrame):
			if not frame.deviceKey.hex() in self._sessions:
				dev = self._sessions[frame.deviceKey.hex()] = DeviceSession(frame.deviceKey)
				await self.onReceivedDeviceKey(self, dev)
				await self.sendHeartbeats()
		elif isinstance(frame, DeviceStateFrame):
			if len(self._sessions.keys()) == 0:
				# Got device state without heartbeat first, ignoring

				# TODO: Not sure this is the way to go, I'm under the impression that this is how Ekon's server works
				# Basically I think the server don't know the ID of the device talking to it
				# That's why it ignores State frames with no prior heartbeat/Hello

				# TODO: We might want to send Server Hello ourselves?
				return

			dev._lastState = frame.state
			await self.onDeviceData(self, dev, copy(frame.state))
		else:
			raise Exception("Unknown Device frame type")
		dev.lastMsgTime = datetime.datetime.now()

		# Todo, check if dev._lastState differs frame._state

	async def sendHeartbeats(self):
		for _ in self._sessions:
			self._createAsyncTask(self.sendData( ServerHeartbeatFrame(self.serverId).toBytes()))

		self._lastHeartbeatSentTime = datetime.datetime.now()

	def doTimeoutChecks(self, args=None):
		# In spite of what you think, it's not recursion
		if self._startPeriodicTimeoutCheckStarted:
			self._timeout_task = self._callLaterFn(1, self.doTimeoutChecks)

		now = datetime.datetime.now()
		for key in list(self._sessions.keys()):
			s = self._sessions[key]
			dt = now-s.lastMsgTime
			if dt.seconds > ServerController.DEVICE_TIMEOUT:
				self._createAsyncTask( self.onDeviceTimeout(self, s) )
				del self._sessions[key]
		if len(self._sessions.keys()) > 0:
			if (now-self._lastHeartbeatSentTime).seconds > ServerController.SEND_HEARTBEAT_INTERVAL:
				self._createAsyncTask(  self.sendHeartbeats() )

	async def startPeriodicTimeoutCheck(self):
		if not self._startPeriodicTimeoutCheckStarted:
			self._startPeriodicTimeoutCheckStarted = True
			self._timeout_task = self._callLaterFn(1, self.doTimeoutChecks)

	async def stopPeriodicTimeoutCheck(self):
		self._startPeriodicTimeoutCheckStarted = False
		# self._timeout_task.cancel()

	async def turnOff(self, deviceSession):
		data = ServerTurnOnOffFrame(on=False).toBytes()
		await self.sendData(data)

	async def updateDeviceState(self, deviceSession, newDeviceState):
		data = ServerUpdateDeviceFrame(newDeviceState).toBytes()
		await self.sendData(data)


# Stub, not really implemented
class ClientController(object):
	def __init__(self, clientData):
		self._clientData = clientData
		self._state = AirconStateData()
		self.onServerData = emptyFn
		self.onServerConnect = emptyFn
		self.onServerTimeout = emptyFn

	async def processData(self, data):
		frame = ServerFrame.fromData(data)
		if isinstance(frame, ServerHeartbeatFrame):
			# TBD
			pass
		elif isinstance(frame, ServerUpdateDeviceFrame):
			# TBD
			self._state = frame.state
