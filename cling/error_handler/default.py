# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

"""
Generic error handler.

As handling of device errors is done differently among vendors, a variety of
error detection mechanisms can be incorporated. For example, in Cisco devices
the usage of an error list and a simple heuristic method is sufficient.
Juniper devices may require more sophisticated handling. In all cases, new
modules should be added in a

"<personality>.py"

file. Inside this file a subclass of DefaultErrorHandler should be created as:

"<Personality>ErrorHandler>"

(first leter capital).
"""

class DefaultErrorHandler(object):

    def __init__(self, personality = None):
        self.personality = personality

    def has_error(self, output):
        """ The actual error detector

        It can be really simple with string in list matching to very complex
        with regexps or even API calls
        """
        return False
