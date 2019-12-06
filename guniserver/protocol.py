# !/usr/bin/python3
# -*-coding:utf-8 -*-
# **********************************************
# @Time     : 2019/12/5 18:06
# @Author   : Kevin Zheng
# @File     : protocol.py
# @Contact  : 95900021@qq.com
# @Version  : 0.1.0
# @Function : protocol in TCP server
# **********************************************
import asyncio
import socket
import logging

from guniserver.config import Config
from guniserver.errors import *

logger = logging.getLogger("guniserver")


def get_remote_addr(transport):
    socket_info = transport.get_extra_info("socket")
    if socket_info is not None:
        try:
            info = socket_info.getpeername()
        except OSError:
            # This case appears to inconsistently occur with uvloop
            # bound to a unix domain socket.
            family = None
            info = None
        else:
            family = socket_info.family

        if family in (socket.AF_INET, socket.AF_INET6):
            return str(info[0]), int(info[1])
        return None
    info = transport.get_extra_info("peername")
    if info is not None and isinstance(info, (list, tuple)) and len(info) == 2:
        return str(info[0]), int(info[1])
    return None


def get_local_addr(transport):
    socket_info = transport.get_extra_info("socket")
    if socket_info is not None:
        info = socket_info.getsockname()
        family = socket_info.family
        if family in (socket.AF_INET, socket.AF_INET6):
            return str(info[0]), int(info[1])
        return None
    info = transport.get_extra_info("sockname")
    if info is not None and isinstance(info, (list, tuple)) and len(info) == 2:
        return str(info[0]), int(info[1])
    return None


def is_ssl(transport):
    return bool(transport.get_extra_info("sslcontext"))


def get_client_addr(scope):
    client = scope.get("client")
    if not client:
        return ""
    return "%s:%d" % client


class TCPProtocol(asyncio.Protocol):
    def __init__(self,
                 config: Config,
                 server: None,
                 _loop=None):
        if not config.loaded:
            config.load()

        self.config = config
        self.app = config.loaded_app
        self.loop = _loop or asyncio.get_event_loop()
        self.limit_concurrency = config.concurrency

        # Global state
        self.host = server

        # Per-connection state
        self.transport = None
        self.counter_ka = config.c_keep_alive
        self.recv_buff = bytes()
        self.server = None
        self.client = None

        self.read_paused = False

    # Protocol interface
    def connection_made(self, transport):
        if len(self.host.connections) >= self.config.concurrency:
            self.shutdown()

        self.host.connections.add(self)
        self.counter_ka = self.config.c_keep_alive
        self.transport = transport
        self.server = get_local_addr(transport)
        self.client = get_remote_addr(transport)

        prefix = "%s:%d - " % tuple(self.client) if self.client else ""

        self.app.made_conn(self)
        logger.info("%sConnection made", prefix)

    def connection_lost(self, exc):
        self.app.lost_conn(self)
        self.host.connections.discard(self)

        prefix = "%s:%d - " % tuple(self.client) if self.client else ""
        logger.info("%sConnection lost", prefix)

    def eof_received(self):
        pass

    def data_received(self, data):
        # reset counter for keep alive
        self.counter_ka = self.config.c_keep_alive
        self.recv_buff += data

        prefix = "%s:%d - " % tuple(self.client) if self.client else ""

        if len(self.recv_buff) >= self.config.reqs_queued:
            # pause reading
            self.transport.pause_reading()
            self.read_paused = True
            logger.info("%sConnection pause reading", prefix)


        try:
            logger.info("%sConnection recv_data=%s", prefix,
                        self.recv_buff.hex())
            self.app.feed_data(self)
        except AppError as e:
            msg = "Invalid frame received: " + str(e.args)
            logger.warning(msg)
            self.transport.close()

    def shutdown(self):
        """
        Called by the server to commence a graceful shutdown.
        """
        self.transport.close()

    def handle_ka(self):
        """
        handle timeout of keep alive
        """
        logger.info("handle ka %d ", self.counter_ka)
        self.counter_ka -= 1
        if self.counter_ka <= 0:
            prefix = "%s:%d - " % tuple(self.client) if self.client else ""
            logger.info("%sConnection alive end", prefix)
            self.shutdown()
