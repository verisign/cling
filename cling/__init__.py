# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

__version__ = '2.3.1'

__all__ = ['Cling', 'Error', 'Reactor']


class Error(Exception):
    """The module's generic exception"""

    pass


from cli import Cling
from reactor import Reactor
