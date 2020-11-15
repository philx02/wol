#!/usr/bin/python3

import asyncio
from websocketserver import WebSocketServer
import wakeonlan
from subprocess import call
import platform
import os

class WolServer:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.producer_condition = asyncio.Condition(lock=self.lock)
        self.awake = False
        self.ip_address = "192.168.2.106"
        self.mac_address = "C4:E9:84:05:1B:E1"

    async def init(self, websocket):
        await websocket.send("hello")

    async def produce(self, websocket):
        with (await self.producer_condition):
            await self.producer_condition.wait()
            status = self.awake
        await websocket.send(str(status))

    async def consume(self, websocket):
        message = await websocket.recv()
        if message == "wol":
            wakeonlan.send_magic_packet(self.mac_address, ip_address=self.ip_address)
        await websocket.send("wol_done")

    async def notify_clients(self, websocket_server):
        if len(websocket_server.connected) > 0:
            if platform.system() == "Windows":
                self.awake = call("ping -n 1 " + self.ip_address) == 0
            else:
                self.awake = call(["ping", "-c", "1", self.ip_address]) == 0
        with (await self.producer_condition):
            self.producer_condition.notify_all()
        await asyncio.sleep(1)
        asyncio.ensure_future(self.notify_clients(websocket_server))

def main():
    loop = asyncio.get_event_loop()
    wol_server = WolServer()

    websocket_server = WebSocketServer(wol_server.init, wol_server.consume, wol_server.produce, 8011)
    loop.run_until_complete(websocket_server.start_server)

    asyncio.ensure_future(wol_server.notify_clients(websocket_server))

    asyncio.get_event_loop().run_forever()

main()
