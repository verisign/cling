# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for Cisco IOS devices."

from .default import DefaultErrorHandler
import re

class IosErrorHandler(DefaultErrorHandler):

    _ERROR_MATCHES = [
                   re.compile(r'%\s+invalid', flags=re.I),
                   re.compile(r'%\s+unknown', flags=re.I),
                   re.compile(r'%\s+ambiguous', flags=re.I),
                   re.compile(r'%\s+incomplete', flags=re.I),
                   re.compile(r'authorization failed', flags=re.I),
                   ]

    def __init__(self, personality):
        super(IosErrorHandler, self).__init__(personality)

    def has_error(self, output):
        # Code that detects _ERROR_MSGS in output
        #if any(err in output for err in self._ERROR_MSGS):
        #    return True
        # Match _ERROR_MATCHES in output
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False
