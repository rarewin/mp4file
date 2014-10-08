# -*- coding: utf-8 -*-
# vim: set hls is ai et sw=4 sts=4 ts=8 nu ft=python:
'''
Created on Dec 6, 2009

@author: napier
'''

# built-in modules
import logging
import os

# local modules
from atom import parse_atoms, Atom


log = logging.getLogger("mp4file")


def getFileSize(file):
    file.seek(0, os.SEEK_END)
    endFile = file.tell()
    file.seek(0, os.SEEK_SET)
    return endFile


class Mp4File(Atom):
    def __init__(self, filename):
        file = open(filename, "rb")
        Atom.__init__(self, getFileSize(file), '', '', 0, file)
        self._set_children(parse_atoms(file, getFileSize(file)))
