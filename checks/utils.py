import os
from stat import *

def median(vals):
    vals = sorted(vals)
    if not vals:
        raise ValueError(vals)
    elif len(vals) % 2 == 0:
        i1 = int(len(vals) / 2)
        i2 = i1 - 1
        return float(vals[i1] + vals[i2]) / 2.
    else:
        return vals[int(len(vals) / 2)]


class TailFile(object):

    def __init__(self,logger,path,callback):
        self._path = path
        self._f = None
        self._inode = None
        self._size = 0
        self._log = logger
        self._callback = callback
   
    def _open_file(self, move_end=False, where=False):

        already_open = False
        #close and reopen to handle logrotate
        if self._f is not None:
            self._f.close()
            self._f = None
            already_open = True

        stat = os.stat(self._path)
        inode = stat[ST_INO]
        size = stat[ST_SIZE]

        if already_open:
            if self._inode is not None:
                #Check if file has been removed
                if inode != self._inode:
                    self._log.debug("File removed, reopening")
                    move_end = False
                    where = False
            elif self._size > 0:
                #Check if file has been truncated
                if size < self._size:
                    self._log.debug("File truncated, reopening")
                    move_end = False
                    where = False

        self._inode = inode
        self._size = size

        self._f = open(self._path,'r')
        if move_end:
            self._log.debug("Opening file %s" % (self._path))
            self._f.seek(1,os.SEEK_END)
        elif where:
            self._log.debug("Reopening file %s at %s" % (self._path, where))
            self._f.seek(where)

        return True

    def tail(self, line_by_line=True, move_end=True):
        """Read line-by-line and run callback on each line.
        line_by_line: yield each time a callback has returned True
        move_end: start from the last line of the log"""
        try:
            self._open_file(move_end=move_end)

            while True:
                where = self._f.tell()
                line = self._f.readline()
                if line:
                    if self._callback(line.rstrip("\n")):
                        if line_by_line:
                            where = self._f.tell()
                            yield True
                            self._open_file(move_end=False,where=where)
                        else:
                            continue
                    else:
                        continue
                else:
                    yield True
                    self._open_file(move_end=False, where=where)

        except Exception, e:
            # log but survive
            self._log.exception(e)
            raise StopIteration(e)

