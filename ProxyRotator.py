# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 06:41:59 2023

@author: jpw
"""
import requests
import queue
import threading

from MyDefaultLogger import MyDefaultLogger

LOG_LEVEL = "DEBUG"
LOG_FILE = "log_proxy_rotator.txt"
PROXY_FILE = "proxies.txt"
THREADS = 50
TIMEOUT = 2


class ProxyRotator():
    def __init__(self):
        self.logger = MyDefaultLogger(__name__, LOG_LEVEL, LOG_FILE).logger
        self.unchecked_proxies = queue.Queue()
        self.valid_proxies = []
        self.threads = THREADS
        self.counter = 1

        self.__get_proxies()
        self.__threaded_validating()

    def __get_proxies(self):
        with open(PROXY_FILE, "r") as f:
            proxies = f.read().split("\n")
        self.logger.info(f" get {len(proxies)} proxies from {PROXY_FILE}")
        for proxy in proxies:
            self.unchecked_proxies.put(proxy)

    def __validate_proxies(self):
        while not self.unchecked_proxies.empty():
            proxy = self.unchecked_proxies.get()
            try:
                response = requests.get("http://ipinfo.io/json",
                                        proxies={"http": proxy,
                                                 "https": proxy},
                                        timeout=TIMEOUT
                                        )
                if response.status_code == requests.codes.ok:
                    self.logger.info("{0:20s} added to valid proxy Queue".format(proxy))
                    self.valid_proxies.append(proxy)
                else:
                    self.logger.info("{0:20s} is not reachable".format(proxy))
            except:
                continue

    def __threaded_validating(self):
        ths = []
        x = threading.active_count()
        for _ in range(self.threads):
            t = threading.Thread(target=self.__validate_proxies)
            ths.append(t)
            t.start()
        self.logger.debug("{0:3d} threads are running".format(threading.active_count()-x))
        for thd in ths:
            thd.join()
        self.logger.debug("--> Validating-Threads are joined <--")

    def rotating_requests(self, url):
        index = self.counter % len(self.valid_proxies)
        self.counter += 1
        try:
            response = requests.get(url,
                                    proxies={"http": self.valid_proxies[index],
                                             "https": self.valid_proxies[index]},
                                    timeout=TIMEOUT
                                    )
            self.logger.info("via proxy {0:20s} request {1}".format(self.valid_proxies[index], url))
            return response
        except Exception as e:
            return None


if __name__ == "__main__":
    pr = ProxyRotator()
