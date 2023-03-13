# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 18:41:18 2023

@author: jpw
"""

from bs4 import BeautifulSoup

from MyDefaultLogger import MyDefaultLogger
from ProxyRotator import ProxyRotator

URLS = ["https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",     # https://docs.proxyscrape.com/
        "https://free-proxy-list.net/"]


class ProxyCrawler():
    def __init__(self, url):
        self.__logger = MyDefaultLogger(__name__)
        self.__rotator = ProxyRotator()
        self.url = url
        self.site = ""
        self.__proxy_list = []

        if "proxyscrape.com" in self.url:
            self.__proxyscrape()
        elif "free-proxy-list.net" in self.url:
            self.__free_proxy_list()

    def __get_site(self):
        self.__logger.info("Send a get request to {0}".format(self.url))
        self.site = self.__rotator.rotating_requests(self.url)
        self.__logger.info("Request successful")

    def __free_proxy_list(self):
        self.__get_site()
        soup = BeautifulSoup(self.site.text, "html.parser")
        x = soup.find("textarea")
        print(x)
        

    def __proxyscrape(self):
        self.__get_site()
        self.__proxy_list = self.site.text.split("\n")
        with open("proxies.txt","w") as f:
            for proxy in self.__proxy_list:
                if not proxy.isspace() and proxy != "":
                    self.__logger.info("Get {0}".format(proxy.strip()))
                    f.write(proxy.strip() + "\n")
        self.__logger.info("Get {0} proxies".format(len(self.__proxy_list)))


if __name__ == "__main__":
    pc = ProxyCrawler(URLS[1])
