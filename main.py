# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 12:14:47 2023

@author: jpw
"""

from MyDefaultLogger import MyDefaultLogger
from ProxyRotator import ProxyRotator

LOG_LEVEL = "DEBUG"
LOG_FILE = "log_proxy_rotator.txt"

logger = MyDefaultLogger(__name__, LOG_LEVEL, LOG_FILE)

rotator = ProxyRotator()

sites = [
    "http://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    "http://books.toscrape.com/catalogue/category/books/mystery_3/index.html",
    "http://books.toscrape.com/catalogue/category/books/historical-fiction_4/index.html",
    "http://books.toscrape.com/catalogue/category/books/sequential-art_5/index.html",
    "http://books.toscrape.com/catalogue/category/books/classics_6/index.html",
    "http://books.toscrape.com/catalogue/category/books/philosophy_7/index.html",
    "http://books.toscrape.com/catalogue/category/books/romance_8/index.html",
    "http://books.toscrape.com/catalogue/category/books/womens-fiction_9/index.html",
    ]


l = []

for site in sites:
    response = rotator.rotating_requests(site)
    if response:
        print(response.status_code)
