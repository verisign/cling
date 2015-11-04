# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for Palo Alto (PANOS) devices."

from .default import DefaultErrorHandler
import re

class PanosErrorHandler(DefaultErrorHandler):

    _ERROR_MATCHES = [
                   re.compile(r'invalid', flags=re.I),
                   re.compile(r'error', flags=re.I),
                   re.compile(r'unknown', flags=re.I),
                   re.compile(r'incomplete', flags=re.I),
                   re.compile(r'ambiguous', flags=re.I),
                   ]

    def __init__(self, personality):
        super(PanosErrorHandler, self).__init__(personality)

    def has_error(self, output):
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False
