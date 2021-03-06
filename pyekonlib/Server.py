from pyekonlib.Controllers import ServerController
import socket
import time
import threading
import logging
import asyncio
_LOGGER = logging.getLogger(__name__)

class UDPServer(object):
    # Todo, implement logging maybe with
    # logging.getLogger("asyncio").setLevel(logging.DEBUG)

    def __init__(self, bindingPort, serverId,
                 onHvacConnected,
                 onHvacTimeout,
                 onDeviceChangeCallback,
                 callLaterFn,
                 createAsyncTaskFromThreadFn,
                 createAsyncTaskFromEventLoopFn,
                 forward_endpoint = None):
        _LOGGER.debug("Creating UDPServer")
        self._addressPair = ("0.0.0.0", bindingPort)
        self._serverId = serverId
        self._onDeviceChangeCallback = onDeviceChangeCallback
        self._callLaterFn = callLaterFn
        self._createAsyncTaskFromThreadFn = createAsyncTaskFromThreadFn
        self._onHvacConnected = onHvacConnected
        self._onHvacTimeout = onHvacTimeout
        self._started = False
        self._stopRequest = False
        self._serverController = ServerController( createAsyncTaskFromEventLoopFn , callLaterFn)
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
        # Behind the scene this is actually implemented as a thread, so calls to asyncio functions
        # Should be considered from a thread context
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

    # This is run in the thread created by the ProtocolFactory
    def syncHandleRecivedDataFromDevice(self, data, addr):
        self._peer = addr
        # Magic of sync->async
        self._createAsyncTaskFromThreadFn(self._serverController.processData(data))
        if self._forward_endpoint:
            # Send data to forwarding server
            self._srv_transport.sendto(data, self._forward_endpoint)

    # This is run in the thread created by the ProtocolFactory
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

    async def turnOff(self):
        await self._serverController.turnOff(self._serverController.getCurrentSession())

    async def turnOn(self):
        await self._serverController.turnOn(self._serverController.getCurrentSession())


# Since python suck in protecting bad programmers writing bad code (such as me)
# in a way that the code misuses the async framework and screws up the common event loop,
# I've decided to implement this wrapper which allocates a different event loop for this integration
# effectively, rendering asyncio useless and spawning another thread.

class UDPServerLoopIndependent(UDPServer):

    def __init__(self, bindingPort, serverId,
            onHvacConnected,  # note, onXXX are still async functionsף They will be called from my event loop
                              # Which should be sufficient since HA, for example, explicitlly uses it's own loop to .. do stuff.
            onHvacTimeout,
            onDeviceChangeCallback,
            forward_endpoint = None):

        self.el = asyncio.new_event_loop()
        _workThread = threading.Thread(target=self.el.run_forever)
        _workThread.start()

        super().__init__( bindingPort, serverId,
            onHvacConnected,
            onHvacTimeout,
            onDeviceChangeCallback,
            self.el.call_later,
            self.my_create_async_task,
            self.el.create_task,
            forward_endpoint)

    # Create async task from a thread context
    def my_create_async_task(self, corutine):
        return asyncio.run_coroutine_threadsafe(corutine, self.el)
