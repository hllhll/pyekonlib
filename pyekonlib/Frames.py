import datetime	
import struct
from pyekonlib.Misc import *
from pyekonlib import *
StartOfFrame = 1
# FrameType
FT_ServerUpdateDeviceFrame = 0x10
FT_ServerHeartbeatFrame = 0x03
FT_ServerHeartonOffFrame = 0x06
FT_DeviceHeartbeatFrame = 0
FT_DeviceStateFrame = 3

class Frame(object):
	def __init__(self):
		pass

# From server
class ServerFrame(Frame):
	def __init__(self):
		super().__init__()

	@staticmethod
	def fromData(data):
		data = bytearray(data)
		idx = 0
		# Server Heartbeat
		# [0000]   01 03 9C 40 00 08 6B 88                             ...@..k. 
		# Server Command
		#		   01 10 9C 40 00 08 10 00 ...
		assert data[idx] == StartOfFrame
		assert crc16(data[idx:]) == 0
		idx += 1

		if data[idx] == FT_ServerUpdateDeviceFrame:
			idx += 1
			obj = ServerUpdateDeviceFrame()
			format_s = ">IBBBBBBBBBBBHHH"

			(num, obj._f1, _, onoff_val, _, obj._f2, _, obj._state._state, _,
				obj._state._fanSpeed, _, _, obj._state._currentTemp, obj._state._targetTemp, obj._state._f3) = struct.unpack_from(format_s, data, idx)
			obj._state._onoff = False
			if onoff_val==0x55:
				obj._state._onoff = True
			obj._number = num
			return obj
		if data[idx] == FT_ServerHeartbeatFrame:
			obj = ServerHeartbeatFrame()
			return obj
		# TODO: Better exceptions
		raise Exception("Unknown frame type")

	def toString(self):
		pass


# TODO: This looks like a server "hello" frame and not heartbeat, it might be that there ARE NO HEARTBEATS at all
#  in both directions
class ServerHeartbeatFrame(ServerFrame):
	# [0000]   01 03 9C 40 00 08 6B 88 
	def __init__(self, id=0):
		super().__init__()
		self._serverId = id

	def toString(self):
		return "Server Heartbeat %d" % self._serverId

	def toBytes(self):
		format_s = ">BBI"

		data = struct.pack(format_s,StartOfFrame, FT_ServerHeartbeatFrame , self._serverId)
		cs = crc16(data)
		data = bytearray(data)

		data.append( (cs>>8)&0xff )
		data.append( (cs)&0xff )
		return data

class ServerTurnOnOffFrame(ServerFrame):
	def __init__(self, on=False):
		self._number = 0x9c40
		self.on = on
		super().__init__()

	def toBytes(self):
		# 01 06 9C 40 00 55   66 71
		# 01 06 numbe onoff cs cs
		format_s = ">BBHH"
		on_val = 0xAA # Off
		if self.on:
			on_val = 0x55
		data = struct.pack(format_s, StartOfFrame, FT_ServerHeartonOffFrame, self._number, on_val)
		cs = crc16(data)
		data = bytearray(data)

		data.append( (cs>>8) & 0xff )
		data.append( (cs) & 0xff )
		return data

class ServerUpdateDeviceFrame(ServerFrame):
	def __init__(self, state = AirconStateData()):
		self._state = state
		self._number = 0x9C400008
		# Not the same as device._f1
		self._f1 = 0x10
		# Not the same as device._f2
		self._f2 = 0
		super().__init__()

	def toBytes(self):
		#01 10   <uint32>	 <f1> 00 <on> 00 ?? 00 <hvac> 00 <fs> 00 00 <ct> <ct> <tt> <tt> ?? ?? <cs> <cs>
		format_s = ">BBIBBBBBBBBBBBHHH"

		ekon_onoff = 0xAA
		if self._state.onoff:
			ekon_onoff = 0x55

		data = struct.pack(format_s, StartOfFrame , FT_ServerUpdateDeviceFrame, self._number, self._f1, 0, ekon_onoff, 0, self._f2, 0, self._state.mode.value, 0,
			self._state.fanSpeed, 0, 0, self._state.currentTemp, self._state.targetTemp, self._state._f3)
		cs = crc16(data)
		data = bytearray(data)

		data.append( (cs>>8) & 0xff )
		data.append( (cs) & 0xff )
		return data

	def toString(self):
		return "Server UpdateDeviceFrame, number=0x%x, f1=0x%x, f2=0x%x\n" % (self._number, self._f1, self._f2) + self._state.toString()


class DeviceFrame(Frame):
	def __init__(self):
		super().__init__()
	@staticmethod
	def fromData(data):
		data = bytearray(data)
		idx = 0
		# 01 03 <f1> 00 <on> 00 ?? 00 <hvac> 00 <fan> 00 00 <ct> <ct> <tt> <tt> ?? ?? <cs> <cs>
		# Assuming initial "0" might be omited from heartbeat packet
		# see https://github.com/hllhll/HomeAssistant-EKON-iAircon/issues/19
		assert (len(data) >= 0x13)
		if data[0]==0:
			idx = 1
		if data[idx]==StartOfFrame and data[idx+1] == FT_DeviceHeartbeatFrame and data[idx+2] == 0x10:
			idx += 2
			# Not a checksum??!?!?
			# TODO: Check whats up with the checksum
			return DeviceHeartbeatFrame(data[idx:])
		if data[idx] == StartOfFrame and data[idx+1] == FT_DeviceStateFrame:
			assert crc16(data[idx:]) == 0
			ret = DeviceStateFrame()
			# Data packet
			idx += 2

			[ret._f1, _, onoff_val, _, ret._f2, _, modeval, _, ret.state.fanSpeed, _, _, ret.state.currentTemp, ret.state.targetTemp, ret.state._f3, cs] = struct.unpack_from(">BBBBBBBBBBBHHHH",data,idx)

			ret.state.onoff = False
			if onoff_val == 0x55:
				ret.state.onoff = True

			ret.state.mode = AirconMode(modeval)

			return ret
		raise Exception("Unknown frame type")


class DeviceHeartbeatFrame(DeviceFrame):
	def __init__(self, deviceKey = 0):
		self.deviceKey = deviceKey
		super().__init__()

	def toString(self):
		return "DeviceHeartbeatFramee deviceKey=" + str(self.deviceKey)


class DeviceStateFrame(DeviceFrame):
	def __init__(self):
		self.state = AirconStateData()
		self._f1 = 0
		self._f2 = 0
		super().__init__()
	def toString(self):
		ret = "DeviceStateFrame f1=%x f2=%x\n" % (self._f1, self._f2)
		return ret+self.state.toString()
