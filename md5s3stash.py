#!/usr/bin/env python
""" md5s3stash
    content addressable storage in AWS S3
"""
from __future__ import unicode_literals
import sys
import os
import argparse
import tempfile
import urllib2
import urllib
import logging
import shutil
import hashlib
import basin
import boto
import urlparse
from collections import namedtuple


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='content addressable storage in AWS S3')
    parser.add_argument('url', nargs='+',
                        help='URL or path of source file to stash')
    parser.add_argument('-b', '--bucket_base', nargs="?",
                        help='this must be a unique name in all of AWS S3')
    parser.add_argument('-t', '--tempdir', required=False,
                        help="if your files might be large, make sure this is on a big disk")
    parser.add_argument('-w', '--warnings', default=False,
                        help='show python `DeprecationWarning`s supressed by default',
                        required=False, action='store_true')
    parser.add_argument('--loglevel', default='ERROR', required=False)

    if argv is None:
        argv = parser.parse_args()

    # environment wins over command line parameter??
    # seems like a bug
    try:
        bucket_base = os.environ['BUCKET_BASE']
    except KeyError:
        assert argv.bucket_base, "`-b` or `BUCKET_BASE` must be set"
        bucket_base = argv.bucket_base[0]

    if not argv.warnings:
        # supress warnings
        # http://stackoverflow.com/a/2047600/1763984
        import warnings
        warnings.simplefilter("ignore", DeprecationWarning)

    if argv.tempdir:
        tempfile.tempdir = argv.tempdir

    # set debugging level
    numeric_level = getattr(logging, argv.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % argv.loglevel)
    logging.basicConfig(level=numeric_level, )

    # if being used in a library, probably want to be able to recycle
    # connection?
    conn = boto.connect_s3()
    for url in argv.url:
        print("{0}\t{1}\t{2}\t{3}".format(
            *md5s3stash(url, bucket_base, conn)
        ))


def md5s3stash(url, bucket_base, conn=None):
    """ stash a file at `url` in the named `bucket_base` ,
        `conn` is an optional boto.connect_s3()
    """
    (inputfile, tdir, baseFile, md5, mime_type) = checkChunks(url)
    s3_url = md5_to_s3_url(md5, bucket_base)
    temp_file = os.path.join(tdir, baseFile)
    if conn is None:
        conn = boto.connect_s3()
    s3move(temp_file, s3_url, mime_type, conn)
    shutil.rmtree(tdir)
    StashReport = namedtuple('StashReport', 'url, md5, s3_url, mime_type')
    report = StashReport(url, md5, s3_url, mime_type)
    logging.getLogger('MD5S3:stash').info(report)
    return report


def md5_to_s3_url(md5, bucket_base):
    """ calculate the s3 URL given an md5 and an bucket_base """
    return "s3://{0}.{1}/{2}".format(
        md5_to_bucket(md5),
        bucket_base,
        md5
    )


def md5_to_bucket(md5):
    """ calculate the bucket given an md5 and a bucket_base """
    # "Consider utilizing multiple buckets that start with different
    # alphanumeric characters. This will ensure a degree of partitioning
    # from the start. The higher your volume of concurrent PUT and
    # GET requests, the more impact this will likely have." --
    # http://aws.amazon.com/articles/1904?_encoding=UTF8&jiveRedirect=1
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

    # http://stats.stackexchange.com/a/70884/14900
    # take the first two digits of the hash and turn that into an inteter
    # this should be evenly distributed
    int_value = int(md5[0], 16)+10*int(md5[1], 16)
    # divide by the length of the alphabet and take the remainder
    bucket = int_value % len(ALPHABET)
    return basin.encode(ALPHABET, bucket)


def checkChunks(url):
    """
       Helper to download large files the only arg is a url this file
       will go to a temp directory the file will also be downloaded in
       chunks and md5 checksum is returned

       based on downloadChunks@https://gist.github.com/gourneau/1430932
       and http://www.pythoncentral.io/hashing-files-with-python/
    """
    baseFile = os.path.basename(url)
    temp_path = tempfile.mkdtemp(prefix="md5s3_")
    logging.getLogger('MD5S3').info("temp path %s" % temp_path)

    hasher = hashlib.new('md5')
    BLOCKSIZE = 1024 * hasher.block_size

    try:
        file = os.path.join(temp_path, baseFile)
        req = urllib.urlopen(url)  # urllib works with normal file paths
        mime_type = req.info()['Content-type']
        downloaded = 0
        with open(file, 'wb') as fp:
            while True:
                chunk = req.read(BLOCKSIZE)
                hasher.update(chunk)
                downloaded += len(chunk)
                if not chunk:
                    break
                fp.write(chunk)
    except urllib2.HTTPError, e:
        print "HTTP Error:", e.code, url
        return False
    except urllib2.URLError, e:
        print "URL Error:", e.reason, url
        return False

    return file, temp_path, baseFile, hasher.hexdigest(), mime_type


def s3move(place1, place2, mime, s3):
    l = logging.getLogger('MD5S3:s3move')
    l.debug({
        'place1': place1,
        'place2': place2,
        'mime': mime,
        's3': s3,
    })
    parts = urlparse.urlsplit(place2)
    # SplitResult(scheme='s3', netloc='test.pdf', path='/dkd', query=''
    # , fragment='')
    try:
        bucket = s3.get_bucket(parts.netloc)
        l.debug('bucket exists')
    except boto.exception.S3ResponseError:
        bucket = s3.create_bucket(parts.netloc)
        l.debug('bucket created')
    if not(bucket.get_key(parts.path)):
        key = bucket.new_key(parts.path)
        key.set_contents_from_filename(place1)
        key.set_metadata("Content-Type", mime)
        # key.set_acl('public-read')
        l.debug('file sent to s3')
    else:
        l.info('key existed already')


# main() idiom for importing into REPL for debugging
if __name__ == "__main__":
    sys.exit(main())


"""
Copyright (c) 2014, Regents of the University of California
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the {organization} nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
