import os, sys
import unittest
import shutil # for cleanup
from cStringIO import StringIO
from contextlib import contextmanager
from urllib2 import HTTPError, URLError
from mock import patch
import md5s3stash
import urllib2
from collections import namedtuple
from pprint import pprint as pp
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

DIR_THIS_FILE = os.path.abspath(os.path.split(__file__)[0])
DIR_FIXTURES = os.path.join(DIR_THIS_FILE, 'fixtures')


# some helper stuff for the tests

#from: http://schinckel.net/2013/04/15/capture-and-test-sys.stdout-sys.stderr-in-unittest.testcase/
@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    command(*args, **kwargs)
    sys.stdout.seek(0)
    yield sys.stdout.read()
    sys.stdout = out

# urllib
class FakeReq(object):
    def __init__(self, strdata, code=200):
        self.io = StringIO(strdata)
        self.code = code
    def info(self):
        return {
            'Content-type':'text/html',
            'ETag': 'you\'re it',
        }
    def read(self, chunk):
        return self.io.read(chunk)
    def getcode(self):
        return self.code

# urllib 2
# https://gist.github.com/puffin/966992
class MockResponse(object):
    def __init__(self, resp_data, code=200, msg='OK'):
        self.resp_data = resp_data
        self.code = code
        self.msg = msg
        self.headers = {'content-type': 'text/plain; charset=utf-8'}
    def read(self):
        return self.resp_data
    def getcode(self):
        return self.code
    def add_handler(self, handler):
        return None
    def open(self, o):
        return StringIO(self.resp_data)



################################################################################
# tests
################################################################################

class CheckChunksTestCase(unittest.TestCase):
    '''Test that the md5s3stash test case supports authentication
    '''
    def setUp(self):
        super(CheckChunksTestCase, self).setUp()
        self.testfilepath = os.path.join(DIR_FIXTURES, '1x1.png')
        self.temp_file = None
        # self.opener = urllib2.build_opener(md5s3stash.DefaultErrorHandler())

    def tearDown(self):
        super(CheckChunksTestCase, self).tearDown()
        if self.temp_file:
            os.remove(self.temp_file)

    def test_local_file_download(self):
    #return file, temp_path, baseFile, hasher.hexdigest(), mime_type
        (self.temp_file, md5, mime_type) = md5s3stash.checkChunks(self.testfilepath)
        self.assertEqual(md5, '71a50dbba44c78128b221b7df7bb51f1')
        self.assertEqual(mime_type, 'image/png')
        #how to check the tmp files?
        self.assertTrue('md5s3' in self.temp_file)
        self.assertTrue(os.path.isfile(self.temp_file))
        self.assertEqual(os.stat(self.temp_file).st_size, 95)

    @patch('md5s3stash.urlopen_with_auth')
    def test_local_file_download_wauth(self, mock_urlopen):
        '''To see that the checkChunks accepts an auth argument'''
        mock_urlopen.return_value = FakeReq('test resp')
        (self.temp_file, md5, mime_type) = md5s3stash.checkChunks(
                                    self.testfilepath,
                                    auth=('username','password'))
        # mock_urlopen.reset_mock()
        file = os.path.join(DIR_FIXTURES, '1x1.png')
        # print "last modified: %s" % time.ctime(os.path.getmtime(file))
        lmod = format_date_time(os.path.getmtime(file))
        mock_urlopen.assert_called_once_with(
                                    file,
                                    auth=('username', 'password'), 
                                    cache={self.testfilepath: {u'If_None_Match': "you're it", u'If_Last_Modified': lmod , u'md5': '85b5a0deaa11f3a5d1762c55701c03da'}})
        
    @patch('urllib.urlopen')
    def test_HTTPError(self, mock_urlopen):
        '''Test handling of HTTPError from urllib'''
        with open(self.testfilepath) as fp:
            side_effect=HTTPError('http://bogus-url', 500, 'test HTTPError',
                'headers', fp)
        mock_urlopen.side_effect = side_effect
        with capture(md5s3stash.checkChunks, 'http://bogus-url') as output:
            self.assertFalse(md5s3stash.checkChunks('http://bogus-url'))
            # self.assertEqual(output, 'URL Error: [Errno 8] nodename nor servname provided, or not known http://bogus-url\n')

    def test_URLError(self):
        '''Test handling of URLError from urllib2'''
        with capture(md5s3stash.checkChunks, 'http://bogus-url') as output:
            self.assertFalse(md5s3stash.checkChunks('http://bogus-url'))
            #self.assertEqual(
                 #output,
                #'URL Error: [Errno 8] nodename nor servname provided, or not known http://bogus-url\n'
            #)

    def test_IOError(self):
        '''Test handling of IOError from urllib.
        Current raise IOError'''
        try:
            (self.temp_file, md5, mime_type) = md5s3stash.checkChunks('./this-path-is-bogus')
        except IOError:
            return True
        self.fail("Didn't raise IOError for file path ./this-path-is-bogus")


class URLOpenWithAuthTestCase(unittest.TestCase):
    '''Test the function of the urlopen_with_auth function.
    with no auth, defaults to urllib.urlopen
    '''
    def setUp(self):
        super(URLOpenWithAuthTestCase, self).setUp()
        self.testfilepath = os.path.join(DIR_FIXTURES, '1x1.png')
        "Mock urllib2.urlopen"
        self.patcher = patch('urllib2.OpenerDirector')
        self.urlopen_mock = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_urlopen_with_auth_exists(self):
        req = md5s3stash.urlopen_with_auth(self.testfilepath)
        req = md5s3stash.urlopen_with_auth(self.testfilepath, auth=None)
        url_http = 'http://example.edu'
        self.assertRaises(URLError, md5s3stash.urlopen_with_auth, url_http,
                                            auth=('user','password'))

    @patch('urllib.urlopen')
    # @patch('md5s3stash.urllib2.build_opener')
    def test_urlopen_with_auth(self, mock_urlopen, mock_bo={}):
        test_str = 'test resp'
        mock_urlopen.return_value = StringIO(test_str)
        self.urlopen_mock.return_value = MockResponse(test_str)
        # self.urlopen_mock.return_value = StringIO(test_str)
        url_http = 'https://example.edu'
        f = md5s3stash.urlopen_with_auth(url_http,
                                         auth=('user','password'),
                                         cache={},)
        self.assertEqual(test_str, f.read())
        #what else can i test?

class CacheTestCase(unittest.TestCase):
    def setUp(self):
        super(CacheTestCase, self).setUp()
        self.url_cache = {}
        self.hash_cache = {
            '85b5a0deaa11f3a5d1762c55701c03da': (
                's3_url', 'mime_type', (100, 100)
            )
        }
        self.testfilepath = os.path.join(DIR_FIXTURES, '1x1.png')
        "Mock urllib2.urlopen"
        self.patcher = patch('urllib2.urlopen')
        self.urlopen_mock = self.patcher.start()


    @patch('md5s3stash.urlopen_with_auth')
    @patch('md5s3stash.s3move')
    def test_hash_cache(
        self,
        mock_s3move,
        mock_urlopen
    ):
        mock_urlopen.return_value = FakeReq('test resp')
        report = md5s3stash.md5s3stash('http://example.edu/', 'fake-bucket',
                                conn='FAKE CONN',
                                url_cache=self.url_cache,
                                hash_cache=self.hash_cache)
        StashReport = namedtuple('StashReport', 'url, md5, s3_url, mime_type, dimensions')
        self.assertEqual(
            report,
            StashReport(
                url='http://example.edu/',
                md5='85b5a0deaa11f3a5d1762c55701c03da',
                s3_url='s3_url',
                mime_type='mime_type',
                dimensions=(100, 100)
            )
        )
        self.assertEqual(
            self.hash_cache,
            {'85b5a0deaa11f3a5d1762c55701c03da': ('s3_url',
                                      'mime_type',
                                      (100, 100))}
        )
        mock_urlopen.reset_mock()

    #urolopen_with_auth

    #@patch('md5s3stash.urlopen_with_auth')
    #def test_conditional_get_cache(self, mock_urlopen):
        #mock_urlopen.return_value = FakeReq('test resp', 304)


class Md5toURLTestCase(unittest.TestCase):

    def setUp(self):
        self.md5 = 'd68e763c825dc0e388929ae1b375ce18'
        self.bucket_base = 'test'

    def test_md5_to_s3_url(self):
        self.assertEqual(md5s3stash.md5_to_s3_url(self.md5, self.bucket_base), 
                        's3://1.test/d68e763c825dc0e388929ae1b375ce18'
                        )

    def test_md5_to_http_url(self):
        self.assertEqual(md5s3stash.md5_to_http_url(self.md5, self.bucket_base),
                        'http://1.test.s3.amazonaws.com/d68e763c825dc0e388929ae1b375ce18'
                        )

    def test_md5_to_bucket_shard(self):
        self.assertEqual(md5s3stash.md5_to_bucket_shard(self.md5), '1')

class md5s3stash_TestCase(unittest.TestCase):
    '''Want to test pass through of auth credentials.
    Currently will punt and mock rest of interactions
    '''
    def setUp(self):
        super(md5s3stash_TestCase, self).setUp()
        self.testfilepath = os.path.join(DIR_FIXTURES, '1x1.png')

    
    @patch('md5s3stash.urlopen_with_auth')
    @patch('md5s3stash.s3move')
    def test_md5s3stash_with_auth(
        self,
        mock_s3move,
        mock_urlopen
    ):
        mock_urlopen.return_value = FakeReq('test resp')
        report = md5s3stash.md5s3stash(self.testfilepath, 'fake-bucket',
                                conn='FAKE CONN',
                                url_auth=('username', 'password'))
        tdict = {
            self.testfilepath : {u'If_None_Match': "you're it", u'md5': '85b5a0deaa11f3a5d1762c55701c03da'},
            'https://example.com/endinslash/': {u'If_None_Match': "you're it", u'md5': '85b5a0deaa11f3a5d1762c55701c03da'}, }

        mock_urlopen.assert_called_once_with(
          os.path.join(DIR_FIXTURES, '1x1.png'),
          auth=('username', 'password'), cache=tdict,)
        #mock_urlopen.reset_mock()

        self.assertEqual(report.mime_type, None)  # mock's file is not an image
        self.assertEqual(report.md5, '85b5a0deaa11f3a5d1762c55701c03da')
        self.assertEqual(report.url, os.path.join(DIR_FIXTURES, '1x1.png'))
        self.assertEqual(report.s3_url,
            's3://m.fake-bucket/85b5a0deaa11f3a5d1762c55701c03da')

    @patch('md5s3stash.urlopen_with_auth')
    @patch('md5s3stash.s3move')
    def test_md5s3stash_trailing_slash_url(self, mock_s3move, mock_urlopen):
        '''The Nuxeo urls end with a slash.
        The use of os.path.basename doesn't work as it returns a blank str ''.
        Need to switch to use of NamedTemporaryFile with delete=False to handle
        all cases.
        '''
        mock_urlopen.return_value = FakeReq('test resp')
        report = md5s3stash.md5s3stash('https://example.com/endinslash/', 'fake-bucket',
                                conn='FAKE CONN',
                                url_auth=('username', 'password'))


class ImageInfoTestCase(unittest.TestCase):
    def setUp(self):
        super(ImageInfoTestCase, self).setUp()
        self.testfilepath = os.path.join(DIR_FIXTURES, '1x1.png')
        self.testemptypath = os.path.join(DIR_FIXTURES, 'empty')

    def test_image_info(self):
        self.assertEqual(
            md5s3stash.image_info(self.testfilepath),
            ('image/png', (1, 1))
        )
        self.assertEqual(
            md5s3stash.image_info(self.testemptypath),
            (None, (0, 0))
        )
        self.assertRaises(IOError, md5s3stash.image_info, '')


if __name__=='__main__':
    unittest.main()
