
import os

# python 2.4 compatibility
try:
    SEEK_SET = os.SEEK_SET
    SEEK_CUR = os.SEEK_CUR
    SEEK_END = os.SEEK_END
except:
    SEEK_SET = 0
    SEEK_CUR = 1
    SEEK_END = 2

from defs import *
from mp4file import (
    Mp4File,
    Atom
)
