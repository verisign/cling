# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for Brodace Ironware devices."

from .default import DefaultErrorHandler
import re

class IronwareErrorHandler(DefaultErrorHandler):

    # These are the most common error messages that a Cisco can return
#     _ERROR_MSGS = [
#                "% Invalid input detected at '^' marker",
#                '% Unknown command or computer name, or unable to find '
#                'computer address',
#                'Command authorization failed',
#                'Authorization failed',
#                '% Incomplete command',
#                '% Ambiguous command'
#                     ]

    _ERROR_MATCHES = [
                    re.compile(r'%Error', flags=re.I),
                    re.compile(r'Invalid input', flags=re.I),
                    re.compile(r'(?:incomplete|ambiguous) command', flags=re.I),
                    re.compile(r'failed', flags=re.I),
                    re.compile(r'[^\r\n]+ not found', flags=re.I),
                    re.compile(r'not authorized', flags=re.I)
                   ]

    def __init__(self, personality):
        super(IronwareErrorHandler, self).__init__(personality)

    def has_error(self, output):
        # Code that detects _ERROR_MSGS in output
        #if any(err in output for err in self._ERROR_MSGS):
        #    return True
        # Match _ERROR_MATCHES in output
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False
