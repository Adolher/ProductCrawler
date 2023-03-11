# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 07:37:28 2023

@author: jpw
"""

import logging
import sys
import os


class MyDefaultLogger(logging.Logger):
    def __init__(self, name, level, log_file_name):
        super().__init__(self)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        stream_handler = logging.StreamHandler(sys.stdout)
        file_handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), log_file_name))

        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(module)s %(funcName)s [%(message)s]')
        stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)
