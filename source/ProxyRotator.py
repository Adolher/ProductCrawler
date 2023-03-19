# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 06:41:59 2023

@author: jpw
"""
import queue
import logging
import requests
import threading
from source.DefaultLogger import debug_verbose
from requests.exceptions import RequestException, ProxyError, ConnectionError, Timeout, ContentDecodingError, \
    TooManyRedirects

# ToDo: #22 set docstrings

class ProxyRotator:
    def __init__(self, num_threads=50, start_timeout=4, max_timeout=32, proxies_file="proxies.txt", valid_proxies_file="valid_proxies.txt", accepted_bad_proxy_quote=0.5, min_valid_proxies=20):
        self.logger = logging.getLogger(__name__)
        self.__unchecked_proxies = queue.Queue()
        self.__valid_proxies = []
        self.__bad_valid_proxies = 0
        self.__request_counter = 1
        self.__min_valid_proxies = min_valid_proxies
        self.__accepted_bad_proxy_quote = accepted_bad_proxy_quote
        self.__threads = num_threads
        self.__start_timeout = start_timeout
        self.__max_timeout = max_timeout
        self.__proxies_file = proxies_file
        self.__valid_proxies_file = valid_proxies_file

        self.__urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",     # https://docs.proxyscrape.com/
            "https://free-proxy-list.net/"]

        if not self.__read_valid_proxies():
            self.__get_proxies()

    @debug_verbose  # ToDo: #13 use wrapper with conditions?
    def __get_proxies(self, under_min=False) -> None:  # done
        try:
            if under_min:
                self.logger.info("Fetch new proxy lists from internet.")
                proxies = self.__get_sites()
            else:
                self.logger.info("try reading proxies from {0}".format(self.__proxies_file))
                with open(self.__proxies_file, "r") as f:
                    proxies = f.read().split("\n")
        except FileNotFoundError:
            self.logger.warning(f"{0} does not exists! Fetch proxy lists from internet.".format(self.__proxies_file))
            proxies = self.__get_sites(own_ip=True)
            # ToDo: #20 save proxies in file

        self.logger.info(f"get {len(proxies)} proxies")
        for i in range(len(proxies) - 1):
            self.__unchecked_proxies.put(proxies[i])
        self.__threaded_validating()
        if len(self.__valid_proxies) < self.__min_valid_proxies:
            self.__get_proxies(under_min=True)

    @debug_verbose
    def __validate_proxies(self, timeout) -> None:
        while not self.__unchecked_proxies.empty():
            proxy = self.__unchecked_proxies.get()
            try:
                response = requests.get("http://ipinfo.io/json",
                                        proxies={"http": proxy,
                                                 "https": proxy},
                                        headers={
                                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'},
                                        timeout=timeout
                                        )
                if response.status_code == requests.codes.ok and response.text is not None:
                    text = response.json()
                    self.__valid_proxies.append(proxy)
                    self.logger.info("added {0:25s} {1} in {2}".format(proxy, response.status_code, text["country"]))
                else:
                    self.logger.info("      {0:25s} {1} {2}".format(proxy, response.status_code, response.reason))
            except ProxyError:
                self.logger.error("      {0:25s} ProxyError".format(proxy))
            except Timeout:
                self.logger.error("      {0:25s} Timeout (timeout={1})".format(proxy, timeout))
                if timeout < self.__max_timeout:
                    self.__validate_proxies(timeout=(timeout * 2))
            except ConnectionError:
                self.logger.error("      {0:25s} ConnectionError".format(proxy))
            except RequestException as e:
                self.logger.error(e)

    @debug_verbose
    def __threaded_validating(self) -> None:
        self.logger.info("start validating proxies")
        ths = []
        x = threading.active_count()
        for _ in range(self.__threads):
            t = threading.Thread(target=self.__validate_proxies, args=(self.__start_timeout,))
            ths.append(t)
            t.start()
        for thd in ths:
            thd.join()
        self.logger.info(f"found {len(self.__valid_proxies)} valid proxies")
        self.__save_valid_proxies()

    @debug_verbose
    def __save_valid_proxies(self) -> None:
        self.logger.info("save valid proxies to {0}".format(self.__valid_proxies_file))
        with open(self.__valid_proxies_file, "w") as f:
            for proxy in self.__valid_proxies:
                f.write(proxy + "\n")
        self.logger.info("{0} valid proxies were saved".format(len(self.__valid_proxies)))

    @debug_verbose
    def __read_valid_proxies(self) -> bool:
        self.logger.info("Try to read {0}".format(self.__valid_proxies_file))
        try:
            with open(self.__valid_proxies_file, "r") as f:
                self.__valid_proxies = f.read().split()
            self.logger.info("get {0} valid proxies".format(len(self.__valid_proxies)))
            return True
        except FileNotFoundError:
            self.logger.error("{0} does not exist".format(self.__valid_proxies_file))
            return False

    @debug_verbose
    def rotating_requests(self, url, timeout=None, proxy=True, index=0) -> requests.Response:
        def error_handling(name, index):
            self.logger.error(
                "proxy {0:25s} ERROR {1} (bad proxies: {2} / valid proxies: {3})".format(self.__valid_proxies[index],
                                                                                         name, self.__bad_valid_proxies,
                                                                                         len(self.__valid_proxies)))
            self.__valid_proxies.pop(index)
            self.__bad_valid_proxies += 1
            if float(self.__bad_valid_proxies) / len(self.__valid_proxies) > self.__accepted_bad_proxy_quote:
                self.__get_proxies()

        if not timeout:
            timeout = self.__start_timeout
        if index != 0:
            proxies = {"http": self.__valid_proxies[index], "https": self.__valid_proxies[index]}
        elif proxy:
            index += self.__request_counter % (len(self.__valid_proxies) - 1)
            proxies = {"http": self.__valid_proxies[index], "https": self.__valid_proxies[index]}
        else:
            proxies = None

        try:
            if proxy:
                self.logger.info("request via proxy {0:25s} to {1} timeout={2:2d}".format(str(proxies), url, timeout))
            self.__request_counter += 1
            response = requests.get(url,
                                    proxies=proxies,
                                    headers={
                                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'},
                                    timeout=timeout
                                    )
            return response
        except Timeout:
            self.logger.error("proxy {0:25s} Timeout (timeout={1})".format(self.__valid_proxies[index], timeout))
            if timeout < self.__max_timeout:
                return self.rotating_requests(url, timeout + 3, proxy, index)
            else:
                return self.rotating_requests(url, timeout, proxy)
        except ContentDecodingError:
            error_handling("ContentDecodingError", index)
            return self.rotating_requests(url, timeout, proxy, index)
        except TooManyRedirects:
            error_handling("TooManyRedirects", index)
            return self.rotating_requests(url, timeout, proxy, index)
        except ConnectionError:
            error_handling("ConnectionError", index)
            return self.rotating_requests(url, timeout, proxy, index)

    @debug_verbose
    def __get_sites(self, own_ip=False) -> list:
        if own_ip:
            self.logger.warning("!!!WARNING!!! REQUEST WITH YOUR OWN IP !!!WARNING!!!")
            # ToDo: #16 write a describing message
            confirm = False if input("Do you agree with it? ( y / [n] )") != "y" else True
            if not confirm:
                exit()
        proxies = []

        for url in self.__urls:
            self.logger.info("Send a get request to {0}".format(url))
            if "proxyscrape.com" in url:
                response = self.rotating_requests(url, proxy=not own_ip)
                proxies.extend(self.__proxyscrape(response.text))
            elif "free-proxy-list.net" in url:
                response = self.rotating_requests(url, proxy=not own_ip)
                proxies.extend(self.__free_proxy_list(response.text))
            # ToDo: #17 clean proxies from duplicates
            self.logger.info("Request successful")

        return proxies

    # def __free_proxy_list(self, html):    # ToDo: #15 finish this method
    #     proxies_fpl = []
    #     soup = BeautifulSoup(html, "html.parser")
    #     x = soup.find("textarea")
    #     return proxies_fpl

    def __proxyscrape(self, text) -> requests.Response:     # ToDo: finish this method
        self.__proxy_list = text.split("\r\n")
        with open("proxies.txt", "w") as f:  # ToDo: #14 exception handling!!!
            for proxy in self.__proxy_list:
                self.logger.info("Get {0}".format(proxy))
                f.write(proxy + "\n")
        self.logger.info("Get {0} proxies".format(len(self.__proxy_list)))


if __name__ == "__main__":
    pr = ProxyRotator()
