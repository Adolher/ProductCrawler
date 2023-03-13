# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 07:37:28 2023

@author: jpw
"""

import logging
import sys
import os

LOG_LEVEL = "DEBUG"
LOG_FILE = "log_proxy_rotator.txt"


class MyDefaultLogger(logging.Logger):
    def __init__(self, name, level=LOG_LEVEL, log_file_name=LOG_FILE):
        super().__init__(self)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        stream_handler = logging.StreamHandler(sys.stdout)
        file_handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), log_file_name), encoding="utf-8")

        format_string = "[{0}] {1:20} {2} {3} [{4}]".format('%(asctime)s', '%(levelname)s', '%(module)s', '%(funcName)s', '%(message)s')
        formatter = logging.Formatter(format_string)      #'[%(asctime)s] %(levelname)s %(module)s %(funcName)s [%(message)s]')      # format the output -> levelname
        stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)
