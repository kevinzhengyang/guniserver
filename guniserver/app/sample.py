# !/usr/bin/python3
# -*-coding:utf-8 -*-
# **********************************************
# @Time     : 2019/12/6 17:30
# @Author   : Kevin Zheng
# @File     : sample.py
# @Contact  : 95900021@qq.com
# @Version  : 
# @Function :
# **********************************************
import logging
from guniserver.application import TcpApp

logger = logging.getLogger("guniserver")
sapp = TcpApp()


@sapp.recver()
def _(recv_buff, proto=None):
    size = len(recv_buff)
    logger.debug('sample receiver processing...')
    if size > 4:
        data = recv_buff[0:]
        return size, data
    else:
        logger.debug('size is %d', size)
        return 0, None
