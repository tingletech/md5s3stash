import os, sys
import unittest
import shutil # for cleanup
from cStringIO import StringIO
from contextlib import contextmanager
from urllib2 import HTTPError, URLError
from mock import patch
import md5s3stash

DIR_THIS_FILE = os.path.abspath(os.path.split(__file__)[0])
DIR_FIXTURES = os.path.join(DIR_THIS_FILE, 'fixtures')


#from: http://schinckel.net/2013/04/15/capture-and-test-sys.stdout-sys.stderr-in-unittest.testcase/
@contextmanager
def capture(command, *args, **kwargs):
  out, sys.stdout = sys.stdout, StringIO()
  command(*args, **kwargs)
  sys.stdout.seek(0)
  yield sys.stdout.read()
  sys.stdout = out

class FakeReq():
    def __init__(self, strdata):
        self.io = StringIO(strdata)
    def info(self):
        return {'Content-type':'text/html'}
    def read(self, chunk):
        return self.io.read(chunk)


################################################################################

class CheckChunksTestCase(unittest.TestCase):
    '''Test that the md5s3stash test case supports authentication
    '''
    def setUp(self):
        super(CheckChunksTestCase, self).setUp()
        self.testfilepath = os.path.join(DIR_FIXTURES, '1x1.png')
        self.temp_file = None

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
        self.assertIn('md5s3', self.temp_file)
        self.assertTrue(os.path.isfile(self.temp_file))
        self.assertEqual(os.stat(self.temp_file).st_size, 95)

    @patch('md5s3stash.urlopen_with_auth')
    def test_local_file_download_wauth(self, mock_urlopen):
        '''To see that the checkChunks accepts an auth argument'''
        mock_urlopen.return_value = FakeReq('test resp')
        (self.temp_file, md5, mime_type) = md5s3stash.checkChunks(self.testfilepath, auth=('username','password'))
        mock_urlopen.assert_called_once_with('/home/mredar/Documents/workspace/ucldc/md5s3stash/fixtures/1x1.png', ('username', 'password'))
        
    @patch('urllib.urlopen')
    def test_HTTPError(self, mock_urlopen):
        '''Test handling of HTTPError from urllib'''
        with open(self.testfilepath) as fp:
            side_effect=HTTPError('http://bogus-url', 500, 'test HTTPError',
                'headers', fp)
        mock_urlopen.side_effect = side_effect
        with capture(md5s3stash.checkChunks, 'http://bogus-url') as output:
            self.assertFalse(md5s3stash.checkChunks('http://bogus-url'))
            self.assertEqual(output, 'HTTP Error: 500 http://bogus-url\n')

    @patch('urllib.urlopen', side_effect=URLError('BOOM!'))
    def test_URLError(self, mock_urlopen):
        '''Test handling of URLError from urllib'''
        with capture(md5s3stash.checkChunks, 'http://bogus-url') as output:
            self.assertFalse(md5s3stash.checkChunks('http://bogus-url'))
            self.assertEqual(output, 'URL Error: BOOM! http://bogus-url\n')

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

    def test_urlopen_with_auth_exists(self):
        req = md5s3stash.urlopen_with_auth(self.testfilepath)
        req = md5s3stash.urlopen_with_auth(self.testfilepath, auth=None)
        url_http = 'http://example.edu'
        self.assertRaises(URLError, md5s3stash.urlopen_with_auth, url_http,
                                            auth=('user','password'))

    @patch('urllib2.urlopen')
    def test_urlopen_with_auth(self, mock_urlopen):
        test_str = 'test resp'
        mock_urlopen.return_value = StringIO(test_str)
        url_http = 'https://example.edu'
        f = md5s3stash.urlopen_with_auth( url_http,
                                            auth=('user','password'))
        self.assertEqual(test_str, f.read())
        #what else can i test?


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
                        'http://s3.amazonaws.com/1.test/d68e763c825dc0e388929ae1b375ce18'
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
    def test_md5s3stash_with_auth(self, mock_s3move, mock_urlopen):
        mock_urlopen.return_value = FakeReq('test resp')
        report = md5s3stash.md5s3stash(self.testfilepath, 'fake-bucket',
                                conn='FAKE CONN',
                                url_auth=('username', 'password'))
        mock_urlopen.assert_called_once_with(
          '/home/mredar/Documents/workspace/ucldc/md5s3stash/fixtures/1x1.png',
          ('username', 'password'))
        self.assertEqual(report.mime_type, 'text/html')
        self.assertEqual(report.md5, '85b5a0deaa11f3a5d1762c55701c03da')
        self.assertEqual(report.url,
           '/home/mredar/Documents/workspace/ucldc/md5s3stash/fixtures/1x1.png')
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

if __name__=='__main__':
    unittest.main()
