from pyekonlib.Controllers import ServerController
import socket
import logging
import asyncio
_LOGGER = logging.getLogger(__name__)

class UDPServer(object):
    def __init__(self, bindingPort, serverId, onHvacConnected, onHvacTimeout, onDeviceChangeCallback, callLaterFn, createAsyncTaskFn, forward_endpoint = None):
        _LOGGER.debug("Creating UDPServer")
        self._addressPair = ("0.0.0.0", bindingPort)
        self._serverId = serverId
        self._onDeviceChangeCallback = onDeviceChangeCallback
        self._callLaterFn = callLaterFn
        self._createAsyncTaskFn = createAsyncTaskFn
        self._onHvacConnected = onHvacConnected
        self._onHvacTimeout = onHvacTimeout
        self._started = False
        self._stopRequest = False
        self._serverController = ServerController(createAsyncTaskFn, callLaterFn)
        self._serverController.onReceivedDeviceKey = self.receivedDeviceKey
        self._serverController.onDeviceData = self.deviceData
        self._serverController.onDeviceTimeout = self.deviceTimeout
        self._serverController.sendData = self.sendData

        self._forward_endpoint = forward_endpoint

        # TODO: Change this when supporting multiple devices
        self._peer = ("0.0.0.0", 1)

        self._dev_transport = self._dev_protocol = None
        self._srv_transport = self._srv_protocol = None

    class EkonProtocolFactory:
        def __init__(self, _sync_data_recived_fn):
            self._sync_data_recived_fn = _sync_data_recived_fn
            self._transport = None

        def connection_made(self, transport):
            self._transport = transport

        def datagram_received(self, data, addr):
            self._sync_data_recived_fn(data, addr)

    #class EkonDeviceProtocolFactory:
    #    def __init__(self, _sync_data_recived_fn):

    async def start(self):
        _LOGGER.info("Starting UDP Server reciver task and periodicTimeoutCheck")
        if self._started:
            return
        self._started = True
        # await self._createAsyncTaskFn(self.reciverTask())

        # Get a reference to the event loop as we plan to use
        # low-level APIs.
        loop = asyncio.get_running_loop()

        # One protocol instance will be created to serve all
        # client requests.
        self._dev_transport, self._dev_protocol = await loop.create_datagram_endpoint(
            lambda: UDPServer.EkonProtocolFactory( self.syncHandleRecivedDataFromDevice ),
            local_addr=self._addressPair)

        if self._forward_endpoint:
            loop = asyncio.get_running_loop()
            self._srv_transport, self._srv_protocol = await loop.create_datagram_endpoint(
                lambda: UDPServer.EkonProtocolFactory( self.syncHandleRecivedDataFromServer ),
                remote_addr=self._forward_endpoint)


        await self._serverController.startPeriodicTimeoutCheck()

    async def stop(self):
        _LOGGER.info("Stopping UDP Server reciver task and periodicTimeoutCheck")
        #self._stopRequest = True
        self._dev_transport.close()
        if self._forward_endpoint:
            self._srv_transport.close()
        await self._serverController.stopPeriodicTimeoutCheck()

    def syncHandleRecivedDataFromDevice(self, data, addr):
        self._peer = addr
        # Magic of sync->async
        self._createAsyncTaskFn(self._serverController.processData(data))
        if self._forward_endpoint:
            # Send data to forwarding server
            self._srv_transport.sendto(data, self._forward_endpoint)

    def syncHandleRecivedDataFromServer(self, data, addr):
        self._dev_transport.sendto(data, self._peer)

    async def receivedDeviceKey(self, srvController, deviceSession):
        _LOGGER.debug("UDPServer - receivedDeviceKey")
        # For this use case, only receiving the device key / id doesnt really matter,
        # Session was already setup by the controller
        pass

    async def deviceData(self, srvController, deviceSession, airconState):
        _LOGGER.debug("UDPServer - Got data from device")
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
        _LOGGER.debug("UDPServer - device timeout")
        await self._onHvacTimeout(deviceSession)

    async def sendData(self, data):
        _LOGGER.debug("UDPServer - Sending data to device")
        # self._sock.sendto(data, self._peer)
        self._dev_transport.sendto(data, self._peer)

    async def sendNewState(self, state):
        await self._serverController.updateDeviceState(self._serverController.getCurrentSession(), state)



