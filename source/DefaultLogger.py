# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 07:37:28 2023

@author: J.P. Wagner


This module is created to make debug logging more comfortable. You just need to wrap your classes, methods or functions and you'll get your debug-informations.

Classes:
    DebugClassWrapper():
        __init__(self, wrapped_class: object) -> None
        __call__(self, *args, **kwargs) -> object
        debug_method_wrapper(func: object) -> object
        
    DebugAdapter(logging.LoggerAdapter):
        __init__(self, logger: logging.Logger, extra: dict) -> None
        process(self, msg: str, kwargs: dict) -> tuple

Functions:
    initialize_logger() -> logging.Logger
    __std_out_filter(level: int) -> object
    __std_err_filter(level: int) -> object

"""

import json
import inspect
import logging
import logging.config
from datetime import datetime

CONFIG_FILE = "source/config/log_config.json"

# ToDo: #23 change RotatingFileHandler to TimedRotatingFileHandler


def initialize_logger() -> logging.Logger:
    """
    
    Initializes a basic Logger according to the data in config/log_config.json
    Call this function first of all after import statements
    It will be not necessary to import the logging module
    
    Example:
        from DefaultLogger import initialize_logger
        
        logger = initialize_logger()
        
        logger.debug("This is a debug message")
        logger.info("This is a info message")

    Returns:
        logging.Logger: RootLogger
    """
    logging.basicConfig()
    log = logging.getLogger()
    log = DebugAdapter(log, {})

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as cf:
            config = json.load(cf)
            logging.config.dictConfig(config["dev_logger"])
    except FileNotFoundError as e:
        log.error(e)
    return log


class DebugClassWrapper():
    """DebugClassWrapper is used to get debug informations without mulling the methods with 'logging.debug()' calls.
    
    Usage:
        from DefaultLogger import DebugClassWrapper
        
        @DebugClassWrapper
        class MyClass:
            def __init__(self):
                ...
            
            @DebugClassWrapper.debug_method_wrapper
            def method(self):
                ...
    Attributes:
        wrapped_class: object
        
    Methods:
        debug_method_wrapper(func)

    """
    def __init__(self, wrapped_class: object) -> None:
        self.wrapped_class = wrapped_class

    def __call__(self, *args, **kwargs) -> object:
        self.wrapped_class.logger = logging.getLogger(self.wrapped_class.__module__)
        self.wrapped_class.logger = DebugAdapter(self.wrapped_class.logger, {})
        
        self.wrapped_class = self.wrapped_class(*args, **kwargs)

        self.wrapped_class.logger.debug(f"arguments: {self.wrapped_class.__repr__()}", extra={"c_func_name":self.wrapped_class.__module__, "position": "initial "})
        return self.wrapped_class

    @staticmethod
    def debug_method_wrapper(func: object) -> object:
        """debug_method_wrapper is used to get debug informations without mulling the methods with 'logging.debug()' calls.
        
        Usage:
            from DefaultLogger import DebugClassWrapper
            
            @DebugClassWrapper
            class MyClass:
                def __init__(self):
                    ...
                
                @DebugClassWrapper.debug_method_wrapper
                def method(self):
                    ...
        """
        sig = inspect.signature(func)

        def debug_wrapper(self, *args, **kwargs):   # ToDo: #18 make debug_wrapper thread save
            
            if self.logger.isEnabledFor(10):
                bound = sig.bind(self, *args, **kwargs)
                bound.apply_defaults()

                module_name = inspect.getmodule(func).__name__
                qname = func.__qualname__
                name = (module_name + "." + qname)

                self.logger.debug(f"arguments: {bound.arguments}", extra={"position": "enter ", "c_func_name": name})

                start = datetime.now()
                return_val = func(self, *args, **kwargs)
                end = datetime.now()

                self.logger.debug(f"return {return_val}", extra={"time_info":str(end - start), "position":"exit ", "c_func_name": name})
            else:
                return_val = func(self, *args, **kwargs)

            return return_val

        return debug_wrapper


class DebugAdapter(logging.LoggerAdapter):
    def __init__(self, logger: logging.Logger, extra: dict) -> None:
        super().__init__(logger, extra)
    
    def process(self, msg: str, kwargs: dict) -> tuple:
        kwargs["extra"] = {} if "extra" not in kwargs.keys() else kwargs["extra"]
        kwargs["extra"]["time_info"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f") if "time_info" not in kwargs['extra'].keys() else kwargs["extra"]["time_info"]
        kwargs["extra"]["position"] = "in " if "position" not in kwargs["extra"].keys() else kwargs["extra"]["position"]
        kwargs["extra"]["c_func_name"] = "" if "c_func_name" not in kwargs["extra"].keys() else kwargs["extra"]["c_func_name"] + " enbedded in "
        return msg, kwargs


def __std_out_filter(level: int) -> object:
    level = getattr(logging, level)

    def filter(record):
        return record.levelno <= level

    return filter


def __std_err_filter(level: int) -> object:
    level = getattr(logging, level)

    def filter(record):
        return record.levelno >= level

    return filter
