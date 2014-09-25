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

class CheckChunksTestCase(unittest.TestCase):
    '''Test that the md5s3stash test case supports authentication
    '''
    def setUp(self):
        super(CheckChunksTestCase, self).setUp()
        self.testFilePath = os.path.join(DIR_FIXTURES, '1x1.png')
        self.tdir = None

    def tearDown(self):
        super(CheckChunksTestCase, self).tearDown()
        if self.tdir:
            shutil.rmtree(self.tdir)

    def test_local_file_download(self):
    #return file, temp_path, baseFile, hasher.hexdigest(), mime_type
        (inputfile, self.tdir, baseFile, md5, mime_type) = md5s3stash.checkChunks(self.testFilePath)
        self.assertEqual(baseFile, '1x1.png')
        self.assertEqual(md5, '71a50dbba44c78128b221b7df7bb51f1')
        self.assertEqual(mime_type, 'image/png')
        #how to check the tmp files?
        self.assertIn('md5s3', inputfile)
        self.assertIn('md5s3', self.tdir)
        self.assertTrue(os.path.isfile(inputfile))
        self.assertTrue(os.path.isdir(self.tdir))
        self.assertEqual(os.stat(inputfile).st_size, 95)

    @patch('urllib.urlopen')
    def test_HTTPError(self, mock_urlopen):
        '''Test handling of HTTPError from urllib'''
        with open(self.testFilePath) as fp:
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
            (inputfile, self.tdir, baseFile, md5, mime_type) = md5s3stash.checkChunks('./this-path-is-bogus')
        except IOError:
            return True
        self.fail("Didn't raise IOError for file path ./this-path-is-bogus")

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


if __name__=='__main__':
    unittest.main()
