# !/usr/bin/python3
# -*-coding:utf-8 -*-
# **********************************************
# @Time     : 2019/12/5 18:02
# @Author   : Kevin Zheng
# @File     : server.py
# @Contact  : 95900021@qq.com
# @Version  : 
# @Function :
# **********************************************
import asyncio
import functools
import logging
import os
import signal
import sys
import uvloop

from guniserver.protocol import TCPProtocol

logger = logging.getLogger("guniserver")

HANDLED_SIGNALS = (
    signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)


class Server:
    def __init__(self, config):
        self.config = config
        self.total_requests = 0
        self.connections = set()

        self.started = False
        self.should_exit = False
        self.force_exit = False
        self.last_notified = 0

        self.loop = None

        self.be_servers = []

    def run(self):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.serve())

    async def serve(self):
        process_id = os.getpid()

        config = self.config
        if not config.loaded:
            config.load()

        self.install_signal_handlers()

        message = "Started server process [%d]"
        logger.info(message, process_id)

        await self.startup()
        if self.should_exit:
            return
        await self.main_loop()
        await self.shutdown()

        message = "Finished server process [%d]"
        logger.info(message, process_id)

    async def startup(self):
        config = self.config

        create_protocol = functools.partial(TCPProtocol,
                                            config=config,
                                            server=self)

        # Standard case. Create a socket from a host/port pair.
        try:
            server = await self.loop.create_server(create_protocol,
                                                   host=config.host,
                                                   port=config.port)
        except OSError as exc:
            logger.error(exc)
            sys.exit(1)

        message = "GuniServer running on %s:%d (Press CTRL+C to quit)"
        logger.info(message, config.host, config.port)
        self.be_servers.append(server)
        self.started = True

    async def main_loop(self):
        counter = 0
        should_exit = await self.on_tick(counter)
        while not should_exit:
            counter += 1
            await asyncio.sleep(1)
            should_exit = await self.on_tick(counter)

    async def on_tick(self, counter) -> bool:
        if self.config.t_keep_alive and counter % self.config.t_keep_alive == 0:
            # notify all connections
            for connection in list(self.connections):
                connection.handle_ka()

        # Determine if we should exit.
        if self.should_exit:
            return True
        if self.config.concurrency is not None:
            return self.total_requests >= self.config.concurrency
        return False

    async def shutdown(self):
        logger.info("Shutting down")

        # Stop accepting new connections.
        for server in self.be_servers:
            server.close()
        for server in self.be_servers:
            await server.wait_closed()

        # Request shutdown on all existing connections.
        for connection in list(self.connections):
            connection.shutdown()
        await asyncio.sleep(0.1)

        # Wait for existing connections to finish sending responses.
        if self.connections and not self.force_exit:
            msg = "Waiting for connections to close. (CTRL+C to force quit)"
            logger.info(msg)
            while self.connections and not self.force_exit:
                await asyncio.sleep(0.1)

        # Wait for existing tasks to complete.
        if not self.force_exit:
            msg = "Waiting for background tasks to complete. (CTRL+C to force quit)"
            logger.info(msg)
            while not self.force_exit:
                await asyncio.sleep(0.1)

    def install_signal_handlers(self):
        loop = asyncio.get_event_loop()

        try:
            for sig in HANDLED_SIGNALS:
                loop.add_signal_handler(sig, self.handle_exit, sig, None)
        except NotImplementedError:
            # Windows
            for sig in HANDLED_SIGNALS:
                signal.signal(sig, self.handle_exit)

    def handle_exit(self, sig, frame):
        if self.should_exit:
            self.force_exit = True
        else:
            self.should_exit = True
