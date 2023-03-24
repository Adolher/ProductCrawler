# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 12:14:47 2023

@author: jpw
"""
import logging

from source.ProxyRotator import ProxyRotator
from source.DefaultLogger import initialize_logger

initialize_logger()
logger = logging.getLogger(__name__)

sites = [
    "http://books.toscrape.com/catalogue/category/books_1/index.html",
    "http://books.toscrape.com/catalogue/category/books/travel_2/index.html",
    "http://books.toscrape.com/catalogue/category/books/mystery_3/index.html",
    "http://books.toscrape.com/catalogue/category/books/historical-fiction_4/index.html",
    "http://books.toscrape.com/catalogue/category/books/sequential-art_5/index.html",
    "http://books.toscrape.com/catalogue/category/books/classics_6/index.html",
    "http://books.toscrape.com/catalogue/category/books/philosophy_7/index.html",
    "http://books.toscrape.com/catalogue/category/books/romance_8/index.html",
    "http://books.toscrape.com/catalogue/category/books/womens-fiction_9/index.html",
    "http://books.toscrape.com/catalogue/category/books/fiction_10/index.html"
    ]

rotator = ProxyRotator()
c = 0
for i in range(1):
    for x in range(len(sites)):
        response = rotator.rotating_requests(sites[x])
