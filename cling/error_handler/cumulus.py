# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"""
Error handler tailored for cumulus devices.
"""

from .default import DefaultErrorHandler
import re


class CumulusErrorHandler(DefaultErrorHandler):
    _ERROR_MATCHES = [
        re.compile(r'\s*error', flags=re.I),
        re.compile(r'\s+command\s+not\s+found', flags=re.I),
    ]

    def __init__(self, personality):
        super(CumulusErrorHandler, self).__init__(personality)

    def has_error(self, output):
        if any(m.search(output) for m in self._ERROR_MATCHES):
            return True
        return False
