# !/usr/bin/python3
# -*-coding:utf-8 -*-
# **********************************************
# @Time     : 2019/12/5 16:26
# @Author   : Kevin Zheng
# @File     : main.py
# @Contact  : 95900021@qq.com
# @Version  : 0.1.0
# @Function : main function
# **********************************************
import sys
sys.path.append('..')
from guniserver.config import Config
from guniserver.server import Server


def main(conf):
    sys.path.insert(0, "..")
    config = Config(conf=conf)
    server = Server(config=config)
    server.run()


if __name__ == "__main__":
    conf_file = sys.argv[1] if (len(sys.argv) > 1) else 'config.yaml'
    main(conf_file)
