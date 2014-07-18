import sys
import argparse
from os.path import abspath, expanduser, exists, isfile

from utils import log_error
from seeker import BZ2DateSeeker, ArchiveError


class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('ERROR: %s\n' % message)
        self.print_help()
        sys.exit(2)


def parse_args():
    parser = DefaultHelpParser(description='A small bz2-archived logs seeker.')

    parser.add_argument('archive', type=str, metavar='FILE',
                        help='Path of an archive,'
                             ' in which the date will be searched.')
    parser.add_argument('date', type=str, help='Date for seeking.')
    parser.add_argument('date_format', type=str, nargs='?', default='%Y-%m-%d',
                        help='Format of the date, default: %%Y-%%m-%%d.')

    parser.add_argument('-o', '--offset-only', action='store_true',
                        default=False, dest='offset_only',
                        help='Don\'t output lines with the date,'
                              'show block offset only.')
    parser.add_argument('-x', '--hex', default=False, action='store_true',
                        dest='hex', help='Show the offset in hex.')

    return parser.parse_args()


def _check_filepath(config):
    archive = abspath(expanduser(config.archive))
    if not (exists(archive) and isfile(archive)):
        log_error('Cannot find the file: %s' % archive)
    else:
        config.archive = archive


def main():
    config = parse_args()
    _check_filepath(config)

    with BZ2DateSeeker(config.archive, config.date_format) as seeker:
        try:
            block = seeker.seek(config.date)
        except ArchiveError as e:
            log_error(e.message)

        if not block:
            log_error('Cannot find the date into this archive.')

        if not config.offset_only:
            seeker.output_date(config.date, block.start)
        else:
            mask = '%s' if not config.hex else '0x%x'
            start_offset = mask % block.start
            end_offset = mask % block.end

            print 'Start offset of the block in the archive: %s' % start_offset
            print 'End offset of the block in the archive: %s' % end_offset

if __name__ == '__main__':
    main()
