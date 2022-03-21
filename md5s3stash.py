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
import urlparse
import base64
import logging
import hashlib
import basin
import boto
import magic
from PIL import Image
from collections import namedtuple
import re

regex_s3 = re.compile(r's3.*amazonaws.com')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='content addressable storage in AWS S3')
    parser.add_argument('url', nargs='+',
                        help='URL or path of source file to stash')
    parser.add_argument('-b', '--bucket_base', nargs="?",
                        help='this must be a unique name in all of AWS S3')
    parser.add_argument('-s', '--bucket_scheme', nargs="?",
                        default="simple", choices=['simple', 'multivalue'],
                        help='this must be a unique name in all of AWS S3')
    parser.add_argument(
        '-t', '--tempdir',
        required=False,
        help="if your files might be large, make sure this is on a big disk"
    )
    parser.add_argument(
        '-w', '--warnings',
        default=False,
        help='show python `DeprecationWarning`s supressed by default',
        required=False,
        action='store_true',
    )
    parser.add_argument('--loglevel', default='ERROR', required=False)
    parser.add_argument('-u', '--username', required=False,
                        help='username for downloads requiring BasicAuth')
    parser.add_argument('-p', '--password', required=False,
                        help='password for downloads requiring BasicAuth')

    if argv is None:
        argv = parser.parse_args()

    if argv.bucket_base:
        bucket_base = argv.bucket_base
    else:
        assert 'BUCKET_BASE' in os.environ, "`-b` or `BUCKET_BASE` must be set"
        bucket_base = os.environ['BUCKET_BASE']

    if not argv.warnings:
        # supress warnings
        # http://stackoverflow.com/a/2047600/1763984
        import warnings
        warnings.simplefilter("ignore", DeprecationWarning)

    if argv.tempdir:
        tempfile.tempdir = argv.tempdir

    auth = None
    if argv.username:
        auth = (argv.username, argv.password)
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
            *md5s3stash(url, bucket_base, conn, url_auth=auth, bucket_scheme=argv.bucket_scheme)
        ))


def md5s3stash(
        url,
        bucket_base,
        conn=None,
        url_auth=None,
        url_cache={},
        hash_cache={},
        bucket_scheme='simple'
    ):
    """ stash a file at `url` in the named `bucket_base` ,
        `conn` is an optional boto.connect_s3()
        `url_auth` is optional Basic auth ('<username>', '<password'>) tuple
        to use if the url to download requires authentication.
        `url_cache` is an object with a dict interface, keyed on url
            url_cache[url] = { md5: ..., If-None-Match: etag, If-Modified-Since: date }
        `hash_cache` is an obhect with dict interface, keyed on md5
            hash_cache[md5] = ( s3_url, mime_type, dimensions )
        `bucket_scheme` is text string 'simple' or 'multibucket'
    """
    StashReport = namedtuple('StashReport', 'url, md5, s3_url, mime_type, dimensions')
    (file_path, md5, mime_type) = checkChunks(url, url_auth, url_cache)
    try:
        return StashReport(url, md5, *hash_cache[md5])
    except KeyError:
        pass
    s3_url = md5_to_s3_url(md5, bucket_base, bucket_scheme=bucket_scheme)
    if conn is None:
        conn = boto.connect_s3()
    s3move(file_path, s3_url, mime_type, conn)
    (mime, dimensions) = image_info(file_path)
    os.remove(file_path)  # safer than rmtree
    hash_cache[md5] = (s3_url, mime, dimensions)
    report = StashReport(url, md5, *hash_cache[md5])
    logging.getLogger('MD5S3:stash').info(report)
    return report


# think about refactoring the next two functions

def md5_to_s3_url(md5, bucket_base, bucket_scheme='multibucket'):
    """ calculate the s3 URL given an md5 and an bucket_base """
    if bucket_scheme == 'simple':
        url = "s3://{0}/{1}".format(
            bucket_base,
            md5
        )
    elif bucket_scheme == 'multibucket':
        url = "s3://{0}.{1}/{2}".format(
            md5_to_bucket_shard(md5),
            bucket_base,
            md5
        )
    return url



def md5_to_http_url(md5, bucket_base, bucket_scheme='multibucket', s3_endpoint='s3.amazonaws.com'):
    """ calculate the http URL given an md5 and an bucket_base """
    if bucket_scheme == 'simple':
        url = "http://{0}/{1}/{2}".format(
            s3_endpoint,
            bucket_base,
            md5
        )
    elif bucket_scheme == 'multibucket':
        url = "http://{1}.{2}.{0}/{3}".format(
            s3_endpoint,
            md5_to_bucket_shard(md5),
            bucket_base,
            md5
        )
    return url


def md5_to_bucket_shard(md5):
    """ calculate the shard label of the bucket name from md5 """
    # "Consider utilizing multiple buckets that start with different
    # alphanumeric characters. This will ensure a degree of partitioning
    # from the start. The higher your volume of concurrent PUT and
    # GET requests, the more impact this will likely have."
    #  -- http://aws.amazon.com/articles/1904
    # "Bucket names must be a series of one or more labels. Adjacent
    # labels are separated by a single period (.). [...] Each label must
    # start and end with a lowercase letter or a number. "
    #  -- http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html
    # see also:  http://en.wikipedia.org/wiki/Base_36
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
    # http://stats.stackexchange.com/a/70884/14900
    # take the first two digits of the hash and turn that into an inteter
    # this should be evenly distributed
    int_value = int(md5[0], 16)+10*int(md5[1], 16)
    # divide by the length of the alphabet and take the remainder
    bucket = int_value % len(ALPHABET)
    return basin.encode(ALPHABET, bucket)

def is_s3_url(url):
    '''For s3 urls, if you send http authentication headers, S3 will
    send a "400 Bad Request" in response.
    Now look for s3*.amazonaws.com
    '''
    # moving to OR this will be s3-us-west-2.amazonaws.com
    match = regex_s3.search(url)
    return True if match else False

def urlopen_with_auth(url, auth=None, cache={}):
    '''Use urllib2 to open url if the auth is specified.
    auth is tuple of (username, password)
    '''
    opener = urllib2.build_opener(DefaultErrorHandler())
    req = urllib2.Request(url)
    p = urlparse.urlparse(url)

    # try to set headers for conditional get request
    try:
        here = cache[url]
        if 'If-None-Match' in here:
            req.add_header('If-None-Match', cache[url]['If-None-Match'],)
        if 'If-Modified-Since' in here:
            req.add_header('If-Modified-Since', cache[url]['If-Modified-Since'],)
    except KeyError:
        pass

    if not auth or is_s3_url(url):
        if p.scheme not in ['http', 'https']:
            return urllib.urlopen(url) # urllib works with normal file paths
    else:
        # make sure https
        if p.scheme != 'https':
            raise urllib2.URLError('Basic auth not over https is bad idea! \
                    scheme:{0}'.format(p.scheme))
        # Need to add header so it gets sent with first request,
        # else redirected to shib
        b64authstr = base64.b64encode('{0}:{1}'.format(*auth))
        req.add_header('Authorization', 'Basic {0}'.format(b64authstr))

    # return urllib2.urlopen(req)
    return opener.open(req)


def checkChunks(url, auth=None, cache={}):
    """
       Helper to download large files the only arg is a url this file
       will go to a temp directory the file will also be downloaded in
       chunks and md5 checksum is returned

       based on downloadChunks@https://gist.github.com/gourneau/1430932
       and http://www.pythoncentral.io/hashing-files-with-python/
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, prefix='md5s3_')
    logging.getLogger('MD5S3').info("temp file path %s" % temp_file.name)

    hasher = hashlib.new('md5')
    BLOCKSIZE = 1024 * hasher.block_size

    try:
        req = urlopen_with_auth(url, auth=auth, cache=cache)
        thisurl = cache.get(url, dict())
        if req.getcode() == 304:
            return None, thisurl['md5'], None
        mime_type = req.info()['Content-type']
        # record these headers, they will let us pretend like we are a cacheing
        # proxy server, and send conditional GETs next time we see this file
        etag = req.info().get('ETag', None);
        if etag:
            thisurl['If-None-Match'] = etag
        lmod = req.info().get('Last-Modified', None);
        if lmod:
            thisurl['If-Modified-Since'] = lmod
        downloaded = 0
        with temp_file:
            while True:
                chunk = req.read(BLOCKSIZE)
                hasher.update(chunk)
                downloaded += len(chunk)
                if not chunk:
                    break
                temp_file.write(chunk)
    except urllib2.HTTPError, e:
        print "HTTP Error:", e.code, url
        return False
    except urllib2.URLError, e:
        print "URL Error:", e.reason, url
        return False

    md5 = hasher.hexdigest()
    thisurl['md5'] = md5
    cache[url] = thisurl
    return temp_file.name, md5, mime_type


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
        bucket = s3.get_bucket(parts.netloc, validate=False)
        l.debug('bucket exists')
    except boto.exception.S3ResponseError:
        bucket = s3.create_bucket(parts.netloc)
        l.debug('bucket created')
    if not(bucket.get_key(parts.path, validate=False)):
        key = bucket.new_key(parts.path)
        # metadata has to be set before setting contents/creating object. 
        # See https://gist.github.com/garnaat/1791086
        key.set_metadata("Content-Type", mime)
        key.set_contents_from_filename(place1)
        # key.set_acl('public-read')
        l.debug('file sent to s3')
    else:
        l.info('key existed already')


def image_info(filepath):
    ''' get image info
        `filepath` path to a file
        returns
          a tuple of two values
            1. mime/type if an image; otherwise None
            2. a tuple of (height, width) if an image; otherwise (0,0)
    '''
    try:
        return (
            magic.Magic(mime=True).from_file(filepath),
            Image.open(filepath).size
        )
    except IOError as e:
        if not e.message.startswith('cannot identify image file'):
            raise e
        else:
            return (None, (0,0))


# example 11.7 Defining URL handlers
# http://www.diveintopython.net/http_web_services/etags.html
class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_304(self, req, fp, code, msg, headers):
        result = urllib2.HTTPError(
            req.get_full_url(), code, msg, headers, fp)
        result.status = code
        return result


# main() idiom for importing into REPL for debugging
if __name__ == "__main__":
    sys.exit(main())


"""
Copyright (c) 2015, Regents of the University of California
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
