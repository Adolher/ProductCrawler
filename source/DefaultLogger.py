# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 07:37:28 2023

@author: jpw
"""

import os
import json
import inspect
import logging
import logging.config
from datetime import datetime

CONFIG_FILE = "source/config/log_config.json"

# ToDo: #10 create a class wrapper to log class.__init__()
# ToDo: #11 set Docstrings
# ToDo: #23 change RotatingFileHandler to TimedRotatingFileHandler


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


class DebugVerboseAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra, is_class=False):
        super().__init__(logger, extra)
        self.handler_index = [ i for i in range(len(self.logger.root.handlers)) if self.logger.root.handlers[i].name == "debug_verbose_handler"][0]
        self.native_formatter = self.logger.root.handlers[self.handler_index].formatter

        if is_class:
            fmt = "\n{placeholder:+^250}\n{asctime: <24}{levelname: <8}{placeholder:+<218}\n{module_class}\n{placeholder:+^250}\n{placeholder:+^250}\n{processName} {threadName}\n\n{class_str}\n\n"
            self.temp_formatter = logging.Formatter(fmt, style="{")
        else:
            if extra["position"] == "start":
                fmt = "\n{asctime: <24}{levelname: <8}{placeholder:*<168}\n{module_class_function}\n{placeholder:*^200}\n{processName} {threadName}\n\ncalling depth: {calling_depth}\ncalling stack: {way}\n\n-> arguments: {arguments}\n"
                self.temp_formatter = logging.Formatter(fmt, style="{")
            elif extra["position"] == "end":
                self.extra["return_val"] = ('return ' + str(self.extra['return_val'])).center(len('return ' + str(self.extra['return_val'])) + 6).center(200, '^')
                fmt = "\nelapsed time: {elapsed}\n{return_val}\n{placeholder:^^200}\n"
                self.temp_formatter = logging.Formatter(fmt, style="{")

    def send_log(self, msg):
        self.logger.root.handlers[self.handler_index].setFormatter(self.temp_formatter)
        self.debug(msg)
        self.logger.root.handlers[self.handler_index].setFormatter(self.native_formatter)


class DebugVervoseClassWrapper():
    def __init__(self, wrapped_class) -> None:
        print("DebugVervoseClassWrapper.__init__() >> start")
        self.wrapped_class = wrapped_class
        print("DebugVervoseClassWrapper.__init__() >> end\n")

    def __call__(self, *args, **kwargs):
        print("DebugVervoseClassWrapper.__call__() >> start")
        self.wrapped_class.logger = logging.getLogger(self.wrapped_class.__module__)
        self.wrapped_class = self.wrapped_class(*args, **kwargs)

        module_class = str(self.wrapped_class.__module__).center(len(str(self.wrapped_class.__module__)) + 6, ' ').center(250, '+')
        extra = {"module_class": module_class,"class_str": self.wrapped_class.__str__(), "placeholder": ""}

        adapt_logger = DebugVerboseAdapter(self.wrapped_class.logger, extra, is_class=True)
        adapt_logger.send_log(f"arguments: {self.wrapped_class.__repr__()}")
        
        
        
        print("DebugVervoseClassWrapper.__call__() >> end\n")
        return self.wrapped_class


def debug_verbose(func):
    sig = inspect.signature(func)

    def debug_wrapper(self, *args, **kwargs):   # ToDo: #18 make debug_wrapper thread save
        
        if self.logger.isEnabledFor(10):
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            
            recurs_stack = inspect.getouterframes(inspect.currentframe())
            recurs_stack.reverse()
            calling_depth = len(recurs_stack)

            way = ""
            for rs in recurs_stack:
                if "debug" in rs[3] or rs == recurs_stack[-1]:
                    calling_depth -= 1
                    continue
                else:
                    way += f"in {rs[3]} [line: {rs[2]}] -> {rs[4][0].strip()} >>> "
            way = way[:-5] if way.endswith(">>> ") else way

            module_name = inspect.getmodule(func).__name__
            qname = func.__qualname__
            module_class_function = (module_name + "." + qname).center(len(str(module_name + "." + qname)) + 6, ' ').center(200, '*')

            extra = {"position": "start", "module_class_function": module_class_function,
                    "calling_depth": calling_depth, "way": way, "arguments": bound.arguments, "placeholder": ""}

            adapt_logger = DebugVerboseAdapter(self.logger, extra)
            adapt_logger.send_log(f"arguments: {bound.arguments}")

            start = datetime.now()
            return_val = func(self, *args, **kwargs)
            end = datetime.now()

            extra = {"position":"end", "return_val":return_val, "elapsed":end - start, "placeholder": ""}

            adapt_logger = DebugVerboseAdapter(self.logger, extra)
            adapt_logger.send_log(f"return {return_val}")
        else:
            return_val = func(self, *args, **kwargs)

        return return_val

    return debug_wrapper
