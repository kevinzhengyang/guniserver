# !/usr/bin/python3
# -*-coding:utf-8 -*-
# **********************************************
# @Time     : 2019/12/5 16:26
# @Author   : Kevin Zheng
# @File     : config.py
# @Contact  : 95900021@qq.com
# @Version  : 0.1.0
# @Function : configuration class
# **********************************************
import yaml
import sys
import logging.handlers
import logging.config
import importlib

from guniserver.errors import *


def import_from_string(import_str):
    if not isinstance(import_str, str):
        return import_str

    module_str, _, attrs_str = import_str.partition(":")
    if not module_str or not attrs_str:
        message = (
            'Import string "{import_str}" must be in format "<module>:<attribute>".'
        )
        raise ImportFromStringError(message.format(import_str=import_str))

    try:
        module = importlib.import_module(module_str)
    except ImportError as exc:
        if exc.name != module_str:
            raise exc from None
        message = 'Could not import module "{module_str}".'
        raise ImportFromStringError(message.format(module_str=module_str))

    instance = module
    try:
        for attr_str in attrs_str.split("."):
            instance = getattr(instance, attr_str)
    except AttributeError:
        message = 'Attribute "{attrs_str}" not found in module "{module_str}".'
        raise ImportFromStringError(
            message.format(attrs_str=attrs_str, module_str=module_str)
        )

    return instance


logger = logging.getLogger("guniserver")


class Config:
    def __init__(self,
                 conf: str = 'config.yaml'):
        """
        constructor
        :param conf: yaml configuration file
        """
        # reading config file
        with open(conf, 'r', encoding='utf-8') as f:
            app_config = yaml.safe_load(f)

            self.log_level = app_config['Logging']['log_level']
            self.log_file = app_config['Logging']['log_file']
            self.max_size = app_config['Logging']['max_size'] * 1024 * 1024
            self.back_count = app_config['Logging']['back_count']

            self.host = app_config['Server']['host']
            self.port = app_config['Server']['port']
            self.worker = app_config['Server']['worker']
            self.concurrency = app_config['Server']['concurrency']
            self.reqs_queued = app_config['Server']['reqs_queued'] * 1024
            self.t_keep_alive = app_config['Server']['t_keep_alive']
            self.c_keep_alive = app_config['Server']['c_keep_alive']

            self.app = app_config['Server']['app']

        logging.basicConfig(level=logging.DEBUG,
                            format='[%(asctime)s][%(levelname)s](%(name)s) %(message)s',
                            datefmt='%Y%m%d%H%M%S')
        f_logger = logging.handlers.RotatingFileHandler(self.log_file,
                                                        maxBytes=self.max_size,
                                                        backupCount=self.back_count)
        f_logger.setLevel(self.log_level)
        f_logger.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s](%(name)s) %(message)s'))
        logger.addHandler(f_logger)
        logger.info("Loading conf from %s", conf)
        self.loaded_app = None
        self.loaded = False

    def load(self) -> None:
        """
        load app script
        :return: None
        """
        assert not self.loaded

        try:
            self.loaded_app = import_from_string(self.app)
        except ImportFromStringError as exc:
            logger.error("Error loading ASGI app. %s" % exc)
            sys.exit(1)

        self.loaded = True
