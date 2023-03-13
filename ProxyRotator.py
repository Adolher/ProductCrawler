# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 06:41:59 2023

@author: jpw
"""
import requests
from requests.exceptions import RequestException, ProxyError, ConnectionError, Timeout
import queue
import threading
import json
from bs4 import BeautifulSoup

from MyDefaultLogger import MyDefaultLogger


class ProxyRotator():
    def __init__(self, num_threads=50, start_timeout=4, max_timeout=32, proxies_file="proxies.txt", valid_proxies_file="valid_proxies.txt", accepted_bad_proxy_quote=0.5, min_valid_proxies=20):
        self.__logger = MyDefaultLogger(__name__).logger
        self.__unchecked_proxies = queue.Queue()
        self.__valid_proxies = []

        self.__counter = 1
        self.__min_valid_proxies = min_valid_proxies
        self.__accepted_bad_proxy_quote = accepted_bad_proxy_quote
        self.__threads = num_threads
        self.__start_timeout = start_timeout
        self.__max_timeout = max_timeout
        self.__proxies_file = proxies_file
        self.__valid_proxies_file = valid_proxies_file

        self.__urls = ["https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",     # https://docs.proxyscrape.com/
                       "https://free-proxy-list.net/"]
        

        if not self.__read_valid_proxies():
            self.__get_proxies()

    def __get_proxies(self, under_min=False):
        try:
            if under_min:
                proxies = self.__get_sites()
            else:
                self.__logger.info("try reading proxies from {0}".format(self.__proxies_file))
                with open(self.__proxies_file, "r") as f:
                    proxies = f.read().split("\n")
        except FileNotFoundError:
            proxies = self.__get_sites(own=True)
        self.__logger.info(f"get {len(proxies)} proxies")
        for proxy in proxies:
            self.__unchecked_proxies.put(proxy)
        self.__threaded_validating()
        if len(self.__valid_proxies) < self.__min_valid_proxies:
            self.__get_proxies()
        for proxy in proxies:
            self.__unchecked_proxies.put(proxy)
        self.__save_valid_proxies()
        

    def __validate_proxies(self, timeout):
        self.__logger.info("Start proxy validation.")
        while not self.__unchecked_proxies.empty():
            proxy = self.__unchecked_proxies.get()
            try:
                response = requests.get("http://ipinfo.io/json",
                                        proxies={"http": proxy,
                                                 "https": proxy},
                                        headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'},
                                        timeout=timeout
                                        )
                if response.status_code == requests.codes.ok and response.text is not None:
                    text = json.loads(response.text)
                    self.__valid_proxies.append(proxy)
                    self.__logger.info("added {0:25s} {1} in {2}".format(proxy, response.status_code, text["country"]))
                else:
                    self.__logger.info("      {0:25s} {1} {2}".format(proxy, response.status_code, response.reason))
            except ProxyError:
                self.__logger.error("      {0:25s} ProxyError (Cannot connect to proxy.)".format(proxy))
            except Timeout:
                self.__logger.error("      {0:25s} Timeout (timeout={1})".format(proxy, timeout))
                if timeout < self.__max_timeout:
                    self.__validate_proxies(timeout=(timeout*2))
            except ConnectionError:
                self.__logger.error("      {0:25s} ConnectionError (Eine vorhandene Verbindung wurde vom Remotehost geschlossen.)".format(proxy))
            except RequestException as e:
                self.__logger.error(e)

    def __threaded_validating(self):
        self.__logger.info("start validating proxies")
        ths = []
        x = threading.active_count()
        for _ in range(self.__threads):
            t = threading.Thread(target=self.__validate_proxies, args=(self.__start_timeout,))
            ths.append(t)
            t.start()
        self.__logger.debug("{0:3d} threads are running".format(threading.active_count()-x))
        for thd in ths:
            thd.join()
        self.__logger.info(f"found {len(self.__valid_proxies)} valid proxies")
        

    def __save_valid_proxies(self):
        self.__logger.info("save valid proxies to {0}".format(self.__valid_proxies_file))
        with open(self.__valid_proxies_file,"w") as f:
            for proxy in self.__valid_proxies:
                f.write(proxy + "\n")
        self.__logger.info("{0} valid proxies were saved".format(len(self.__valid_proxies)))
        
    def __read_valid_proxies(self):
        self.__logger.info("Try to read {0}".format(self.__valid_proxies_file))
        try:
            with open(self.__valid_proxies_file,"r") as f:
                self.__valid_proxies = f.read().split()
            self.__logger.info("get {0} valid proxies".format(len(self.__valid_proxies)))
            return True
        except FileNotFoundError:
            self.__logger.error("{0} does not exist".format(self.__valid_proxies_file))
            return False

    def rotating_requests(self, url, timeout=None, proxy=True):
        index = self.__counter % len(self.__valid_proxies)
        
        timeout = self.__start_timeout if not timeout else None
        proxy = self.__valid_proxies[index] if proxy else None

        self.__logger.info("proxy {0:25s} timeout={2:2d} request {1}".format(proxy, url, timeout))
        self.__counter += 1
        try:
            response = requests.get(url,
                                    proxies={"http": proxy,
                                             "https": proxy},
                                    headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'},
                                    timeout=timeout
                                    )
            return response
        except Timeout:
            self.__logger.error("Timeout (timeout={0})".format(timeout))
            if timeout < self.__max_timeout:
                return self.rotating_requests(url, timeout*2)
        except ProxyError:
            self.__valid_proxies.pop(index)
            self.__bad_valid_proxies += 1
            self.__logger.error("ProxyError (bad proxies: {0} valid proxies: {1})".format(self.__bad_valid_proxies, len(self.__valid_proxies)))
            if float(self.__bad_valid_proxies)/len(self.__valid_proxies) > self.__accepted_bad_proxy_quote:
                self.__get_proxies()
            return self.rotating_requests(url, timeout)
        
    def __get_sites(self, own=False):
        if own:
            self.__logger.warning("!!!WARNING!!! REQUEST WITH YOUR OWN IP !!!WARNING!!!")
            confirm = False if input("Do you agree with it? ( y / [n] )") != "y" else True
            if not confirm: exit()
        proxies = []
        
        for url in self.__urls:
            self.__logger.info("Send a get request to {0}".format(url))
            if "proxyscrape.com" in url:
                response = self.rotating_requests(url, proxy=False)
                proxies.extend(self.__proxyscrape(response.text))
            elif "free-proxy-list.net" in url:
                response = self.rotating_requests(url, proxy=False)
                proxies.extend(self.__free_proxy_list(response.text))
            self.__logger.info("Request successful")

        return proxies


-    def __free_proxy_list(self, html):
        proxies_fpl = []
        soup = BeautifulSoup(html, "html.parser")
        x = soup.find("textarea")
        return proxies_fpl
        

-    def __proxyscrape(self, html):
        self.__proxy_list = html.split("\n")
        with open("proxies.txt","w") as f:
            for proxy in self.__proxy_list:
                if not proxy.isspace() and proxy != "":
                    self.__logger.info("Get {0}".format(proxy.strip()))
                    f.write(proxy.strip() + "\n")
        self.__logger.info("Get {0} proxies".format(len(self.__proxy_list)))


if __name__ == "__main__":
    pr = ProxyRotator()
