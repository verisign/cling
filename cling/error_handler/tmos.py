# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for F5 LTM/GMT (TMOS) devices."

from .default import DefaultErrorHandler
import re

class TmosErrorHandler(DefaultErrorHandler):

    _ERROR_MATCHES = [
                   re.compile(r'data input error', flags=re.I),
                   re.compile(r'syntax error', flags=re.I),
                   ]

    def __init__(self, personality):
        super(TmosErrorHandler, self).__init__(personality)

    def has_error(self, output):
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False

