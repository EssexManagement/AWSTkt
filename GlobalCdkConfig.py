"""

"""

import os

from aws_cdk import Duration


class Singleton(type):
    """Base class for Singleton"""
    _instances = {}

    def __call__(cls, *args, **kw):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kw)
        g = cls._instances[cls]
        g.args = args
        g.kw.update(kw)
        return g
# pylint: disable=too-few-public-methods


class Globals(metaclass=Singleton):

    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw

    def __getattr__(self, key):
        return self.kw.get(key)

    def __setitem__(self, key, value):
        self.kw[key] = value

    def __getitem__(self, item):
        return self.kw[item]

    def __setattr__(self, key, value):
        if key in ['args', 'kw']:
            super(Globals, self).__setattr__(key, value)
            return
        self.kw[key] = value

    def set(self, key, value):
        self.kw[key] = value

    def get(self, item,default=None):
        return self.kw.get(item, default)

    def __iter__(self):
        self._i = 0
        return self

    def __next__(self):
        if self._i < len(self.kw):
            r = list(self.kw.keys())[self._i]
            self._i += 1
            return r
        else:
            raise StopIteration()

    def keys(self):
        return self.kw.keys()

    def pop(self, *args):
        return self.kw.pop(*args)


    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return str(self.kw)

Globals()