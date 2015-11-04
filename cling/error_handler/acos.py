# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for A10 ACOS devices."

from .default import DefaultErrorHandler
import re

class AcosErrorHandler(DefaultErrorHandler):

    _ERROR_MATCHES = [
                   re.compile(r'%\s+invalid', flags=re.I),
                   re.compile(r'%\s+unknown', flags=re.I),
                   re.compile(r'%\s+ambiguous', flags=re.I),
                   re.compile(r'%\s+incomplete', flags=re.I),
                   re.compile(r'failed', flags=re.I),
                   ]

    def __init__(self, personality):
        super(AcosErrorHandler, self).__init__(personality)

    def has_error(self, output):
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False
