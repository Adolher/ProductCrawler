# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 07:37:28 2023

@author: jpw
"""

import json
import inspect
import logging
import logging.config
from datetime import datetime

CONFIG_FILE = "source/config/log_config.json"

# ToDo: #10 create a class wrapper to log class.__init__()
# ToDo: #11 set Docstrings
# ToDo: #23 change RotatingFileHandler to TimedRotatingFileHandler

class DebugVerboseAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra):
        super().__init__(logger, extra)
        self.handler_index = [ i for i in range(len(self.logger.root.handlers)) if self.logger.root.handlers[i].name == "debug_verbose_handler"][0]
        self.temp_formatter = logging.Formatter("%(message)s")
        self.native_formatter = self.logger.root.handlers[self.handler_index].formatter
        self.levelname = logging.getLevelName(self.logger.getEffectiveLevel())

    def __get_verbose_msg(self, position):
        if position == "start":
            start_v_msg = f"\n%s\n%s\n%s\n\ncalling depth -> %s\ncalling stack -> %s\n\n -> arguments: %s\n" % (
                self.levelname.ljust(len(self.levelname) + 3, ' ').ljust(200, '*'),
                str(self.extra['qname']).center(len(str(self.extra['qname'])) + 6, ' ').center(200, '*'),
                str(self.extra["time"]).ljust(len(str(self.extra["time"])) + 3, ' ').ljust(200, '*'),
                self.extra["calling_depth"], self.extra["way"], self.extra["arguments"],
            )
            return start_v_msg
        elif position == "end":
            end_v_message = f"\nelapsed time: {self.extra['elapsed']}\n" \
              f"{('return ' + str(self.extra['return_val'])).center(len('return ' + str(self.extra['return_val'])) + 6).center(200, '^')}\n{200 * '^'}\n"
            return end_v_message

    def send_log(self):
        self.logger.root.handlers[self.handler_index].setFormatter(self.temp_formatter)
        self.debug("")
        self.logger.root.handlers[self.handler_index].setFormatter(self.native_formatter)

    def process(self, msg, kwargs):
        return self.__get_verbose_msg(self.extra['position']), kwargs


def initialize_logger():
    logging.basicConfig()
    log = logging.getLogger()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
            config = json.load(cf)
            logging.config.dictConfig(config["dev_logger"])     # ToDo: #19 work on formats -> in all Formatters the same informations but in diffrent format
    except FileNotFoundError as e:
        log.error(e)
    return log


def debug_verbose(func):    # ToDo: #12 set wrapper-function debug_verbose() as staticmethod of class DebugVerboseAdapter
    sig = inspect.signature(func)

    def debug_wrapper(self, *args, **kwargs):   # ToDo: #18 make debug_wrapper thread save

        bound = sig.bind(self, *args, **kwargs)
        bound.apply_defaults()
        calling_depth = len(inspect.getouterframes(inspect.currentframe()))
        recurs_stack = inspect.getouterframes(inspect.currentframe())   # ToDo: #8 try to replace '<module>' with module_name
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
