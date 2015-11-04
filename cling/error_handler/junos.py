# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for Juniper JUNOS devices."

from .default import DefaultErrorHandler
import re

class JunosErrorHandler(DefaultErrorHandler):

    # These are the most common error messages that a Cisco can return
    _ERROR_MATCHES = [
                   re.compile(r'\s+syntax error', re.I),
                   re.compile(r'^missing argument', re.I),
                   re.compile('^(unknown|invalid|error)', re.I)
                   ]

    def __init__(self, personality):
        super(JunosErrorHandler, self).__init__(personality)

    def has_error(self, output):
        # Match _ERROR_MATCHES in output
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False

