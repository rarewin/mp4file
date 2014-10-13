# -*- coding: utf-8 -*-
# vim: set hls is ai et sw=4 sts=4 ts=8 nu ft=python:
'''
Created on Dec 6, 2009

@author: napier
'''
import logging
import os
import struct

from atomsearch import find_path, findall_path

log = logging.getLogger("mp4file")

ATOM_TYPE_MAP = { '\xa9too': 'encoder',
                  '\xa9nam': 'title',
                  '\xa9alb': 'album',
                  '\xa9art': 'artist',
                  '\xa9cmt': 'comment',
                  '\xa9gen': 'genre',
                  'gnre': 'genre',
                  '\xa9day': 'year',
                  'trkn': 'tracknum',
                  'disk': 'disknum',
                  '\xa9wrt': 'composer',
                  'tmpo': 'bpm',
                  'cptr': 'copyright',
                  'cpil': 'compilation',
                  'covr': 'coverart',
                  'rtng': 'rating',
                  '\xa9grp': 'grouping',
                  'pcst': 'podcast',
                  'catg': 'category',
                  'keyw': 'keyword',
                  'purl': 'podcasturl',
                  'egid': 'episodeguid',
                  'desc': 'description',
                  '\xa9lyr': 'lyrics',
                  'tvnn': 'tvnetwork',
                  'tvsh': 'tvshow',
                  'tven': 'tvepisodenum',
                  'tvsn': 'tvseason',
                  'tves': 'tvepisode',
                  'purd': 'purcahsedate',
                  'pgap': 'gapless',
                  }

# There are a lot of atom's with children.  No need to create
# special classes for all of them
ATOM_WITH_CHILDREN = [ 'stik', 'moov', 'trak',
                       'udta', 'ilst', '\xa9too',
                       '\xa9nam', '\xa9alb', '\xa9art',
                       '\xa9cmt', '\xa9gen', 'gnre',
                       '\xa9day', 'trkn', 'disk',
                       '\xa9wrt', 'tmpo', 'cptr',
                       'cpil', 'covr', 'rtng',
                       '\xa9grp', 'pcst', 'catg',
                       'keyw', 'purl', 'egid',
                       'desc', '\xa9lyr', 'tvnn',
                       'tvsh', 'tven', 'tvsn',
                       'tves', 'purd', 'pgap',
                       'mdia', 'minf',
                       'stbl', 'edts',
                       'moof', 'traf',
                      ]

FULL_BOX = (
        'mfhd', 'tfhd', 'trun', 
        'ctts', 'dref', 'elst',
        'esds', 'hmhd', 'mdhd',
        'mehd', 'mvhd', 'nmhd',
        'smhd', 'stco', 'stsc',
        'stsd', 'stss', 'stsz',
        'stts', 'tfra', 'tkhd',
        'vmhd', 'hdlr', 'saio',
        )


class EndOFFile(Exception):
    def __init_(self):
        Exception.__init__(self)


def read64(file):
    '''Return a number by consuming 64 bits from the file's current position.
    '''
    data = file.read(8)
    if (data is None or len(data) <> 8):
        raise EndOFFile()
    return struct.unpack(">Q", data)[0]


def read32(file):
    '''Return a number by consuming 32 bits from the file's current position.
    '''
    data = file.read(4)
    if (data is None or len(data) <> 4):
        raise EndOFFile()
    return struct.unpack(">I", data)[0]


def read24(file):
    '''Return a number by consuming 24 bits from the file's current position.
    '''
    data = file.read(3)
    if (data is None or len(data) <> 3):
        raise EndOFFile()
    return struct.unpack(">I", '\0'+data)[0]


def read16(file):
    '''Return a number by consuming 16 bits from the file's current position.
    '''
    data = file.read(2)
    if (data is None or len(data) <> 2):
        raise EndOFFile()
    return struct.unpack(">H", data)[0]


def read8(file):
    '''Return a number by consuming 8 bits from the file's current position.
    '''
    data = file.read(1)
    if (data is None or len(data) <> 1):
        raise EndOFFile()
    return struct.unpack(">B", data)[0]


def type_to_str(data):
    a = (data >> 0) & 0xff
    b = (data >> 8) & 0xff
    c = (data >> 16) & 0xff
    d = (data >> 24) & 0xff

    return '%c%c%c%c' % (d, c, b, a)


def create_atom(size, type, offset, file):
    clz = type
    # Possibly remap atom types that aren't valid
    # python variable names
    if (ATOM_TYPE_MAP.has_key(type)):
        clz = ATOM_TYPE_MAP[type]
    try:
        # Try and eval the class into existance
        return eval("%s(size, type, clz, offset, file)" % clz)
    except NameError:
        # Not defined, use generic Atom
        return Atom(size, type, clz, offset, file)


def parse_atom(file):
    '''Parse the stream to an atom, just from it's current stream position.
    '''
    try:
        offset = file.tell()
        size = read32(file)
        type = type_to_str(read32(file))
        return create_atom(size, type, offset, file)
    except EndOFFile:
        return None


def parse_atoms(file, maxFileOffset):
    atoms = []
    while file.tell() < maxFileOffset:
        atom = parse_atom(file)
        atoms.append(atom)

        # Seek to the end of the atom
        file.seek(atom.offset + atom.size, os.SEEK_SET)

    return atoms


class Atom(object):
    def __init__(self, size, type, name, offset, file):
        self.__init_pre__(size, type, name, offset, file)
        self.__init_post__(size, type, name, offset, file)

    def __init_pre__(self, size, type, name, offset, file):
        self.size = size
        self.type = type
        self.version = None
        self.flags = None
        self.largesize = None
        self.uuids = None

        self.name = name
        self.offset = offset
        self.header_size = 8
        self.file = file

        self.children = []
        self.attrs = {}

        if type in FULL_BOX:
            file.seek(offset+self.header_size)
            self.version = read8(file)
            self.flags = read24(file)
            self.header_size += 4

        if size == 1:
            file.seek(offset+self.header_size)
            self.largesize = read64(file)
            self.header_size += 8

        # TODO: handling of size == 0

        if type == 'uuid':
            file.seek(offset+self.header_size)
            self.uuids = file.read(16)
            self.header_size += 16

    def __init_post__(self, size, type, name, offset, file):
        if type in ATOM_WITH_CHILDREN:
            self._set_children(parse_atoms(file, offset + self.get_actual_size()))

    def __str__(self):
        return self.type

    __repr__ = __str__

    def _set_attr(self, key, value):
        self.attrs[key] = value

    def _set_children(self, children):
        # Tell the children who their parents are
        for child in children:
            child.parent = self
        self.children = children

    def get_attribute(self, key):
        return self.attrs[key]

    def get_actual_size(self):
        if self.size == 1:
            return self.largesize
        if self.size == 0:
            return None
        return self.size

    def get_atoms(self):
        return self.children

    def find(self, path):
        return find_path(self, path)

    def findall(self, path):
        return findall_path(self, path)

    def _write_header(self, stream):
        stream.write(struct.pack('>I', self.size))
        stream.write(self.type)
        if self.version is not None:
            stream.write(struct.pack('>B', self.version))
        if self.flags is not None:
            stream.write(struct.pack('>I', self.flags)[1:])
        if self.largesize is not None:
            stream.write(self.largesize)
        if self.uuids is not None:
            stream.write(self.uuids)

    def _write_data(self, stream):
        if self.children:
            for child in self.children:
                child.write(stream)
        else:
            self.file.seek(self.offset+self.header_size, os.SEEK_SET)
            stream.write(self.file.read(self.get_actual_size()-self.header_size))

    def write(self, stream):
        '''Write out the box into the given stream.

        :param stream: a writable stream object.
        '''
        # header
        self._write_header(stream)
        # data
        self._write_data(stream)

    def writeFile(self, filename):
        with open(filename, 'w') as fout:
            self.write(fout)


class ftyp(Atom):
    def __init__(self, size, type, name, offset, file):
        Atom.__init__(self, size, type, name, offset, file)
        self._set_attr('major_version', type_to_str(read32(file)))
        self._set_attr('minor_version', read32(file))

class meta(Atom):
    def __init__(self, size, type, name, offset, file):
        Atom.__init__(self, size, type, name, offset, file)
        # meta has an extra null after the atom header.  consume it here
        read32(file)
        self._set_children(parse_atoms(file, offset + size))

class saio(Atom):
    def write(self, stream):
        if self.flags:
            # TODO: special treatment to remove 8 bytes from saio
            version, flags = self.version, self.flags
            self.version = self.flags = None
            self._write_header(stream)
            self.version, self.flags = version, flags
            self.file.seek(self.offset+self.header_size+4, os.SEEK_SET)
            stream.write(self.file.read(self.get_actual_size()-4-self.header_size))
            stream.write(struct.pack('>I', 0))
            stream.write(struct.pack('>I', 0))
        else:
            super(saio, self).write(stream)

class data(Atom):
    def __init__(self, size, type, name, offset, file):
        Atom.__init__(self, size, type, name, offset, file)
        # Mask off the version field
        self.type = read32(file) & 0xFFFFFF
        data = None
        if self.type == 1:
            data = self.parse_string()
            self._set_attr("data", data)
        elif self.type == 21 or self.type == 0:
            # Another random null padding
            read32(self.file)
            data = read32(self.file)
            self._set_attr("data", data)
        elif self.type == 13 or self.type == 14:
            # Another random null padding
            read32(self.file)
            data = self.file.read(self.size - 16)
            self._set_attr("data", data)
        else:
            print self.type

    def parse_string(self):
        # consume extra null?
        read32(self.file)
        howMuch = self.size - 16
        return unicode(self.file.read(howMuch), "utf-8")
