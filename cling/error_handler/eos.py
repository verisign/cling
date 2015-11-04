# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"Error handler tailored for Arista EOS devices."

from .default import DefaultErrorHandler
import re

class EosErrorHandler(DefaultErrorHandler):

    _ERROR_MATCHES = [
                   re.compile(r"% ?error", flags=re.I),
                   re.compile(r"% ?bad secret", flags=re.I),
                   re.compile(r"% ?invalid input", flags=re.I),
                   re.compile(r"% ?(?:incomplete|ambiguous) command", flags=re.I),
                   re.compile(r"connection timed out", flags=re.I),
                   re.compile(r"returned error code:\d+", flags=re.I),

                   ]

    def __init__(self, personality):
        super(EosErrorHandler, self).__init__(personality)

    def has_error(self, output):
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False
