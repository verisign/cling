#-*- coding: utf-8 -*-

from setuptools import setup, find_packages
import cling

setup (
    name='cling',
    version=cling.__version__,
    packages=find_packages('.'),
    description=('Cling(CLI next gen) is a Python module for automating '
                 'network device command line interface interaction'),
    author='Anton Gavrik, Leonidas Poulopoulos, Michael Lim',
    license='BSD 3-Clause',                 
)

