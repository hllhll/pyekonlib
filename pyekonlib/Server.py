from pyekonlib.Controllers import ServerController
import socket


class UDPServer(object):
    def __init__(self, bindingPort, serverId, onHvacConnected, onHvacTimeout, onDeviceChangeCallback, asyncSleepFn, createAsyncTaskFn, forward_endpoint = None):
        self._addressPair = ("0.0.0.0", bindingPort)
        self._serverId = serverId
        self._onDeviceChangeCallback = onDeviceChangeCallback
        self._sleepFn = asyncSleepFn
        self._createAsyncTaskFn = createAsyncTaskFn
        self._onHvacConnected = onHvacConnected
        self._onHvacTimeout = onHvacTimeout
        self._started = False
        self._stopRequest = False
        self._serverController = ServerController(createAsyncTaskFn, asyncSleepFn)
        self._serverController.onReceivedDeviceKey = self.receivedDeviceKey
        self._serverController.onDeviceData = self.deviceData
        self._serverController.onDeviceTimeout = self.deviceTimeout
        self._serverController.sendData = self.sendData

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(self._addressPair)
        self._sock.setblocking(False)

        self._forward_endpoint = forward_endpoint
        self._forward_sock = None
        if self._forward_endpoint:
            self._forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._forward_sock.setblocking(False)
            self._forward_sock.bind(('0.0.0.0', 80))

        # TODO: Change this when supporting multiple devices
        self._peer = ("0.0.0.0", 1)

    async def start(self):
        if self._started:
            return
        self._started = True
        await self._createAsyncTaskFn(self.reciverTask)
        await self._serverController.startPeriodicTimeoutCheck()

    async def stop(self):
        self._stopRequest = True
        await self._serverController.stopPeriodicTimeoutCheck()

    async def reciverTask(self):
        while not self._stopRequest:
            hasData = True
            try:
                data, addr = self._sock.recvfrom(256)
            except BlockingIOError as e:
                await self._sleepFn(1)
                hasData = False

            if hasData:
                self._peer = addr
                await self._serverController.processData(data)
                if self._forward_sock is not None:
                    # Send data to forwarding server
                    self._forward_sock.sendto(data, self._forward_endpoint)

            # Check if has data from forwarded server and send to device
            if self._forward_sock is not None:
                hasData = True
                try:
                    data, addr = self._forward_sock.recvfrom(256)
                except BlockingIOError as e:
                    hasData = False

                if hasData:
                    self._forward_sock.sendto(data, self._peer)
        await self._serverController.stopPeriodicTimeoutCheck()
        self._started = False

    async def receivedDeviceKey(self, srvController, deviceSession):
        # For this use case, only receiving the device key / id doesnt really matter,
        # Session was already setup by the controller
        pass

    async def deviceData(self, srvController, deviceSession, airconState):
        if deviceSession.firstState:
            deviceSession.firstState = False
            # For more simpler interfacing, I define connection as established only after I have the
            # 1st state of the hvac
            await self._onHvacConnected(deviceSession, airconState)

        await self._onDeviceChangeCallback(deviceSession, airconState)
        # TODO: This doesn't work, Do I even need it? i want for client to be able to check freshness of data
        """elif deviceSession.lastState!=airconState:
            print("UDPServer device data " + airconState.toString())
            await self._onDeviceChangeCallback(deviceSession, airconState)
        else:
            print ("NoChange.")"""

    async def deviceTimeout(self, srvController, deviceSession):
        await self._onHvacTimeout(deviceSession)

    async def sendData(self, data):
        self._sock.sendto(data, self._peer)

    async def sendNewState(self, state):
        await self._serverController.updateDeviceState(self._serverController.getCurrentSession(), state)



