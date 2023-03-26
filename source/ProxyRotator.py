# -*- coding: utf-8 -*-
"""
Created on Sat Mar 11 06:41:59 2023

@author: jpw
"""
import os
import queue
import requests
import threading
from source.DefaultLogger import DebugVervoseClassWrapper, debug_verbose
from requests.exceptions import RequestException, ProxyError, ConnectionError, Timeout, ContentDecodingError, \
    TooManyRedirects

NUM_THREADS = 1
START_TIMEOUT = (5,3)
MAX_TIMEOUT = 5
ACCEPTED_BAD_PROXY_QUOTE = 0.5
MIN_VALID_PROXIES = 5
PROXIES_FILE = "proxies"
VALID_PROXIES_FILE = "valid_proxies"

# ToDo: #22 set docstrings
# ToDo: #26 create an API to configure the const values
# ToDo: #27 read and save const values from/ to .ini

@DebugVervoseClassWrapper
class ProxyRotator:
    def __init__(self, num_threads=NUM_THREADS, start_timeout=START_TIMEOUT, max_timeout=MAX_TIMEOUT, proxies_file=PROXIES_FILE, valid_proxies_file=VALID_PROXIES_FILE, accepted_bad_proxy_quote=ACCEPTED_BAD_PROXY_QUOTE, min_valid_proxies=MIN_VALID_PROXIES):
        self.__min_valid_proxies = min_valid_proxies
        self.__accepted_bad_proxy_quote = accepted_bad_proxy_quote
        self.__threads = num_threads
        self.__start_timeout = start_timeout
        self.__max_timeout = max_timeout
        self.__proxies_file = proxies_file
        self.__valid_proxies_file = valid_proxies_file

        self.__valid_proxies_index = 0
        self.__bad_proxies = 0
        self.__request_counter = 0

        self.__check_pool = False

        self.__unchecked_proxies = []
        self.__unchecked_proxies_queue = queue.Queue()
        self.__valid_proxies = []

        self.__urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",     # https://docs.proxyscrape.com/
            "https://free-proxy-list.net/"]

    
    def __str__(self) -> str:   # ToDo: #31 write __str__()
        string = ""

        return string
    
    def __repr__(self) -> str:  # ToDo: #32 write __repr__()
        string = ""

        return string

    @debug_verbose
    def rotating_requests(self, url, proxy=True, timeout=None) -> requests.Response:
        def error_handling(name, index):
            self.__bad_proxies += 1
            self.logger.error(
                "{0:>17} {1:25s} ERROR {2} (bad proxies: {3} / valid proxies: {4})".format("proxy", self.__valid_proxies[index],
                                                                                         name, self.__bad_proxies,
                                                                                         len(self.__valid_proxies)))

        if not self.__check_pool:
            self.__check_proxy_pool()

        if self.__bad_proxies > len(self.__valid_proxies):
            return False

        if proxy:
            if not timeout:
                self.__valid_proxies_index = self.__request_counter % len(self.__valid_proxies)
            proxies = {"http": self.__valid_proxies[self.__valid_proxies_index], "https": self.__valid_proxies[self.__valid_proxies_index]}
        else:
            proxies = None

        if not timeout:
            timeout = self.__start_timeout

        try:
            if proxy:
                self.logger.info("request via proxy {0:25s} to {1} timeout={2:2s}".format(str(proxies["http"]), url, str(timeout[0])))
            self.__request_counter += 1
            response = requests.get(url,
                                    proxies=proxies,
                                    headers={
                                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'},
                                    timeout=timeout[0]
                                    )
            
            return response
        except Timeout:
            self.logger.error("{0:>17} {1:25s} Timeout (timeout={2})".format("proxy", self.__valid_proxies[self.__valid_proxies_index], timeout[0]))
            if timeout[0] < self.__max_timeout:
                return self.rotating_requests(url, proxy, timeout=(timeout[0]+timeout[1],timeout[0]))
            else:
                error_handling("Timeout", self.__valid_proxies_index)
                return self.rotating_requests(url, proxy)
        except ContentDecodingError:
            error_handling("ContentDecodingError", self.__valid_proxies_index)
            return self.rotating_requests(url, proxy)
        except TooManyRedirects:
            error_handling("TooManyRedirects", self.__valid_proxies_index)
            return self.rotating_requests(url, proxy)
        except ConnectionError:
            error_handling("ConnectionError", self.__valid_proxies_index)
            return self.rotating_requests(url, proxy)
    
    #######################################################################################################################

    # GET PROXIES

    #######################################################################################################################

    @debug_verbose
    def __get_proxies(self, run) -> None:
        if run <= 2:
            if not self.__read_file(file=self.__proxies_file, target=self.__unchecked_proxies):
                if not self.__get_proxies_from_web(own_ip=True):
                    # what to do?
                    pass
        elif run <= 3:
            self.__valid_proxies = self.__unchecked_proxies
            if not self.__get_proxies_from_web():
                self.__delete_file(self.__proxies_file)
                if not self.__get_proxies_from_web(own_ip=True):
                    # what to do?
                    pass
        else:
            self.__delete_file(self.__proxies_file)
            if not self.__get_proxies_from_web(own_ip=True):
                # what to do?
                pass
    
    @debug_verbose
    def __get_valid_proxies(self, run) -> None:
        if run <= 1:
            if not self.__read_file(file=self.__valid_proxies_file, target=self.__valid_proxies):
                self.__valid_proxies = []
                run += 1
                self.__get_proxies(run)
        else:
            self.__valid_proxies = []
            self.__delete_file(self.__valid_proxies_file)
            self.__get_proxies(run)

    #######################################################################################################################

    # VALIDATING PROXIES

    #######################################################################################################################

    @debug_verbose
    def __start_validating_proxies(self) -> None:
        self.logger.info("start validating proxies")
        self.__valid_proxies = []

        for proxy in self.__unchecked_proxies:
            self.__unchecked_proxies_queue.put(proxy)

        ths = []
        for _ in range(self.__threads):
            t = threading.Thread(target=self.__validate_proxies, args=(self.__max_timeout,))  # ToDo: #29 give the thread the name if proxy-IP [Thread-{Nr:<4} ({proxy-IP:<25})]
            ths.append(t)
            t.start()
        for thd in ths:
            thd.join()
        self.logger.info("found {} valid proxies".format(len(self.__valid_proxies)))
        self.__write_list_to_file(self.__valid_proxies, self.__valid_proxies_file)

    @debug_verbose
    def __validate_proxies(self, timeout) -> None:
        url = "http://ipinfo.io/json"
        while not self.__unchecked_proxies_queue.empty():
            proxy = self.__unchecked_proxies_queue.get()
            try:
                response = requests.get(url,
                                        proxies={"http": proxy,
                                                 "https": proxy},
                                        headers={
                                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'},
                                        timeout=timeout
                                        )
                if response.status_code == requests.codes.ok and response.text is not None:
                    text = response.json()
                    self.__valid_proxies.append(proxy)      # ToDo: #30 save proxies with informations
                    self.logger.info("added {0:25s} {1} in {2}{3:>25} valid proxies".format(proxy, response.status_code, text["country"], len(self.__valid_proxies)))
                else:
                    self.logger.info("      {0:25s} {1} {2}".format(proxy, response.status_code, response.reason))
            except Timeout:
                self.logger.error("      {0:25s} Timeout (timeout={1})".format(proxy, timeout))
            except ProxyError:
                self.logger.error("      {0:25s} ProxyError".format(proxy))
            except ConnectionError:
                self.logger.error("      {0:25s} ConnectionError".format(proxy))
            except RequestException as e:
                self.logger.error(e)

    @debug_verbose
    def __check_proxy_pool(self, run=0.1) -> None:
        self.__check_pool = True
        while(run):
            run = int(run)
            if len(self.__valid_proxies) == 0:
                self.logger.warning("You hav 0 valid proxies!")
                run += 1
            elif len(self.__valid_proxies) < self.__min_valid_proxies:
                self.logger.warning("You hav {0} valid proxies, {1} under minimum amount!".format(len(self.__valid_proxies), self.__min_valid_proxies - len(self.__valid_proxies)))
                run += 1
            elif self.__bad_proxies / float(len(self.__valid_proxies)) > self.__accepted_bad_proxy_quote:
                self.logger.warning("Your bad proxy quote is {0}, defined bad proxy qoute is {1}".format(self.__bad_proxies / float(len(self.__valid_proxies)), self.__accepted_bad_proxy_quote))
                run += 1
            elif self.__request_counter % len(self.__valid_proxies) == 0:
                self.logger.info("Check proxypool regulary after {0} runs".format(len(self.__valid_proxies)))
                run += 1
            else:
                run = 0
            
            if run:
                self.logger.info("Check proxy pool...")
                self.__bad_proxies = 0
                self.__get_valid_proxies(run)
                if run <= 1:
                    self.__start_validating_proxies()
            else:
                self.__check_pool = False

        
                

    #######################################################################################################################

    # INTERNAL WEB INTERACTIONS

    #######################################################################################################################

    @debug_verbose
    def __get_proxies_from_web(self, own_ip=False) -> bool:
        proxies = []

        if own_ip:
            self.logger.warning("!!!WARNING!!! REQUEST WITH YOUR OWN IP !!!WARNING!!!")
            # ToDo: #16 write a describing message
            confirm = False if input("Do you agree with it? ( y / [n] )") != "y" else True
            if not confirm:
                exit()

        for url in self.__urls:
            self.logger.info("Send a get request to {0}".format(url))

            if "proxyscrape.com" in url:
                response = self.rotating_requests(url, proxy=not own_ip)
                if not response:
                    return False
                proxies.extend(self.__proxyscrape(response))
            elif "free-proxy-list.net" in url and False:    # Skip this for now
                response = self.rotating_requests(url, proxy=not own_ip)
                if not response:
                    return False
                proxies.extend(self.__free_proxy_list(response))

            # ToDo: #17 clean proxies from duplicates
            self.logger.info("Request successful")
        
        if not len(proxies) == 0:
            self.__write_list_to_file(proxies, self.__proxies_file)
            self.__unchecked_proxies = proxies
            return True
        else:
            return False


    #######################################################################################################################

    # PARSING HTTP CONTENT

    #######################################################################################################################

    # @debug_verbose
    # def __free_proxy_list(self, html):    # ToDo: #15 finish this method
    #     proxies_fpl = []
    #     soup = BeautifulSoup(html, "html.parser")
    #     x = soup.find("textarea")
    #     return proxies_fpl

    @debug_verbose
    def __proxyscrape(self, response) -> list:
        proxies = response.text.split("\r\n")
        self.logger.info("Get {0} proxies from {1}".format(len(proxies), response.url))
        
        return proxies

    #######################################################################################################################

    # FILE HANDLING

    #######################################################################################################################

    @debug_verbose
    def __delete_file(self, file) -> None:
        self.logger.debug("Try to delete {}".format(file))
        try:
            os.remove(file)
            self.logger.info("{} has been deleted.".format(file))
        except FileNotFoundError:
            self.logger.error("{} does not exist!".format(file))

    @debug_verbose
    def __write_list_to_file(self, proxy_list: list, file):
        self.logger.info("Try to save values to {}".format(file))
        try:
            with open(self.__proxies_file, "w") as f:
                for i in range(len(proxy_list)):
                    self.logger.info("Write {0}".format(proxy_list[i]))
                    f.write(proxy_list[i] + "\n")
            self.logger.info("Finalized writing values to {}".format(file))
        except Exception as e:
            self.logger.error(e)

    @debug_verbose
    def __read_file(self, file, target: list) -> bool:
        self.logger.info("Try to read list from {0}".format(file))
        try:
            with open(file, "r") as f:
                value = f.readline().replace("\n","")
                target.append(value)
                self.logger.info("Get {}".format(value))
                # proxies = f.read().split("\n")[:-1]

            # self.__unchecked_proxies = proxies
            self.logger.info("Get {0} values".format(len(target)))
            return True
        except FileNotFoundError:
            self.logger.error("{0} does not exist".format(file))
            return False


if __name__ == "__main__":
    pr = ProxyRotator()
