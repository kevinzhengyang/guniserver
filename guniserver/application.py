# !/usr/bin/python3
# -*-coding:utf-8 -*-
# **********************************************
# @Time     : 2019/12/5 18:08
# @Author   : Kevin Zheng
# @File     : application.py
# @Contact  : 95900021@qq.com
# @Version  : 0.1.0
# @Function : application upon TCP server
# **********************************************
import logging
from guniserver.errors import *
from typing import Callable

logger = logging.getLogger("guniserver")


class TcpApp:
    """
    TCP application
    """
    def __init__(self):
        self._made_handler = None
        self._recv_handler = None
        self._lost_handler = None

    def recver(self) -> Callable:
        """
        decorator for receiving handler
        """
        def decorate(func):
            assert not self._recv_handler
            self._recv_handler = func
            return func
        return decorate

    def made_conn(self, proto):
        if not self._made_handler:
            return
        self._made_handler(proto)

    def lost_conn(self, proto):
        if not self._lost_handler:
            return
        self._lost_handler(proto)

    def feed_data(self, proto):
        """
        process data received
        :param proto: TCPProtocol object
        """
        if not self._recv_handler:
            raise AppError('cannot find recver')

        buf_len = len(proto.recv_buff)
        size, data = self._recv_handler(proto.recv_buff, proto=proto)

        prefix = "%s:%d - " % tuple(proto.client) if proto.client else ""

        if size <= 0:
            if len(proto.recv_buff) >= proto.config.reqs_queued:
                # reset buff
                proto.recv_buff = bytes()
                proto.read_paused = False
                proto.transport.resume_reading()
                logger.error("%sConnection reset buffer", prefix)
        else:
            if size < buf_len:
                proto.recv_buff = proto.recv_buff[size:]
            else:
                proto.recv_buff = bytes()

            if proto.read_paused:
                # resume reading
                proto.read_paused = False
                proto.transport.resume_reading()
                logger.error("%sConnection resume reading", prefix)

        if data:
            proto.transport.write(data)
