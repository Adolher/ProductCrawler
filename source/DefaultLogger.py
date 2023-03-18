# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 07:37:28 2023

@author: jpw
"""

import inspect
import json
import logging
import logging.config
from datetime import datetime

CONFIG_FILE = "source/config/log_config.json"


class DebugVerboseAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra):
        super().__init__(logger, extra)
        self.temp_formatter = logging.Formatter("%(message)s")
        self.native_formatter = logging.Formatter("%(levelname)-8s at %(processName)s %(threadName)s in %(name)s.%(module)s.%(funcName)s line %(lineno)d -> %(message)s")
        self.levelname = logging.getLevelName(self.logger.getEffectiveLevel())

    def __get_verbose_msg(self, position, msg):
        if position == "start":
            start_v_msg = f"\n%s\n%s\n%s\n\ncalling depth -> %s\ncalling stack -> %s\n\n -> arguments: %s\n%s" % (
                self.levelname.ljust(len(self.levelname) + 3, ' ').ljust(200, '*'),
                str(self.extra['qname']).center(len(str(self.extra['qname'])) + 6, ' ').center(200, '*'),
                str(self.extra["time"]).ljust(len(str(self.extra["time"])) + 3, ' ').ljust(200, '*'),
                self.extra["calling_depth"], self.extra["way"], self.extra["arguments"], msg
            )
            return start_v_msg
        elif position == "end":
            end_v_message = f"\nelapsed time: {self.extra['elapsed']}\n" \
              f"{('return ' + str(self.extra['return_val'])).center(len('return ' + str(self.extra['return_val'])) + 6).center(200, '^')}\n{200 * '^'}\n"
            return end_v_message

    def send_log(self):
        self.logger.root.handlers[2].setFormatter(self.temp_formatter)
        self.debug("")
        self.logger.root.handlers[2].setFormatter(self.native_formatter)

    def process(self, msg, kwargs):
        return self.__get_verbose_msg(self.extra['position'], msg), kwargs


def initialize_logger():
    logging.basicConfig()
    log = logging.getLogger()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
            config = json.load(cf)
            logging.config.dictConfig(config["dev_logger"])
    except FileNotFoundError as e:
        log.error(e)
    return log


def debug_verbose(func):
    sig = inspect.signature(func)

    def debug_wrapper(self, *args, **kwargs):

        bound = sig.bind(self, *args, **kwargs)
        bound.apply_defaults()
        calling_depth = len(inspect.getouterframes(inspect.currentframe()))
        recurs_stack = inspect.getouterframes(inspect.currentframe())
        way = [f"{rs[3]} >> " for rs in recurs_stack]
        way.append(f"{func.__name__}")

        extra = {"position": "start", "qname": func.__qualname__, "time": str(datetime.now()),
                 "calling_depth": calling_depth, "way": way, "arguments": bound.arguments}

        adapt_logger = DebugVerboseAdapter(self.logger, extra)

        adapt_logger.send_log()

        start = datetime.now()
        return_val = func(self, *args, **kwargs)
        end = datetime.now()

        extra["return_val"] = return_val
        extra["elapsed"] = end - start
        extra["position"] = "end"

        adapt_logger.send_log()

        return return_val

    return debug_wrapper


def std_out_filter(level):
    level = getattr(logging, level)

    def filter(record):
        return record.levelno <= level

    return filter


def std_err_filter(level):
    level = getattr(logging, level)

    def filter(record):
        return record.levelno >= level

    return filter
