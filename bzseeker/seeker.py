import os
import re
import bz2
import time
from StringIO import StringIO
from datetime import datetime
from collections import namedtuple

import dtreg
from utils import to_timestamp

_Range = namedtuple('Range', ('start', 'end'))


class ArchiveError(Exception):
    pass


class BZ2DateSeeker(object):
    _block_start = b'\x31\x41\x59\x26\x53\x59'
    _stream_end = b'\x17\x72\x45\x38\x50\x90'

    _signature_regex = re.compile(r'BZh(\d)')

    def __init__(self, logfile, dt_format='%Y-%m-%d'):
        with open(logfile, 'rb') as log:
            self._signature = log.read(4)
            match = self._signature_regex.match(self._signature)
            if not match:
                raise ArchiveError('It is not a bz2 file!')
            self._block_size = int(match.group(1)) * 100 * 1024

        self.logfile = open(logfile, 'rb')
        self._limits = _Range(*self._get_archive_limits())

        self._set_dt_format(dt_format)
        self._init_decompressor()

    def _init_decompressor(self):
        self._decompressor = bz2.BZ2Decompressor()
        self._first_decompress = True

    def _set_dt_format(self, dt_format):
        self.dt_format = dt_format
        self.dt_regex = re.compile('(%s)' % dtreg.convert(dt_format))

    def __enter__(self):
        return self

    def _close_archive(self):
        if hasattr(self, 'logfile') and \
                self.logfile and not self.logfile.closed:
            self.logfile.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_archive()

    def __del__(self):
        self._close_archive()

    def seek(self, date, dt_format=None):
        """
        Search the start position of date in a bzipped log file.

        :param date: string with some date
        :type date: str
        :return: position of day
        """
        if dt_format:
            self._set_dt_format(dt_format)

        stamp = to_timestamp(date, self.dt_format)
        block = self._get_block_with_date(stamp)
        if not block:
            return

        if block.start == block.end:
            block.end = self._get_end_of_block(block.end)

        return block

    def output_date(self, date, start, dt_format=None):
        """
        Output lines with the date.
        Output starts from the block at "start" position and
         ends when the date is no longer met.
        Next blocks reads as needed.

        :param date: string with some date
        :type date: str
        :param start: a start position of a block
        :type start: int
        :param dt_format: format of the date
        :type dt_format: str
        """
        if dt_format:
            self._set_dt_format(dt_format)

        stamp = to_timestamp(date, self.dt_format)
        block = _Range(start, self._get_end_of_block(start))

        rest = self._print_stamp_from_block(block, stamp)
        while rest:
            block_start = block.end
            block_end = self._get_end_of_block(block_start)

            rest = self._print_stamp_from_block(
                _Range(block_start, block_end), stamp, rest)

    def _get_block_with_date(self, stamp):
        """
        Search the timestamp into logfile with binary-search,
         jumping onto blocks.
        """
        rmin, rmax = self._limits

        while rmin < rmax:
            block_start, block_end = self._get_middle_position(rmin, rmax)
            if block_start >= rmax:
                break

            block = self._read_block(block_start, block_end)
            start_stamp, end_stamp = self._get_block_stamps(block)

            # If the date at the middle of this block,
            # we will start work with it.
            if start_stamp != end_stamp and start_stamp <= stamp <= end_stamp:
                return _Range(block_start, block_end)

            if start_stamp < stamp:
                rmin = block_end
            else:
                rmax = block_start

            del block

        if rmax == rmin:
            block_start = rmax
            block_end = self._get_end_of_block(block_start)

            block = self._read_block(block_start, block_end)
            start_stamp, end_stamp = self._get_block_stamps(block)
            if start_stamp <= stamp <= end_stamp:
                return _Range(block_start, block_end)
        return

    def _get_middle_position(self, rmin, rmax):
        middle = int(rmin + (rmax - rmin) / 2)

        block_start = self._get_start_of_block(middle)
        block_end = self._get_end_of_block(middle, is_start_of_block=False)

        return block_start, block_end

    def _get_block_stamps(self, block):
        """
        Read the first and the last sentences of the block and try
         to recognize timestamps in it.
        """
        first = block.find('\n', block.find('\n')+1)
        last = block.rfind('\n', 0, block.rfind('\n')-1)

        return (self._get_stamp_from_line(block[:first]),
                self._get_stamp_from_line(block[last:], reverse=True))

    def _read_block(self, start, end):
        """
        Read and decompress the block of data of the archive.
        """
        last_block = False
        if end >= self._file_size:
            # Removing CRC part
            end = self._file_size - 4
            last_block = True

        self.logfile.seek(start)
        text = self.logfile.read(end - start)

        if self._first_decompress:
            text = self._signature + text
            self._first_decompress = False

        block = ''
        result = self._decompressor.decompress(text)
        while result:
            block += result
            result = self._decompressor.decompress('')

        if last_block:
            # We have sent last block and must re-init decompressor
            self._init_decompressor()

        return block

    def _get_stamp_from_line(self, line, reverse=False):
        if not line or not isinstance(line, basestring):
            return 0

        dates = self.dt_regex.findall(line)
        if dates:
            date = dates[-1] if reverse else dates[0]
            stamp = time.mktime(time.strptime(date, self.dt_format))
            if stamp and stamp > 0:
                return stamp

        return 0

    def _seek_through_file(self, text, limit=None, reverse=False):
        """
        Try to search the text bytes into file.

        :param text: text for search.
        :param limit: how long we should search.
        :param reverse: seeking upward instead downward.
        :return: position of text or -1 if text has not been found
        """
        text = str(text)

        if not limit:
            limit = 2*self._block_size

        current = self.logfile.tell()
        if reverse:
            if current - limit < 0:
                limit = current
            self.logfile.seek(-limit, os.SEEK_CUR)

        block = self.logfile.read(limit)
        position = block.find(text) if not reverse else block.rfind(text)
        if position >= 0:
            return current + position \
                if not reverse else current - limit + position
        return -1

    def _seek_downward(self, text, limit=None):
        return self._seek_through_file(text, limit)

    def _seek_upward(self, text, limit=None):
        return self._seek_through_file(text, limit, True)

    def _get_start_of_block(self, position):
        self.logfile.seek(position)
        block_start = self._seek_upward(self._block_start)
        if block_start <= 0:
            if self.logfile.tell() <= 0:
                block_start = len(self._signature)
            else:
                raise ArchiveError(
                    'Limit is reached, when seeking start of block'
                    % position)

        return block_start

    def _get_end_of_block(self, block_start, is_start_of_block=True):
        shift = 0
        if is_start_of_block:
            shift += len(self._block_start)

        self.logfile.seek(block_start + shift)
        block_end = self._seek_downward(self._block_start)
        if block_end < 0:
            block_end = self._file_size

        return block_end

    def _get_archive_limits(self):
        start = len(self._signature)

        self.logfile.seek(start)
        if not self.logfile.read(len(self._block_start)) == self._block_start:
            raise ArchiveError('The start bytes of first block is incorrect.')

        self.logfile.seek(0, os.SEEK_END)
        self._file_size = self.logfile.tell()

        end = self._seek_upward(self._block_start)
        if end <= 0:
            raise ArchiveError('It seems like block structure'
                               ' of this file is corrupted.')

        return start, end

    def _print_stamp_from_block(self, sblock, stamp, rest=''):
        block = self._read_block(sblock.start, sblock.end)
        block_size = len(block)

        dt_str = datetime.fromtimestamp(stamp).strftime(self.dt_format)

        if rest:
            first_sentence = rest + block[:block.find('\n')]
            if first_sentence.find(dt_str) >= 0:
                print first_sentence

        dt_pos = block.find(dt_str)
        if dt_pos >= 0:
            line_start = block.rfind('\n', 0, dt_pos) + 1
        else:
            return

        block = StringIO(block)
        block.seek(line_start)

        for line in block:
            if line.find(dt_str) >= 0:
                print line.strip('\n')
            elif block.tell() == block_size:
                return line
            else:
                return
