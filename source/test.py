import logging
from datetime import datetime

from source.DefaultLogger import initialize_logger, debug_verbose

initialize_logger()


class A:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @debug_verbose
    def add(self, x, y):
        self.logger.info("{0} + {1} = {2}".format(x,y,x+y))
        self.logger.warning(self.logger.root.handlers)
        return x + y

    def mess(self, x=0):
        self.logger.info("Hallo")
        if x < 5:
            self.mess(x+1)
        else:
            return


s = A()
s.add(7, 4)

s.mess()
