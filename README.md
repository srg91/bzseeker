bzseeker
========

A small date seeker, which seek desired date in log-files, archived with bzip2. Search is perfomed by the date, without full unpacking log-archive. The result of script is output all messages with sought-for date line by line or output an offset of the block, where the desired date met for the first time.

Search is possible without full unpacking, because bzip2 archive consists of independent from each other blocks. Any block can be unpacked without full decompression of archive.

Date search is performed using binary search algorithm (because any log-file is array of string, sorted by date), where elements of an array are blocks in a bzip2 archive. Value of an element is date received from block.

Installation
------------

Install bzseeker  via pip from virtualenv (python 2.7):

    pip install -r https://raw.githubusercontent.com/srg91/bzseeker/master/bootstrapper.txt

Usage
-----

Main attributes of the script are log-file and date (in '%Y-%m-%d' format):

    bzseeker log-file.bz2 2014-01-01
    
You can search date with desired format, setting the format after the date:

    bzseeker log-file.bz2 Jul 28 2014" "%b %d %Y"

To just output offset of a block with desired date, you can set `--offset-only` attribute (and `-x` to output in hex):

    bzseeker log-file.bz2 2014-01-01 --offset-only -x
